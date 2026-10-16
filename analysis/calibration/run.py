"""python -m analysis.calibration.run [--models stuff_v1 location stuff_v2] [--fast]  (HACK-053, ~30 min).

Nested calibration (temperature, one-vs-rest isotonic) of the 5-outcome models, evaluated on pitcher-grouped
outer folds: multiclass log-loss, class-wise ECE, xRV calibration slope, per-pitch skill vs the count null and
pitcher-level predictiveness. Writes reports/calibration/ and its README from the CSVs.

ADOPTION RULE (fixed before the first real run; ``decide`` implements it), per model:
  pick the method with the lowest outer log-loss among those that
  (a) lower log-loss vs no calibration,
  (b) keep first-50 r, first-200 r and split-half ≥ uncalibrated − 0.005 (pitcher level),
  (c) keep per-pitch skill vs the count null ≥ uncalibrated − 0.0002 (absolute, i.e. 0.02 points);
  if none qualifies, keep the model uncalibrated.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from stuffplus import calibration as cal
from stuffplus import config, evaluate, splits
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.baseline import CountBaseline
from stuffplus.models.location import LocationModel
from stuffplus.models.stuff import StuffModel, matched_sample_predictiveness, outcome_class, split_half_reliability

OUT = config.REPORTS_DIR / "calibration"
METHODS = ["none", "temperature", "isotonic"]
TOL_R, TOL_SKILL = 0.005, 0.0002
LABELS = {"none": "sin calibrar", "temperature": "temperatura", "isotonic": "isotónica"}


def load_frame() -> pd.DataFrame:
    main = config.main_checkout_root()
    cache = (main / "artifacts" if main else config.ARTIFACTS_DIR) / "tuning" / "frame_pitching.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    from analysis.altitude_delta.run import prepare
    from stuffplus.io import load_raw
    from stuffplus.models.pitching import build_features
    from stuffplus.schema import clean

    return build_features(prepare(clean(load_raw()))[1])


def model_specs(rounds: dict) -> dict:
    specs = {
        "stuff_v1": ("Stuff+ v1", lambda: StuffModel(features=list(STUFF_FEATURES_INVARIANT), **rounds), None),
        "location": ("Location+", lambda: LocationModel(**rounds), None),
    }
    try:  # Stuff+ v2 (HACK-052) when it is on this branch
        from stuffplus.models.stuff_v2 import StuffV2Model

        specs["stuff_v2"] = ("Stuff+ v2", lambda: StuffV2Model(**rounds), lambda m, test: m.stuff_value(test))
    except ImportError:
        pass
    return specs


def evaluate_model(d: pd.DataFrame, factory, value_fn, k_inner: int) -> pd.DataFrame:
    folds = list(splits.pitcher_group_kfold(d))
    y = outcome_class(d).to_numpy()
    rv = d.rv_x.to_numpy(float)
    res = cal.evaluate_methods(factory, d, folds, METHODS, k_inner=k_inner, value_fn=value_fn)
    base = np.full(len(d), np.nan)
    for tr, te in folds:
        base[te] = CountBaseline().fit(d.iloc[tr], ["rv_x"]).predict(d.iloc[te], "rv_x")
    skill = evaluate.compare({"baseline": base, **{m: res[m]["xrv"] for m in METHODS}}, rv,
                             groups=d.pitcher_anon_id.to_numpy(), n_boot=200).set_index("model")
    rows = []
    for m in METHODS:
        f = d.assign(_v=res[m]["value"])
        pr = matched_sample_predictiveness(f, "_v", sizes=(50, 200)).set_index("first_n")
        rows.append(dict(method=m, logloss=cal.log_loss(res[m]["P"], y), ece=cal.classwise_ece(res[m]["P"], y),
                         xrv_slope=cal.slope(rv, res[m]["xrv"]), skill=skill.loc[m, "skill_vs_baseline"],
                         skill_lo=skill.loc[m, "skill_lo"], skill_hi=skill.loc[m, "skill_hi"],
                         first50_r=pr.loc[50, "stuff_model"], first200_r=pr.loc[200, "stuff_model"],
                         split_half_r=split_half_reliability(f, "_v")["stuff_model"]))
    return pd.DataFrame(rows)


def decide(t: pd.DataFrame) -> pd.DataFrame:
    out = []
    for model, g in t.groupby("model", sort=False):
        g = g.set_index("method")
        b = g.loc["none"]
        ok = []
        for m in ("temperature", "isotonic"):
            r = g.loc[m]
            checks = {"log-loss baja": r.logloss < b.logloss,
                      "nivel pitcher no baja": all(r[c] >= b[c] - TOL_R for c in ("first50_r", "first200_r", "split_half_r")),
                      "habilidad por lanzamiento no baja": r.skill >= b.skill - TOL_SKILL}
            out.append(dict(model=model, method=m, **checks, passes=all(checks.values())))
            if all(checks.values()):
                ok.append((r.logloss, m))
        out.append(dict(model=model, method="ELEGIDO", chosen=min(ok)[1] if ok else "none"))
    return pd.DataFrame(out)


def readme(t: pd.DataFrame, dec: pd.DataFrame) -> str:
    L = ["# Calibración de probabilidades (HACK-053)", "",
         "Generado por `python -m analysis.calibration.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.", "",
         "Los árboles potenciados deforman las probabilidades (Niculescu-Mizil y Caruana 2005). Probamos dos correcciones "
         "sobre los 5 resultados (bola, strike cantado, swing fallido, foul, en juego): **temperatura** (un parámetro, "
         "conserva el orden; Guo et al. 2017) e **isotónica uno contra todos** renormalizada. Siempre **anidado**: el "
         "calibrador se ajusta con predicciones fuera de pliegue dentro del entrenamiento y nunca ve a los pitchers que "
         "evalúa (5 pliegues externos por pitcher, 3 internos).", "",
         "| Modelo | Método | Log-loss | ECE por clase | Pendiente xRV | Habilidad vs nulo | 50 → resto | 200 → resto | Mitad contra mitad |",
         "|---|---|---|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        L.append(f"| {r.label} | {LABELS[r.method]} | {r.logloss:.4f} | {r.ece:.4f} | {r.xrv_slope:.2f} | "
                 f"{100 * r.skill:+.3f} % [{100 * r.skill_lo:+.3f}, {100 * r.skill_hi:+.3f}] | {r.first50_r:.3f} | "
                 f"{r.first200_r:.3f} | {r.split_half_r:.3f} |")
    L += ["", "## Decisión (regla fijada antes de correr; `decision.csv`)", ""]
    labels = t.drop_duplicates("model").set_index("model").label
    for model, g in dec.groupby("model", sort=False):
        chosen = g[g.method == "ELEGIDO"].chosen.iloc[0]
        L.append(f"- **{labels[model]}: {LABELS[chosen]}**.")
        for _, r in g[g.method != "ELEGIDO"].iterrows():
            failed = [c for c in ("log-loss baja", "nivel pitcher no baja", "habilidad por lanzamiento no baja") if not r[c]]
            L.append(f"  - {LABELS[r.method]}: {'pasa' if r.passes else 'no cumple: ' + ', '.join(failed)}.")
    L += ["", "El nivel pitcher de Stuff+ v2 usa su valor integrado sobre conteos (`stuff_value`); el de los demás, el xRV.",
          "El calibrador elegido se aplica en producción en HACK-057 con `stuffplus.calibration.fit_nested`. Stuff+ v2 (HACK-052) se evalúa con este mismo script (`--models stuff_v2`) cuando esté integrado; HACK-057 aplica su veredicto.", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--k-inner", type=int, default=3)
    args = ap.parse_args()
    rounds = dict(class_rounds=15, contact_rounds=10) if args.fast else {}
    d = load_frame().reset_index(drop=True)
    specs = model_specs(rounds)
    chosen = args.models or list(specs)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "methods.csv"
    old = pd.read_csv(path) if path.exists() else pd.DataFrame()
    for key in chosen:
        label, factory, value_fn = specs[key]
        t = evaluate_model(d, factory, value_fn, args.k_inner).assign(model=key, label=label)
        old = pd.concat([old[old.model != key] if len(old) else old, t], ignore_index=True)
        old.round(6).to_csv(path, index=False)
        print("done", key, flush=True)
    dec = decide(old)
    dec.to_csv(OUT / "decision.csv", index=False)
    (OUT / "README.md").write_text(readme(old, dec), encoding="utf-8")
    print(dec[dec.method == "ELEGIDO"].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
