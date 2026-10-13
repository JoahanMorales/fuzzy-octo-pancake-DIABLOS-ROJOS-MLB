"""Real-model serving behind ``stuffplus.api.predict_pitch`` (HACK-031).

``api.predict_pitch`` dispatches here as soon as ``available()`` is True (a bundle with a manifest exists),
so the dashboard switches from the mock to real models without code changes.

Air density in v0: the models take ``rho`` (relative to sea level) as a feature and see movement already
translated to that air with Magnus ∝ ρ. ``predict_frame`` / ``predict_pitch`` translate the input movement
from the air it was measured in to the target air. HACK-004 replaces the Magnus ∝ ρ rule with the fitted
within-pitcher movement model; the interface stays the same.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from stuffplus.bundle import MANIFEST, Bundle, bundle_dir, load_bundle
from stuffplus.models.common import as_model_frame
from stuffplus.scale import GLOBAL

PROB_TARGETS = {  # api.PROB_KEYS → model target
    "whiff": "t_whiff", "chase": "t_chase", "called_strike": "t_called_strike", "weak_contact": "t_weak_contact",
    "groundball": "t_groundball", "hard_contact": "t_hard_contact", "out_in_pa": "t_out_in_pa",
}


def available() -> bool:
    return (bundle_dir() / MANIFEST).exists()


@lru_cache(maxsize=4)
def _cached(path: str) -> Bundle:
    return load_bundle(path)


def get_bundle() -> Bundle:
    return _cached(str(bundle_dir()))


def reset_cache() -> None:
    _cached.cache_clear()


def translate_movement(df: pd.DataFrame, rho_to, rho_from) -> pd.DataFrame:
    """Copy of ``df`` with IVB / HB / hb_arm scaled from ``rho_from`` air to ``rho_to`` air (Magnus ∝ ρ)."""
    out = df.copy()
    scale = np.asarray(rho_to, float) / np.asarray(rho_from, float)
    for c in ("InducedVertBreak", "HorzBreak", "hb_arm"):
        if c in out:
            out[c] = out[c].astype(float) * scale
    out["rho"] = np.broadcast_to(np.asarray(rho_to, float), len(out)) if np.ndim(rho_to) == 0 else np.asarray(rho_to, float)
    return out


def predict_frame(
    df: pd.DataFrame,
    rho: float | np.ndarray | None = None,
    rho_measured: str | float | np.ndarray = "rho",
    bundle: Bundle | None = None,
    year_col: str | None = "year",
) -> pd.DataFrame:
    """Score many pitches. ``df`` needs arm-side features (``models.common.add_arm_side_features``).

    ``rho``: target air (None = each pitch's own air, from ``rho_measured``). ``rho_measured``: column name or
    value(s) with the air the movement was measured in. Returns xRV / plus / probabilities per row, plus the
    park-neutral Stuff+ (same pitch at ρ = 1).
    """
    b = bundle or get_bundle()
    measured = df[rho_measured].to_numpy(float) if isinstance(rho_measured, str) else np.broadcast_to(
        np.asarray(rho_measured, float), len(df))
    target = measured if rho is None else np.broadcast_to(np.asarray(rho, float), len(df))
    env = translate_movement(df, target, measured)
    neu = translate_movement(df, 1.0, measured)

    def run(model: str, frame: pd.DataFrame) -> np.ndarray:
        return b.models[model].predict(as_model_frame(frame, b.features(model)))

    out = pd.DataFrame(index=df.index)
    groups = df[[year_col]] if year_col and year_col in df else None

    def plus(name: str, xrv: np.ndarray) -> np.ndarray:
        """Season reference when the season is known, else the all-seasons reference (single inputs)."""
        sc = b.scalers[name]
        if groups is not None and sc.by == (year_col,):
            return sc.transform(pd.DataFrame({"x": xrv, year_col: groups[year_col].to_numpy()}), "x").to_numpy()
        g = sc.stats[GLOBAL]
        return sc.center + sc.spread * sc.sign * (np.asarray(xrv, float) - g["mean"]) / g["sd"]

    out["xrv_stuff"] = run("stuff_xrv", env)
    out["stuff_plus"] = plus("stuff", out["xrv_stuff"].to_numpy())
    out["stuff_plus_neutral"] = plus("stuff", run("stuff_xrv", neu))
    has_loc = {"plate_x_arm", "PlateLocHeight", "Balls", "Strikes"} <= set(df.columns) and df[
        ["plate_x_arm", "PlateLocHeight"]].notna().all(axis=1).all()
    if has_loc and "location_xrv" in b.models:
        out["xrv_location"] = run("location_xrv", env)
        out["location_plus"] = plus("location", out["xrv_location"].to_numpy())
        out["xrv_pitching"] = run("pitching_xrv", env)
        out["pitching_plus"] = plus("pitching", out["xrv_pitching"].to_numpy())
    for key, t in PROB_TARGETS.items():
        name = f"stuff_{t}"
        if name in b.models:
            out[f"p_{key}"] = run(name, env)
    out["ivb_expected"] = env["InducedVertBreak"].to_numpy()
    out["hb_expected"] = env["HorzBreak"].to_numpy()
    out["rho"] = target
    return out


def _row_from_input(p) -> pd.DataFrame:
    sign = 1.0 if p.throws == "Right" else -1.0
    row = {
        "AutoPitchType": p.pitch_type, "PitcherThrows": p.throws, "is_rhp": int(p.throws == "Right"),
        "RelSpeed": p.velo, "SpinRate": p.spin_rate, "SpinAxis": p.spin_axis,
        "spin_axis_arm": p.spin_axis % 360 if sign > 0 else (360 - p.spin_axis) % 360,
        "InducedVertBreak": p.ivb, "HorzBreak": p.hb, "hb_arm": p.hb * sign,
        "RelHeight": p.rel_height, "RelSide": p.rel_side, "rel_side_arm": p.rel_side * sign,
        "Extension": p.extension,
    }
    if p.plate_x is not None and p.plate_z is not None:
        same = None if p.batter_side is None else int(p.batter_side == p.throws)
        row.update(plate_x_arm=p.plate_x * sign, PlateLocHeight=p.plate_z, PlateLocSide=p.plate_x,
                   Balls=float(p.balls or 0), Strikes=float(p.strikes or 0), same_side=1 if same is None else same)
    return pd.DataFrame([row])


def predict_pitch(p, rho: float, flavour: str = "environment") -> dict[str, Any]:
    """Contract implementation for ``api.predict_pitch`` (same keys as the mock, ``demo_data`` False)."""
    b = get_bundle()
    target = 1.0 if flavour == "neutral" else float(rho)
    r = predict_frame(_row_from_input(p), rho=target, rho_measured=p.rho_measured, bundle=b, year_col=None).iloc[0]
    stuff = float(r["stuff_plus"])
    loc = float(r["location_plus"]) if "location_plus" in r else None
    pitching = float(r["pitching_plus"]) if "pitching_plus" in r else stuff
    probs = {k: round(float(np.clip(r[f"p_{k}"], 0, 1)), 3) for k in PROB_TARGETS if f"p_{k}" in r}
    return {
        "stuff_plus": round(stuff, 1),
        "stuff_plus_neutral": round(float(r["stuff_plus_neutral"]), 1),
        "location_plus": None if loc is None else round(loc, 1),
        "pitching_plus": round(pitching, 1),
        "xrv": round(float(r["xrv_pitching"] if "xrv_pitching" in r else r["xrv_stuff"]), 4),
        "probs": probs,
        "movement_expected": {"ivb": round(float(r["ivb_expected"]), 2), "hb": round(float(r["hb_expected"]), 2)},
        "rho": target,
        "flavour": flavour,
        "model_version": b.version,
        "demo_data": False,
    }
