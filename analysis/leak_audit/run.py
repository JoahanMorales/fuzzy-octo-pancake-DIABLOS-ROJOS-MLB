"""python -m analysis.leak_audit.run [--fast]  (HACK-054, ~25 min).

How much of a "high" whiff AUC is really plate location? Pitcher-grouped OOF (5 folds) with five feature sets:
physics only · + raw VAA/HAA · + location-netted VAA/HAA · + primary-fastball diffs by batter hand · + plate
location itself (the ceiling a location-aware model reaches; pure Stuff+ must never see it).
Per set: whiff-given-swing AUC (LightGBM binary) and, for the location-free sets, the Stuff+ composite's per-pitch
skill vs the count null and pitcher-level predictiveness. Writes reports/leak_audit/ and its README.

ADOPTION RULE for production Stuff+ (fixed before running; ``decide``): a relative-feature set is adopted only if its
Stuff+ per-pitch skill CI does not overlap below the physics-only skill (lo ≥ physics skill) AND first-50 r,
first-200 r and split-half are ≥ physics-only − 0.005. Raw VAA/HAA are never adopted (they carry location).
"""
from __future__ import annotations

import argparse

import lightgbm as lgb
import numpy as np
import pandas as pd

from stuffplus import config, evaluate, splits
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.baseline import CountBaseline
from stuffplus.features.relative import HAND_FEATURES, NET_FEATURES, ApproachResidual, add_hand_diffs
from stuffplus.models.common import BASE_PARAMS, as_model_frame
from stuffplus.models.stuff import StuffModel, matched_sample_predictiveness, split_half_reliability

OUT = config.REPORTS_DIR / "leak_audit"
BASE = list(STUFF_FEATURES_INVARIANT)
SETS = {
    "fisicas": ("Solo física", BASE, True),
    "vaa_crudo": ("+ VAA/HAA crudos", BASE + ["VertApprAngle", "HorzApprAngle"], True),
    "vaa_neto": ("+ VAA/HAA netos de ubicación", BASE + NET_FEATURES, True),
    "mano": ("+ diferencias por mano del bateador", BASE + HAND_FEATURES, True),
    "ubicacion": ("+ ubicación en el plato (techo)", BASE + ["PlateLocHeight", "plate_x_arm"], False),
}
WHIFF_PARAMS = {"objective": "binary", "learning_rate": 0.05, "num_leaves": 63, "min_data_in_leaf": 300}
TOL_R = 0.005


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


def _auc_ci(y, p, groups, n_boot=200, seed=2240):
    from sklearn.metrics import roc_auc_score

    codes = pd.factorize(groups)[0]
    rng = np.random.default_rng(seed)
    n = codes.max() + 1
    vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, n, n)
        w = np.bincount(pick, minlength=n)[codes]
        vals.append(roc_auc_score(y, p, sample_weight=w))
    return float(roc_auc_score(y, p)), float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def run(d: pd.DataFrame, rounds: dict, whiff_rounds: int) -> dict[str, pd.DataFrame]:
    d = add_hand_diffs(d).reset_index(drop=True)
    folds = list(splits.pitcher_group_kfold(d))
    sw = (d["is_swing"] == 1) & d["t_whiff"].notna()
    y_w = d["t_whiff"].to_numpy(float)
    whiff = {k: np.full(len(d), np.nan) for k in SETS}
    xrv = {k: np.full(len(d), np.nan) for k, (_, _, stuff_ok) in SETS.items() if stuff_ok}
    base = np.full(len(d), np.nan)
    r2 = []
    for i, (tr, te) in enumerate(folds):
        ar = ApproachResidual().fit(d.iloc[tr])
        if i == 0:
            r2.append(ar.r2_table())
        train, test = ar.transform(d.iloc[tr]), ar.transform(d.iloc[te])
        base[te] = CountBaseline().fit(train, ["rv_x"]).predict(test, "rv_x")
        trs, tes = sw.to_numpy()[tr], sw.to_numpy()[te]
        for key, (_, feats, stuff_ok) in SETS.items():
            X_tr, X_te = as_model_frame(train[trs], feats), as_model_frame(test[tes], feats)
            m = lgb.train({**BASE_PARAMS, **WHIFF_PARAMS}, lgb.Dataset(X_tr, y_w[tr][trs]), num_boost_round=whiff_rounds)
            whiff[key][te[tes]] = m.predict(X_te)
            if stuff_ok:
                xrv[key][te] = StuffModel(features=feats, **rounds).fit(train).predict_xrv(test)
    g = d.pitcher_anon_id.to_numpy()
    rows = []
    for key, (label, feats, stuff_ok) in SETS.items():
        auc, lo, hi = _auc_ci(y_w[sw], whiff[key][sw], g[sw])
        rows.append(dict(set=key, label=label, whiff_auc=auc, whiff_auc_lo=lo, whiff_auc_hi=hi, stuff_allowed=stuff_ok))
    t = pd.DataFrame(rows)
    rv = d.rv_x.to_numpy(float)
    skill = evaluate.compare({"baseline": base, **xrv}, rv, groups=g, n_boot=200).set_index("model")
    prows = []
    for key, p in xrv.items():
        f = d.assign(_p=p)
        pr = matched_sample_predictiveness(f, "_p", sizes=(50, 200)).set_index("first_n")
        prows.append(dict(set=key, skill=skill.loc[key, "skill_vs_baseline"], skill_lo=skill.loc[key, "skill_lo"],
                          skill_hi=skill.loc[key, "skill_hi"], first50_r=pr.loc[50, "stuff_model"],
                          first200_r=pr.loc[200, "stuff_model"], split_half_r=split_half_reliability(f, "_p")["stuff_model"]))
    t = t.merge(pd.DataFrame(prows), on="set", how="left")
    return {"audit": t, "r2": pd.concat(r2, ignore_index=True)}


