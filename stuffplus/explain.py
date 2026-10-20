"""Why does this pitch get this Stuff+? Coach-friendly explanations (HACK-019).

Uses LightGBM's exact TreeSHAP (``pred_contrib=True``) on the bundle's Stuff+ model and converts each feature's
contribution from xRV (runs) to Stuff+ points with the park-neutral scaler: points = −10 · contribution / sd.
By construction ``base + Σ points == Stuff+`` for every pitch.

* ``explain_pitch(p, rho)``: top contributions with one Spanish sentence each ("+4 por velocidad de 96.0 mph").
* ``altitude_breakdown(p, rho)``: the same pitch in that air vs sea level, split by feature
  ("−3 porque el aire de la CDMX le quita 3.6\" de quiebre vertical").
* ``global_importance``: league-wide importance for the served bundle.

Production Stuff+ v2 (HACK-080). The v2 value is count-neutral (``CountNeutral``: a calibrated multiclass and a contact
model averaged over the 12 counts), which is not one tree ensemble, so TreeSHAP cannot be exact on it. ``V2Explainer``
distils that value into one LightGBM regressor on the v2 stuff features without the count (the target does not depend
on it) over the pitches in their own air, at sea level and in the Harp Helú air, and explains the surrogate exactly:
``base + Σ points`` equals the surrogate's Stuff+, and ``fidelity`` reports how far that is from the real v2 value.
Movement moves between airs with the model's own physics translator, as in reports/altitude_delta.

    python -m stuffplus.explain [--fast]   # reports/explain/ (aggregates, examples at shape medians, README)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from stuffplus import api, serving
from stuffplus.bundle import Bundle
from stuffplus.models.common import as_model_frame
from stuffplus.physics.constants import RHO_HARP_HELU
from stuffplus.scale import GLOBAL

LABELS = {
    "RelSpeed": "velocidad", "SpinRate": "giro", "spin_axis_arm": "eje de giro", "InducedVertBreak": "quiebre vertical",
    "hb_arm": "quiebre horizontal", "RelHeight": "altura de soltado", "rel_side_arm": "soltado lateral",
    "Extension": "extensión", "arm_angle": "ángulo de brazo", "is_rhp": "mano", "AutoPitchType": "tipo de pitch",
    "pitch_family": "tipo de pitch", "rho": "densidad del aire", "velo_diff_fb": "diferencia de velocidad vs su recta",
    "ivb_diff_fb": "diferencia vertical vs su recta", "hb_diff_fb": "diferencia horizontal vs su recta",
}


def _describe(feature: str, value: Any) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = None
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return f"por {LABELS.get(feature, feature)} ({value})" if v is None else f"por {LABELS.get(feature, feature)} desconocido"
    return {
        "RelSpeed": f"por velocidad de {v:.1f} mph",
        "SpinRate": f"por giro de {v:.0f} rpm",
        "spin_axis_arm": f"por eje de giro de {v:.0f}°",
        "InducedVertBreak": f"por {v:.1f}\" de quiebre vertical inducido",
        "hb_arm": f"por {abs(v):.1f}\" de quiebre horizontal hacia el {'brazo' if v >= 0 else 'guante'}",
        "RelHeight": f"por altura de soltado de {v:.1f} ft",
        "rel_side_arm": f"por soltado lateral de {v:.1f} ft",
        "Extension": f"por extensión de {v:.1f} ft",
        "arm_angle": f"por ángulo de brazo de {v:.0f}°",
        "is_rhp": f"por lanzar {'derecho' if v else 'zurdo'}",
        "rho": "por el aire de la CDMX" if v < 0.95 else "por el aire a nivel del mar",
        "velo_diff_fb": f"por {v:+.1f} mph vs su recta",
        "ivb_diff_fb": f"por {v:+.1f}\" de quiebre vertical vs su recta",
        "hb_diff_fb": f"por {v:+.1f}\" de quiebre horizontal vs su recta",
    }.get(feature, f"por {LABELS.get(feature, feature)} = {v:.2f}")


def _to_points(booster, feats: list[str], sc, frame: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """TreeSHAP of ``booster`` in Stuff+ points (park-neutral scaler, league-wide stats) and the base value."""
    contrib = booster.predict(as_model_frame(frame, feats), pred_contrib=True)
    g = sc.stats[GLOBAL]
    k = sc.sign * sc.spread / g["sd"]
    points = pd.DataFrame(contrib[:, :-1] * k, columns=feats, index=frame.index)
    base = sc.center + k * (contrib[:, -1] - g["mean"])
    return points, base


def _contributions(b: Bundle, frame: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """TreeSHAP contributions (Stuff+ points) per feature and the base value, for each row of ``frame``."""
    return _to_points(b.models["stuff_xrv"], b.features("stuff_xrv"), b.scalers["stuff"], frame)


def _altitude_item(f: str, before: Any, after: Any, delta: float) -> dict:
    """One altitude reason: ``delta`` Stuff+ points carried by feature ``f`` between sea level and the CDMX air."""
    if f in ("InducedVertBreak", "hb_arm", "ivb_diff_fb", "hb_diff_fb") and pd.notna(before):
        lost = abs(float(before)) - abs(float(after))
        what = f"le {'quita' if lost > 0 else 'da'} {abs(lost):.1f}\" de {LABELS[f]}"
    elif f == "rho":
        what = "cambia cómo se comporta el contacto (más daño en aire delgado)"
    else:  # value unchanged: TreeSHAP moves credit through interactions with the features that did change
        what = f"cambia el valor de su {LABELS.get(f, f)} (interacción; la variable no cambia)"
    return {"feature": f, "points": round(float(delta), 2), "text": f"{delta:+.0f} porque el aire de la CDMX {what}"}


def _frame_at(p: api.PitchInput, rho: float) -> pd.DataFrame:
    return serving.translate_movement(serving._row_from_input(p), rho, p.rho_measured)


def explain_pitch(p: api.PitchInput, rho: float | str = "harp_helu", top: int = 5, bundle: Bundle | None = None) -> dict:
    """Stuff+ of ``p`` in air ``rho`` and its top ``top`` feature contributions, in Stuff+ points."""
    b = bundle or serving.get_bundle()
    r = api.resolve_rho(rho)
    frame = _frame_at(p, r)
    points, base = _contributions(b, frame)
    row = points.iloc[0]
    order = row.abs().sort_values(ascending=False).index
    items = [{"feature": f, "label": LABELS.get(f, f), "value": frame.iloc[0][f], "points": round(float(row[f]), 2),
              "text": f"{row[f]:+.0f} {_describe(f, frame.iloc[0][f])}"} for f in order[:top]]
    return {"stuff_plus": round(float(base[0] + row.sum()), 1), "base": round(float(base[0]), 1), "rho": r,
            "contributions": items, "other_points": round(float(row[order[top:]].sum()), 2), "model_version": b.version}


def altitude_breakdown(p: api.PitchInput, rho: float | str = "harp_helu", top: int = 4, bundle: Bundle | None = None) -> dict:
    """Same pitch in air ``rho`` vs sea level: total ΔStuff+ and which features carry it (sums exactly)."""
    b = bundle or serving.get_bundle()
    r = api.resolve_rho(rho)
    fa, fs = _frame_at(p, r), _frame_at(p, 1.0)
    pa, base_a = _contributions(b, fa)
    ps, base_s = _contributions(b, fs)
    delta = (pa.iloc[0] - ps.iloc[0])
    total = float(base_a[0] + pa.iloc[0].sum() - base_s[0] - ps.iloc[0].sum())
    order = delta.abs().sort_values(ascending=False).index
    items = [_altitude_item(f, fs.iloc[0].get(f), fa.iloc[0].get(f), delta[f]) for f in order[:top]]
    return {"delta_stuff_plus": round(total, 1), "rho": r, "items": items, "model_version": b.version}


def global_importance(b: Bundle, frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mean |points| per feature and the raw (feature value, points) pairs for dependence plots."""
    points, _ = _contributions(b, frame)
    imp = points.abs().mean().sort_values(ascending=False).rename("mean_abs_points").reset_index().rename(columns={"index": "feature"})
    imp["label"] = imp.feature.map(LABELS).fillna(imp.feature)
    return imp, points


