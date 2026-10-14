"""Why does this pitch get this Stuff+? Coach-friendly explanations (HACK-019).

Uses LightGBM's exact TreeSHAP (``pred_contrib=True``) on the bundle's Stuff+ model and converts each feature's
contribution from xRV (runs) to Stuff+ points with the park-neutral scaler: points = −10 · contribution / sd.
By construction ``base + Σ points == Stuff+`` for every pitch.

* ``explain_pitch(p, rho)``: top contributions with one Spanish sentence each ("+4 por velocidad de 96.0 mph").
* ``altitude_breakdown(p, rho)``: the same pitch in that air vs sea level, split by feature
  ("−3 porque el aire de la CDMX le quita 3.6\" de quiebre vertical").
* ``global_importance`` / ``python -m stuffplus.explain``: league-wide importance and dependence plots
  (reports/explain/, aggregates only).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from stuffplus import api, serving
from stuffplus.bundle import Bundle
from stuffplus.models.common import as_model_frame
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


def _contributions(b: Bundle, frame: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """TreeSHAP contributions (Stuff+ points) per feature and the base value, for each row of ``frame``."""
    feats = b.features("stuff_xrv")
    contrib = b.models["stuff_xrv"].predict(as_model_frame(frame, feats), pred_contrib=True)
    sc = b.scalers["stuff"]
    g = sc.stats[GLOBAL]
    k = sc.sign * sc.spread / g["sd"]
    points = pd.DataFrame(contrib[:, :-1] * k, columns=feats, index=frame.index)
    base = sc.center + k * (contrib[:, -1] - g["mean"])
    return points, base


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
    items = []
    for f in order[:top]:
        before, after = fs.iloc[0].get(f), fa.iloc[0].get(f)
        if f in ("InducedVertBreak", "hb_arm", "ivb_diff_fb", "hb_diff_fb") and pd.notna(before):
            lost = abs(float(before)) - abs(float(after))
            what = f"le {'quita' if lost > 0 else 'da'} {abs(lost):.1f}\" de {LABELS[f]}"
        elif f == "rho":
            what = "cambia cómo se comporta el contacto (más daño en aire delgado)"
        else:  # value unchanged: TreeSHAP moves credit through interactions with the features that did change
            what = f"cambia el valor de su {LABELS.get(f, f)} (interacción; la variable no cambia)"
        items.append({"feature": f, "points": round(float(delta[f]), 2),
                      "text": f"{delta[f]:+.0f} porque el aire de la CDMX {what}"})
    return {"delta_stuff_plus": round(total, 1), "rho": r, "items": items, "model_version": b.version}


def global_importance(b: Bundle, frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mean |points| per feature and the raw (feature value, points) pairs for dependence plots."""
    points, _ = _contributions(b, frame)
    imp = points.abs().mean().sort_values(ascending=False).rename("mean_abs_points").reset_index().rename(columns={"index": "feature"})
    imp["label"] = imp.feature.map(LABELS).fillna(imp.feature)
    return imp, points


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


def main(sample: int = 60_000) -> None:
    import importlib.util

    from stuffplus import config, schema
    from stuffplus.io import load_raw

    spec = importlib.util.spec_from_file_location("stuff_run", config.repo_root() / "analysis" / "stuff_model" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    frame = mod.prepare(schema.clean(load_raw()))
    if "pitch_family" not in frame:
        frame["pitch_family"] = frame["AutoPitchType"].astype(str)
    frame = frame.sample(n=min(sample, len(frame)), random_state=2240)
    b = serving.get_bundle()
    imp, points = global_importance(b, frame)
    out = config.REPORTS_DIR / "explain"
    out.mkdir(parents=True, exist_ok=True)
    imp.round(4).to_csv(out / "global_importance.csv", index=False)
    _plots(frame, points, imp, out)
    print(imp.round(3).to_string(index=False))
    examples = {
        "recta 96 mph con ride": api.PitchInput("Four-Seam", "Right", 96, 2450, 210, 19, 8, extension=6.6),
        "sweeper 84 mph": api.PitchInput("Slider", "Right", 84, 2650, 80, 0, -15, arsenal={"fb_velo": 94, "fb_ivb": 16, "fb_hb": 8}),
        "changeup 85 mph": api.PitchInput("Changeup", "Right", 85, 1750, 240, 6, 15, arsenal={"fb_velo": 94, "fb_ivb": 16, "fb_hb": 8}),
    }
    rows = []
    for name, p in examples.items():
        e, a = explain_pitch(p, "sea_level"), altitude_breakdown(p, "harp_helu")
        rows.append({"pitch": name, "stuff_plus_sea_level": e["stuff_plus"], "top_reasons": " | ".join(i["text"] for i in e["contributions"][:3]),
                     "delta_cdmx": a["delta_stuff_plus"], "altitude_reasons": " | ".join(i["text"] for i in a["items"][:2])})
    pd.DataFrame(rows).to_csv(out / "examples.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