def decide(t: pd.DataFrame) -> pd.DataFrame:
    s = t.set_index("set")
    b = s.loc["fisicas"]
    rows = []
    for key in ("vaa_neto", "mano"):
        r = s.loc[key]
        checks = {"habilidad mejora (IC sobre física)": bool(r.skill_lo >= b.skill),
                  "nivel pitcher no baja": bool(all(r[c] >= b[c] - TOL_R for c in ("first50_r", "first200_r", "split_half_r")))}
        rows.append(dict(set=key, label=r.label, **checks, adopt=all(checks.values())))
    rows.append(dict(set="vaa_crudo", label=s.loc["vaa_crudo", "label"], adopt=False, nota="lleva ubicación: nunca en Stuff+"))
    return pd.DataFrame(rows)


def readme(t: pd.DataFrame, r2: pd.DataFrame, dec: pd.DataFrame) -> str:
    s = t.set_index("set")
    L = ["# Auditoría de fugas: ¿cuánto del AUC es ubicación? (HACK-054)", "",
         "Generado por `python -m analysis.leak_audit.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.", "",
         "El ángulo de llegada vertical (VAA) es física, pero casi toda su variación es *dónde* cruzó el plato el "
         "lanzamiento y desde qué altura salió. Un modelo que ve el VAA crudo ve la ubicación. Medimos cuánto pesa eso "
         "con validación fuera de pliegue por pitcher (5 pliegues).", "",
         "| Variables | AUC swing fallido (IC 95 %) | Stuff+: habilidad vs nulo | 50 → resto | 200 → resto | Mitad contra mitad |",
         "|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        stuff = (f"{100 * r.skill:+.3f} % [{100 * r.skill_lo:+.3f}, {100 * r.skill_hi:+.3f}] | {r.first50_r:.3f} | "
                 f"{r.first200_r:.3f} | {r.split_half_r:.3f}") if r.stuff_allowed else "no permitido en Stuff+ | — | — | —"
        L.append(f"| {r.label} | {r.whiff_auc:.3f} [{r.whiff_auc_lo:.3f}, {r.whiff_auc_hi:.3f}] | {stuff} |")
    vr = r2[r2.angle == "vaa"]
    L += ["", f"**Lectura.** Agregar el VAA crudo sube el AUC de {s.loc['fisicas', 'whiff_auc']:.3f} a "
          f"{s.loc['vaa_crudo', 'whiff_auc']:.3f}; quitarle lo que explican la ubicación y la salida lo deja en "
          f"{s.loc['vaa_neto', 'whiff_auc']:.3f}, y ver la ubicación directamente da {s.loc['ubicacion', 'whiff_auc']:.3f}. "
          f"La ubicación y la altura de salida explican entre {100 * vr.r2_location_release.min():.0f} % y "
          f"{100 * vr.r2_location_release.max():.0f} % de la varianza del VAA según la familia (`r2.csv`). "
          "Un AUC alto con VAA crudo mide en buena parte *dónde* se lanzó, no *qué* se lanzó.", "",
          "## Decisión para Stuff+ en producción (regla fijada antes de correr; `decision.csv`)", ""]
    for _, r in dec.iterrows():
        L.append(f"- **{r.label}: {'adoptar' if r.adopt else 'no adoptar'}**" +
                 (f" ({r.nota})." if isinstance(r.get('nota'), str) else "."))
    L += ["", "## Límites",
          "- Las diferencias por mano usan la recta principal de la temporada (rasgos físicos, sin resultados), "
          "preparadas una vez como las demás variables de arsenal.",
          "- Stuff+ v2 (HACK-052) recibe las variables adoptadas en HACK-057; aquí se mide con la arquitectura v1.", ""]
    return "\n".join(L).replace("—", "-")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    rounds = dict(class_rounds=15, contact_rounds=10) if args.fast else {}
    res = run(load_frame(), rounds, whiff_rounds=40 if args.fast else 300)
    OUT.mkdir(parents=True, exist_ok=True)
    res["audit"].round(6).to_csv(OUT / "audit.csv", index=False)
    res["r2"].round(4).to_csv(OUT / "r2.csv", index=False)
    dec = decide(res["audit"])
    dec.to_csv(OUT / "decision.csv", index=False)
    (OUT / "README.md").write_text(readme(res["audit"], res["r2"], dec), encoding="utf-8")
    print(dec.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