# --- production Stuff+ v2 (HACK-080) ---------------------------------------------------------------------------
SURROGATE_PARAMS = {"learning_rate": 0.1, "num_leaves": 127, "min_data_in_leaf": 100}
EXAMPLE_SHAPES = {"riding 4S": "recta de mucho ride", "sweeper": "sweeper", "changeup": "cambio", "12-6 CB": "curva 12-6"}


@dataclass
class V2Explainer:
    """Surrogate of the production count-neutral Stuff+ v2 value, explained with exact TreeSHAP."""

    model: Any  # stuffplus.models.stuff.CountNeutral
    scaler: Any  # PlusScaler fitted on the sea-level v2 value
    booster: Any
    features: list[str]
    r2: float  # in-sample R² of the surrogate on its training airs

    def at(self, frame: pd.DataFrame, rho: float) -> pd.DataFrame:
        """The same pitches thrown in air ``rho`` (the model's physics translation)."""
        return self.model.translate(frame, rho, frame["rho"].to_numpy(float))

    def stuff_plus(self, frame: pd.DataFrame) -> np.ndarray:
        """Real production Stuff+ v2 of ``frame`` as it stands (league-wide scale, the same one the points use)."""
        g = self.scaler.stats[GLOBAL]
        z = self.scaler.sign * (self.model.predict_xrv(frame) - g["mean"]) / g["sd"]
        return self.scaler.center + self.scaler.spread * z

    def points(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
        return _to_points(self.booster, self.features, self.scaler, frame)


def fit_v2_explainer(model, scaler, frame: pd.DataFrame, rhos=(1.0, RHO_HARP_HELU), rounds: int = 300) -> V2Explainer:
    """Distil the count-neutral v2 value on ``frame`` in its own air and in every air of ``rhos``."""
    import lightgbm as lgb

    from stuffplus.models.common import BASE_PARAMS
    from stuffplus.models.stuff_v2 import COUNT_FEATURES

    feats = [f for f in model.features if f not in COUNT_FEATURES]
    src = frame["rho"].to_numpy(float)
    parts = [frame] + [model.translate(frame, r, src) for r in rhos]
    X = pd.concat([as_model_frame(f, feats) for f in parts], ignore_index=True)
    y = np.concatenate([model.predict_xrv(f) for f in parts])
    booster = lgb.train({**BASE_PARAMS, "objective": "regression", **SURROGATE_PARAMS}, lgb.Dataset(X, y),
                        num_boost_round=rounds)
    r2 = 1 - float(((y - booster.predict(X)) ** 2).sum() / ((y - y.mean()) ** 2).sum())
    return V2Explainer(model, scaler, booster, feats, r2)


def explain_v2(ex: V2Explainer, frame: pd.DataFrame, rho: float = 1.0, top: int = 5) -> list[dict]:
    """Per pitch: real v2 Stuff+ in air ``rho``, the surrogate's and its top ``top`` reasons in Spanish."""
    fa = ex.at(frame, rho)
    points, base = ex.points(fa)
    real = ex.stuff_plus(fa)
    out = []
    for i, (idx, row) in enumerate(points.iterrows()):
        order = row.abs().sort_values(ascending=False).index
        items = [{"feature": f, "label": LABELS.get(f, f), "value": fa.loc[idx, f], "points": round(float(row[f]), 2),
                  "text": f"{row[f]:+.0f} {_describe(f, fa.loc[idx, f])}"} for f in order[:top]]
        out.append({"stuff_plus": round(float(real[i]), 1), "surrogate_stuff_plus": round(float(base[i] + row.sum()), 1),
                    "base": round(float(base[i]), 1), "rho": rho, "contributions": items,
                    "other_points": round(float(row[order[top:]].sum()), 2)})
    return out


def altitude_v2(ex: V2Explainer, frame: pd.DataFrame, rho: float = RHO_HARP_HELU, top: int = 4) -> list[dict]:
    """Per pitch: real v2 ΔStuff+ (air ``rho`` − sea level) and the features that carry the surrogate's Δ."""
    fa, fs = ex.at(frame, rho), ex.at(frame, 1.0)
    pa, ba = ex.points(fa)
    ps, bs = ex.points(fs)
    real = ex.stuff_plus(fa) - ex.stuff_plus(fs)
    out = []
    for i, idx in enumerate(frame.index):
        delta = pa.loc[idx] - ps.loc[idx]
        order = delta.abs().sort_values(ascending=False).index
        out.append({"delta_stuff_plus": round(float(real[i]), 1),
                    "surrogate_delta": round(float(ba[i] + pa.loc[idx].sum() - bs[i] - ps.loc[idx].sum()), 1),
                    "rho": rho, "items": [_altitude_item(f, fs.loc[idx, f], fa.loc[idx, f], delta[f]) for f in order[:top]]})
    return out


def fidelity(ex: V2Explainer, frame: pd.DataFrame, rhos=(1.0, RHO_HARP_HELU)) -> pd.DataFrame:
    """Surrogate vs real v2 Stuff+ on ``frame`` (pitches it was not distilled on) per air, and for ΔStuff+ CDMX."""
    rows, vals = [], {}
    for r in rhos:
        fa = ex.at(frame, r)
        points, base = ex.points(fa)
        vals[r] = (ex.stuff_plus(fa), base + points.sum(axis=1).to_numpy())
    pairs = {f"rho_{r:.3f}": vals[r] for r in rhos}
    if len(rhos) == 2:
        (ra, sa), (rb, sb) = vals[rhos[1]], vals[rhos[0]]
        pairs["delta_cdmx"] = (ra - rb, sa - sb)
    for name, (real, sur) in pairs.items():
        err = sur - real
        rows.append({"target": name, "n": len(real), "r2": 1 - float((err ** 2).sum() / ((real - real.mean()) ** 2).sum()),
                     "corr": float(np.corrcoef(real, sur)[0, 1]), "mae_points": float(np.abs(err).mean()),
                     "p95_abs_points": float(np.quantile(np.abs(err), 0.95)), "real_mean": float(real.mean()),
                     "surrogate_mean": float(sur.mean())})
    return pd.DataFrame(rows)


def shape_examples(frame: pd.DataFrame, shapes=EXAMPLE_SHAPES, min_n: int = 30) -> pd.DataFrame:
    """One typical pitch per shape: the median of every numeric column and the mode of the rest (an aggregate)."""
    rows = []
    for shape, name in shapes.items():
        g = frame[frame["shape"].astype(str) == shape]
        if len(g) < min_n:
            continue
        row = {c: (g[c].median() if pd.api.types.is_numeric_dtype(g[c]) and g[c].dtype != bool else g[c].mode().iloc[0])
               for c in frame.columns}
        rows.append({**row, "example": name, "n": len(g)})
    out = pd.DataFrame(rows)
    if "pitch_family" in frame:
        out["pitch_family"] = out["pitch_family"].astype(frame["pitch_family"].dtype)
    return out


def _plots(frame: pd.DataFrame, points: pd.DataFrame, imp: pd.DataFrame, out_dir) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    feats = [f for f in imp.feature if pd.api.types.is_numeric_dtype(frame[f])][:10]
    rng = np.random.default_rng(2240)
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(feats) + 1.5))
    for i, f in enumerate(reversed(feats)):
        x = points[f].to_numpy()
        val = frame[f].astype(float).to_numpy()
        col = (val - np.nanquantile(val, 0.05)) / (np.nanquantile(val, 0.95) - np.nanquantile(val, 0.05) + 1e-9)
        ax.scatter(x, i + rng.normal(0, 0.08, len(x)), c=np.clip(col, 0, 1), cmap="coolwarm", s=3, alpha=0.4)
    ax.set_yticks(range(len(feats)), [LABELS.get(f, f) for f in reversed(feats)])
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("aporte al Stuff+ (puntos) · color: valor de la variable (azul bajo, rojo alto)")
    ax.set_title("¿Qué hace bueno a un pitch? (TreeSHAP, muestra de la LMB)", fontsize=10)
    fig.savefig(out_dir / "beeswarm.png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    dep = [f for f in ("RelSpeed", "InducedVertBreak", "hb_arm", "Extension", "rho", "SpinRate") if f in points]
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.5))
    for ax, f in zip(axes.ravel(), dep):
        ax.scatter(frame[f].astype(float), points[f], s=2, alpha=0.25, color="#D71920")
        ax.axhline(0, color="black", lw=0.6)
        ax.set_xlabel(LABELS.get(f, f))
        ax.set_ylabel("puntos de Stuff+")
    for ax in axes.ravel()[len(dep):]:
        ax.axis("off")
    fig.suptitle("Dependencia: cómo cambia el Stuff+ con cada variable", fontsize=11)
    fig.savefig(out_dir / "dependence.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


def _readme(fid: pd.DataFrame, r2: float, n_fit: int, rounds: int) -> str:
    f = fid.set_index("target")
    lines = [
        "# Explicaciones SHAP de Stuff+ v2 (HACK-080)",
        "",
        "Generado por `python -m stuffplus.explain`; ninguna cifra se escribió a mano.",
        "",
        "**Qué explica SHAP.** El objetivo es el valor de Stuff+ de producción (v2 con calibración por temperatura,"
        " neutral al conteo: promedio sobre los 12 conteos con los pesos de la familia del pitch; HACK-057), en puntos"
        " de Stuff+ con la escala de nivel del mar de la liga. Ese valor no es un solo ensamble de árboles, así que"
        f" lo destilamos en un regresor LightGBM ({rounds} rondas) sobre las variables de Stuff+ v2 sin el conteo,"
        f" con {n_fit:,} filas: cada lanzamiento de la muestra en su aire, a nivel del mar y en el aire del Harp Helú."
        " TreeSHAP es exacto sobre ese sustituto (base + Σ puntos = Stuff+ del sustituto); la tabla dice cuánto se"
        " aleja del Stuff+ v2 real en lanzamientos que no vio.",
        "",
        "| Objetivo | n | R² | r | Error medio (puntos) | p95 del error (puntos) |",
        "|---|---|---|---|---|---|",
    ]
    for t, row in f.iterrows():
        lines.append(f"| {t} | {int(row.n):,} | {row.r2:.3f} | {row['corr']:.3f} | {row.mae_points:.2f} | {row.p95_abs_points:.2f} |")
    lines += [
        "",
        f"R² del sustituto en su propia muestra: {r2:.3f}. El aire se traslada con el traductor físico del modelo"
        " (el mismo de `reports/altitude_delta/`), no con Magnus ∝ ρ.",
        "",
        "Archivos: `global_importance.csv` (media de |puntos| por variable, lanzamientos en su aire),"
        " `fidelity.csv`, `examples.csv` (el lanzamiento mediano de cuatro formas, a nivel del mar y su ΔStuff+ en la"
        " CDMX, con las razones para el cuerpo técnico), `beeswarm.png` y `dependence.png`.",
        "Sin datos por lanzamiento: solo agregados y lanzamientos medianos por forma.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    import argparse
    import importlib.util

    from stuffplus import config, schema
    from stuffplus.altitude import physics_translator
    from stuffplus.io import load_raw
    from stuffplus.models.stuff import fit_production_stuff
    from stuffplus.scale import PlusScaler

    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location("alt_run", config.repo_root() / "analysis" / "altitude_delta" / "run.py")
    alt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(alt)
    shape_model, d = alt.prepare(schema.clean(load_raw()))
    rounds = dict(class_rounds=60, contact_rounds=40) if args.fast else {}
    model = fit_production_stuff(d, translate=physics_translator(shape_model), k_inner=2 if args.fast else 3, **rounds)
    scaler = PlusScaler().fit(d.assign(x=model.predict_at_rho(d, 1.0)["xrv"].to_numpy()), "x")
    n_fit, n_hold = (10_000, 3_000) if args.fast else (60_000, 20_000)
    pool = d.sample(n=min(len(d), n_fit + n_hold), random_state=2240)
    fit_rows, hold = pool.iloc[:n_fit], pool.iloc[n_fit:]
    srounds = 100 if args.fast else 300
    ex = fit_v2_explainer(model, scaler, fit_rows, rounds=srounds)
    fid = fidelity(ex, hold)
    imp_points, _ = ex.points(fit_rows)
    imp = imp_points.abs().mean().sort_values(ascending=False).rename("mean_abs_points").reset_index().rename(columns={"index": "feature"})
    imp["label"] = imp.feature.map(LABELS).fillna(imp.feature)
    out = config.REPORTS_DIR / "explain"
    out.mkdir(parents=True, exist_ok=True)
    imp.round(4).to_csv(out / "global_importance.csv", index=False)
    fid.round(4).to_csv(out / "fidelity.csv", index=False)
    _plots(fit_rows, imp_points, imp, out)
    examples = shape_examples(d)
    rows = []
    for (_, e), sea, alt_ in zip(examples.iterrows(), explain_v2(ex, examples, 1.0), altitude_v2(ex, examples)):
        rows.append({"pitch": f"{e.example} mediana ({e.n:,} lanzamientos)", "stuff_plus_sea_level": sea["stuff_plus"],
                     "top_reasons": " | ".join(i["text"] for i in sea["contributions"][:3]),
                     "delta_cdmx": alt_["delta_stuff_plus"],
                     "altitude_reasons": " | ".join(i["text"] for i in alt_["items"][:2])})
    pd.DataFrame(rows).to_csv(out / "examples.csv", index=False)
    (out / "README.md").write_text(_readme(fid, ex.r2, 3 * len(fit_rows), srounds), encoding="utf-8")
    print(imp.round(3).to_string(index=False))
    print(fid.round(3).to_string(index=False))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
