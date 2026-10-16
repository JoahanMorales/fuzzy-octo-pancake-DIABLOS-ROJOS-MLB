"""python -m analysis.stuff_v2.run [--parts splits altitude] [--fast]  (HACK-052, ~40 min on the real data).

Before/after: production Stuff+ (v1: pitch_family composite, no count) vs Stuff+ v2 (count values the outcomes;
Stuff+ marginalized over the family's count distribution), plus the count-only ablation and the rubric's null.
Writes reports/stuff_v2/ (aggregates only) and its README from the CSVs, with the adoption verdict.

ADOPTION RULE (fixed before the first real run; ``decide`` implements it):
  R1  v2's per-pitch skill over the count null has a 95 % CI above 0 on pitcher k-fold, season and park holdouts;
  R2  v2 Stuff+ (family weights) keeps pitcher-level first-50 r, first-200 r and split-half ≥ v1 − 0.005;
  R3  league ΔStuff+ in Harp Helú air within ±1.5 of v1, with the same most- and least-resistant shapes.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus import config, evaluate, splits
from stuffplus.altitude import STUFF_FEATURES_INVARIANT, physics_translator
from stuffplus.baseline import CountBaseline
from stuffplus.features.shapes import fit_shapes
from stuffplus.models.stuff import StuffModel, matched_sample_predictiveness, split_half_reliability
from stuffplus.models.stuff_v2 import StuffV2Model, count_only
from stuffplus.physics.constants import RHO_HARP_HELU
from stuffplus.scale import PlusScaler
from stuffplus.validation.stability import stability_table

OUT = config.REPORTS_DIR / "stuff_v2"
TOL_R, TOL_LEAGUE = 0.005, 1.5


def load_frame() -> pd.DataFrame:
    """Altitude-delta preparation (pitch_family, shape, rho, count); cached frame of HACK-028 when present."""
    main = config.main_checkout_root()
    cache = (main / "artifacts" if main else config.ARTIFACTS_DIR) / "tuning" / "frame_pitching.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    from analysis.altitude_delta.run import prepare
    from stuffplus.io import load_raw
    from stuffplus.schema import clean

    return prepare(clean(load_raw()))[1]


def _slope(y, p) -> float:
    ok = np.isfinite(y) & np.isfinite(p)
    return float(np.polyfit(p[ok], y[ok], 1)[0])


def run_splits(d: pd.DataFrame, rounds: dict) -> dict[str, pd.DataFrame]:
    plan = {"pitcher_kfold": list(splits.pitcher_group_kfold(d)), "season_holdout": [splits.season_holdout(d)],
            "park_holdout": [splits.park_holdout(d)]}
    y = d.rv_x.to_numpy(float)
    skill, incr, pitcher_rows = [], [], []
    for name, folds in plan.items():
        preds = {k: np.full(len(d), np.nan) for k in ("baseline", "Stuff+ v1", "Stuff+ v2", "solo conteo")}
        stuff = {k: np.full(len(d), np.nan) for k in ("Stuff+ v1", "Stuff+ v2 (familia)", "Stuff+ v2 (liga)")}
        for tr, te in folds:
            train, test = d.iloc[tr], d.iloc[te]
            preds["baseline"][te] = CountBaseline().fit(train, ["rv_x"]).predict(test, "rv_x")
            v1 = StuffModel(features=list(STUFF_FEATURES_INVARIANT), **rounds).fit(train)
            preds["Stuff+ v1"][te] = stuff["Stuff+ v1"][te] = v1.predict_xrv(test)
            v2 = StuffV2Model(**rounds).fit(train)
            preds["Stuff+ v2"][te] = v2.predict_xrv(test)
            preds["solo conteo"][te] = count_only(rounds).fit(train).predict_xrv(test)
            if name == "pitcher_kfold":
                stuff["Stuff+ v2 (familia)"][te] = v2.stuff_value(test, "family")
                stuff["Stuff+ v2 (liga)"][te] = v2.stuff_value(test, "league")
        idx = np.concatenate([te for _, te in folds])
        g = d.pitcher_anon_id.to_numpy()[idx]
        cmp = evaluate.compare({k: v[idx] for k, v in preds.items()}, y[idx], groups=g, n_boot=300)
        skill.append(cmp.assign(split=name))
        vs = evaluate.compare({k: preds[k][idx] for k in ("solo conteo", "Stuff+ v2")}, y[idx], groups=g,
                              baseline="solo conteo", n_boot=300)
        incr.append(vs[vs.model == "Stuff+ v2"].assign(split=name, vs="solo conteo"))
        if name == "pitcher_kfold":
            for model, p in stuff.items():
                f = d.assign(_p=p)
                pr = matched_sample_predictiveness(f, "_p", sizes=(50, 200)).set_index("first_n")
                st = stability_table(d, p, model, min_n=150, sample_sizes=(50,))
                yy = st[(st.source == "pred") & st.check.str.startswith("year_stability")].correlation
                pitcher_rows.append(dict(model=model, first50_r=pr.loc[50, "stuff_model"],
                                         first200_r=pr.loc[200, "stuff_model"],
                                         observed_first50_r=pr.loc[50, "observed_rv"],
                                         split_half_r=split_half_reliability(f, "_p")["stuff_model"],
                                         year_to_year_r=float(yy.mean()) if len(yy) else np.nan))
            for model in ("Stuff+ v1", "Stuff+ v2"):
                pitcher_rows.append(dict(model=f"{model} · por lanzamiento", calibration_slope=_slope(y, preds[model])))
    return {"skill": pd.concat(skill, ignore_index=True), "incremental": pd.concat(incr, ignore_index=True),
            "pitcher_level": pd.DataFrame(pitcher_rows)}


def run_altitude(d: pd.DataFrame, rounds: dict) -> pd.DataFrame:
    shape_model, _ = fit_shapes(d)
    translate = physics_translator(shape_model)
    v1 = StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=translate, **rounds).fit(d)
    v2 = StuffV2Model(translate=translate, **rounds).fit(d)
    flavours = {
        "Stuff+ v1": (v1.predict_at_rho(d, 1.0)["xrv"].to_numpy(), v1.predict_at_rho(d, RHO_HARP_HELU)["xrv"].to_numpy()),
        "Stuff+ v2 (familia)": (v2.stuff_value_at_rho(d, 1.0), v2.stuff_value_at_rho(d, RHO_HARP_HELU)),
        "Stuff+ v2 (liga)": (v2.stuff_value_at_rho(d, 1.0, "league"), v2.stuff_value_at_rho(d, RHO_HARP_HELU, "league")),
    }
    rows = []
    for model, (sea, hh) in flavours.items():
        sc = PlusScaler().fit(d.assign(x=sea), "x")
        delta = sc.transform(d.assign(x=hh), "x").to_numpy() - sc.transform(d.assign(x=sea), "x").to_numpy()
        by = pd.Series(delta).groupby(d["shape"].astype(str).to_numpy()).agg(["mean", "size"])
        by = by[by["size"] >= 200]["mean"]
        rows.append(dict(model=model, league_delta=float(delta.mean()), best_shape=by.idxmax(), best_delta=by.max(),
                         worst_shape=by.idxmin(), worst_delta=by.min(), **{f"delta_{k}": v for k, v in by.items()}))
    return pd.DataFrame(rows)


def decide(skill: pd.DataFrame, pitcher: pd.DataFrame, alt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    v2 = skill[skill.model == "Stuff+ v2"].set_index("split")
    for split in ("pitcher_kfold", "season_holdout", "park_holdout"):
        rows.append(dict(rule="R1", check=f"habilidad por lanzamiento sobre el nulo, {split}: IC > 0",
                         value=f"{100 * v2.loc[split, 'skill_vs_baseline']:+.3f} % [{100 * v2.loc[split, 'skill_lo']:+.3f}, "
                               f"{100 * v2.loc[split, 'skill_hi']:+.3f}]", passed=bool(v2.loc[split, "skill_lo"] > 0)))
    p = pitcher.set_index("model")
    for col, label in (("first50_r", "primeros 50 → resto"), ("first200_r", "primeros 200 → resto"),
                       ("split_half_r", "confiabilidad mitad contra mitad")):
        a, b = p.loc["Stuff+ v1", col], p.loc["Stuff+ v2 (familia)", col]
        rows.append(dict(rule="R2", check=f"{label}: v2 ≥ v1 − {TOL_R}", value=f"{a:.3f} → {b:.3f}",
                         passed=bool(b >= a - TOL_R)))
    al = alt.set_index("model")
    a, b = al.loc["Stuff+ v1"], al.loc["Stuff+ v2 (familia)"]
    rows.append(dict(rule="R3", check=f"ΔStuff+ de la liga en CDMX a ±{TOL_LEAGUE} de v1",
                     value=f"{a.league_delta:+.1f} → {b.league_delta:+.1f}",
                     passed=bool(abs(b.league_delta - a.league_delta) <= TOL_LEAGUE)))
    rows.append(dict(rule="R3", check="misma forma que más resiste y que más pierde",
                     value=f"{a.best_shape}/{a.worst_shape} → {b.best_shape}/{b.worst_shape}",
                     passed=bool(a.best_shape == b.best_shape and a.worst_shape == b.worst_shape)))
    return pd.DataFrame(rows)


def readme(skill, incr, pitcher, alt, dec) -> str:
    adopt = bool(dec.passed.all())
    L = ["# Stuff+ v2: el conteo valora los resultados, el Stuff+ no depende del conteo (HACK-052)", "",
         "Generado por `python -m analysis.stuff_v2.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.", "",
         "**Qué cambia.** v1 predice el valor del lanzamiento sin ver el conteo, así que por lanzamiento no puede superar "
         "al modelo nulo de la rúbrica (xRV medio por conteo). v2 deja que el conteo (`Balls`, `Strikes`, nada más) valore "
         "los resultados: un strike vale más en 3-0 que en 0-2. La predicción por lanzamiento usa el conteo real y anida "
         "al nulo: mide el **valor incremental del stuff sobre el nulo por conteo**. El **Stuff+ v2** integra el conteo: "
         "promedia el valor del lanzamiento sobre la distribución de conteos de *su familia* en entrenamiento, así que la "
         "mezcla de conteos de un pitcher no mueve su Stuff+. Incluye interacciones stuff × conteo.", "",
         "## Por lanzamiento: habilidad sobre el modelo nulo (`skill.csv`)", "",
         "| Partición | Stuff+ v1 | Stuff+ v2 | Solo conteo (ablación) |", "|---|---|---|---|"]
    for split in ("pitcher_kfold", "season_holdout", "park_holdout"):
        s = skill[skill.split == split].set_index("model")
        cell = lambda m: f"{100 * s.loc[m, 'skill_vs_baseline']:+.3f} % [{100 * s.loc[m, 'skill_lo']:+.3f}, {100 * s.loc[m, 'skill_hi']:+.3f}]"
        L.append(f"| {split} | {cell('Stuff+ v1')} | {cell('Stuff+ v2')} | {cell('solo conteo')} |")
    L += ["", "**Atribución al stuff** (`incremental.csv`): v2 contra la misma arquitectura con solo el conteo."]
    for _, r in incr.iterrows():
        L.append(f"- {r.split}: {100 * r.skill_vs_baseline:+.3f} % [{100 * r.skill_lo:+.3f}, {100 * r.skill_hi:+.3f}]")
    L += ["", "## Nivel pitcher (`pitcher_level.csv`, 5 pliegues por pitcher)", "",
          "| Modelo | 50 → resto (r) | 200 → resto (r) | Mitad contra mitad | Año a año |", "|---|---|---|---|---|"]
    for _, r in pitcher[pitcher.first50_r.notna()].iterrows():
        L.append(f"| {r.model} | {r.first50_r:.3f} | {r.first200_r:.3f} | {r.split_half_r:.3f} | {r.year_to_year_r:.3f} |")
    cal = pitcher[pitcher.calibration_slope.notna()]
    L += ["", "Pendiente de calibración por lanzamiento (1 = ideal): " + "; ".join(
        f"{r.model.split(' ·')[0]} {r.calibration_slope:.2f}" for _, r in cal.iterrows()) + ".", "",
          "## Altitud (`altitude.csv`, aire del Harp Helú contra nivel del mar)", "",
          "| Modelo | ΔStuff+ liga | Resiste más | Pierde más |", "|---|---|---|---|"]
    for _, r in alt.iterrows():
        L.append(f"| {r.model} | {r.league_delta:+.1f} | {r.best_shape} ({r.best_delta:+.1f}) | {r.worst_shape} ({r.worst_delta:+.1f}) |")
    L += ["", "## Decisión (regla fijada antes de correr; `decision.csv`)", "", "| Regla | Prueba | Valor | ¿Pasa? |",
          "|---|---|---|---|"]
    L += [f"| {r.rule} | {r.check} | {r.value} | {'sí' if r.passed else 'no'} |" for _, r in dec.iterrows()]
    L += ["", f"**Veredicto: {'adoptar Stuff+ v2' if adopt else 'no adoptar; v2 queda como ablación documentada'}.**", "",
          "## Límites",
          "- Mismas preparaciones transductivas que HACK-014 (identidad, densidad por juego, valores de carrera).",
          "- Los pesos por familia salen del entrenamiento; la versión con un solo vector de la liga es la sensibilidad.", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parts", nargs="*", default=["splits", "altitude"], choices=["splits", "altitude"])
    ap.add_argument("--fast", action="store_true", help="few trees (smoke only)")
    args = ap.parse_args()
    rounds = dict(class_rounds=15, contact_rounds=10) if args.fast else {}
    d = load_frame().reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if "splits" in args.parts:
        res = run_splits(d, rounds)
        for k, t in res.items():
            t.round(6).to_csv(OUT / f"{k}.csv", index=False)
        print("done splits", flush=True)
    if "altitude" in args.parts:
        run_altitude(d, rounds).round(4).to_csv(OUT / "altitude.csv", index=False)
        print("done altitude", flush=True)
    files = {k: OUT / f"{k}.csv" for k in ("skill", "incremental", "pitcher_level", "altitude")}
    if all(p.exists() for p in files.values()):
        t = {k: pd.read_csv(p) for k, p in files.items()}
        dec = decide(t["skill"], t["pitcher_level"], t["altitude"])
        dec.to_csv(OUT / "decision.csv", index=False)
        (OUT / "README.md").write_text(readme(t["skill"], t["incremental"], t["pitcher_level"], t["altitude"], dec),
                                       encoding="utf-8")
        print("verdict:", "adopt" if dec.passed.all() else "keep v1", flush=True)


if __name__ == "__main__":
    main()
