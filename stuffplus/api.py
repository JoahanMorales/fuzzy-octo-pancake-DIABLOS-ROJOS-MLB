"""Public prediction API: one pitch in, Stuff+ / Location+ / Pitching+ out, at any air density.

The dashboard, the prospect profiler and the design lab call ONLY ``predict_pitch``. Until a real model
bundle exists, a deterministic physics-flavoured MOCK answers (``demo_data: True``). When
``stuffplus.serving`` (HACK-031) is importable and reports ``available()``, calls are dispatched to it and
``demo_data`` becomes False. The output keys below are the contract; serving must return the same keys.

Air density ``rho`` is relative to sea level (1.0). Movement measured in one air is translated to the
target air (Magnus break ∝ rho), so a coach can type the IVB they saw in CDMX (``rho_measured``).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from stuffplus.schema import PITCH_TYPES

# Provisional presets; HACK-004 owns the measured values in stuffplus.physics.constants.
_RHO_FALLBACK = {
    "sea_level": 1.0,
    "harp_helu": 0.81,  # lowest-density Extreme park in the data (prototype, 2024-2026)
    "extreme_altitude": 0.84,  # median Extreme / No Altitude fastball drag
    "medium_altitude": 0.89,
    "coors": 0.85,  # 1,609 m, barometric estimate
}

PROB_KEYS = ("whiff", "chase", "called_strike", "weak_contact", "groundball", "hard_contact", "out_in_pa")
PREDICTION_KEYS = (
    "stuff_plus", "stuff_plus_neutral", "location_plus", "pitching_plus", "xrv", "probs",
    "movement_expected", "rho", "flavour", "model_version", "demo_data",
)
FLAVOURS = ("environment", "neutral")


def rho_presets() -> dict[str, float]:
    """Named air densities; measured values from stuffplus.physics.constants override the fallback."""
    presets = dict(_RHO_FALLBACK)
    try:
        from stuffplus.physics import constants as c  # HACK-004
    except ImportError:
        return presets
    for name, attr in (("sea_level", "RHO_SEA_LEVEL"), ("harp_helu", "RHO_HARP_HELU"), ("coors", "RHO_COORS")):
        if hasattr(c, attr):
            presets[name] = float(getattr(c, attr))
    return presets


def resolve_rho(rho: float | str) -> float:
    if isinstance(rho, str):
        presets = rho_presets()
        if rho not in presets:
            raise ValueError(f"unknown rho preset {rho!r}; use one of {sorted(presets)} or a float")
        return presets[rho]
    value = float(rho)
    if not 0.6 <= value <= 1.2:
        raise ValueError(f"rho={value} outside the plausible range 0.6–1.2 (relative to sea level)")
    return value


@dataclass
class PitchInput:
    """One pitch as a coach or scout would describe it. Units follow Trackman (mph, rpm, deg, in, ft).

    ``hb`` uses Trackman's sign (catcher's view, + toward first base); ``rel_side`` likewise.
    ``rho_measured`` is the air in which ``ivb``/``hb`` were measured (1.0 = sea level).
    """

    pitch_type: str
    throws: str
    velo: float
    spin_rate: float
    spin_axis: float
    ivb: float
    hb: float
    rel_height: float = 5.8
    rel_side: float = 1.8
    extension: float = 6.1
    rho_measured: float = 1.0
    plate_x: float | None = None
    plate_z: float | None = None
    balls: int | None = None
    strikes: int | None = None
    batter_side: str | None = None
    arsenal: dict[str, Any] = field(default_factory=dict)  # e.g. {"fb_velo": 95, "fb_ivb": 17, "usage": 0.2}

    def __post_init__(self) -> None:
        if self.pitch_type not in PITCH_TYPES:
            raise ValueError(f"pitch_type must be one of {PITCH_TYPES}")
        if self.throws not in ("Right", "Left"):
            raise ValueError("throws must be 'Right' or 'Left'")
        for name, lo, hi in (("velo", 55, 106), ("spin_rate", 300, 3800), ("spin_axis", 0, 360),
                             ("ivb", -35, 35), ("hb", -35, 35), ("extension", 3.5, 8.5)):
            v = getattr(self, name)
            if not lo <= v <= hi:
                raise ValueError(f"{name}={v} outside {lo}–{hi}")

    @classmethod
    def from_row(cls, row: Mapping[str, Any], rho_measured: float = 1.0) -> "PitchInput":
        """Build from a cleaned data row (``schema.clean`` output)."""
        return cls(
            pitch_type=str(row["AutoPitchType"]), throws=str(row["PitcherThrows"]), velo=float(row["RelSpeed"]),
            spin_rate=float(row["SpinRate"]), spin_axis=float(row["SpinAxis"]) % 360,
            ivb=float(row["InducedVertBreak"]), hb=float(row["HorzBreak"]), rel_height=float(row["RelHeight"]),
            rel_side=float(row["RelSide"]), extension=float(row["Extension"]), rho_measured=rho_measured,
            plate_x=float(row["PlateLocSide"]), plate_z=float(row["PlateLocHeight"]),
            balls=int(row["Balls"]), strikes=int(row["Strikes"]), batter_side=str(row["BatterSide"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _mock_predict(p: PitchInput, rho: float, flavour: str) -> dict[str, Any]:
    """Deterministic placeholder with the right physics direction. NOT a model: demo_data is True."""

    def stuff_score(r: float) -> tuple[float, float, float]:
        scale = r / p.rho_measured
        ivb, hb = p.ivb * scale, p.hb * scale
        brk = math.hypot(ivb, hb)
        fastball = p.pitch_type in ("Four-Seam", "Sinker", "Cutter")
        s = (0.45 * (p.velo - (92.0 if fastball else 84.0)) / 2.5
             + 0.35 * (brk - (15.0 if fastball else 13.0)) / 5.0
             + 0.20 * (p.extension - 6.1) / 0.4)
        return s, ivb, hb

    s_env, ivb_t, hb_t = stuff_score(rho)
    s_neu, _, _ = stuff_score(1.0)
    s = s_env if flavour == "environment" else s_neu
    loc = None
    if p.plate_x is not None and p.plate_z is not None:
        edge = min(abs(abs(p.plate_x) - 0.83), abs(p.plate_z - 1.5), abs(p.plate_z - 3.5))
        loc = round(100 + 10 * (1.0 - edge / 0.5), 1)
    stuff_plus = round(100 + 10 * s, 1)
    pitching_plus = round(0.6 * stuff_plus + 0.4 * loc, 1) if loc is not None else stuff_plus
    probs = {
        "whiff": round(_sigmoid(-1.3 + 0.45 * s), 3),
        "chase": round(_sigmoid(-0.9 + 0.25 * s), 3),
        "called_strike": round(_sigmoid(-1.7 + 0.1 * s), 3),
        "weak_contact": round(_sigmoid(-0.6 + 0.2 * s), 3),
        "groundball": round(_sigmoid(-0.2 - 0.04 * ivb_t), 3),
        "hard_contact": round(_sigmoid(-1.0 - 0.3 * s + 0.8 * (1 - rho)), 3),
        "out_in_pa": round(_sigmoid(0.7 + 0.15 * s), 3),
    }
    return {
        "stuff_plus": stuff_plus,
        "stuff_plus_neutral": round(100 + 10 * s_neu, 1),
        "location_plus": loc,
        "pitching_plus": pitching_plus,
        "xrv": round(-0.012 * s, 4),
        "probs": probs,
        "movement_expected": {"ivb": round(ivb_t, 2), "hb": round(hb_t, 2)},
        "rho": rho,
        "flavour": flavour,
        "model_version": "mock-0",
        "demo_data": True,
    }


def predict_pitch(p: PitchInput, rho: float | str = "harp_helu", flavour: str = "environment") -> dict[str, Any]:
    """Score one pitch in the air ``rho``. ``flavour='neutral'`` scores it at sea level whatever ``rho`` is.

    Returns a dict with exactly ``PREDICTION_KEYS``; ``probs`` has ``PROB_KEYS``. Location+ is None when no
    plate location is given. ``stuff_plus - stuff_plus_neutral`` is the altitude effect for this pitch.
    """
    if flavour not in FLAVOURS:
        raise ValueError(f"flavour must be one of {FLAVOURS}")
    r = resolve_rho(rho)
    try:
        from stuffplus import serving  # HACK-031
    except ImportError:
        serving = None
    if serving is not None and getattr(serving, "available", lambda: False)():
        return serving.predict_pitch(p, rho=r, flavour=flavour)
    return _mock_predict(p, r, flavour)


def compare_environments(p: PitchInput, a: float | str = "harp_helu", b: float | str = "sea_level") -> dict[str, Any]:
    """Side-by-side for the simulator: the same pitch in air ``a`` vs air ``b``, plus the deltas."""
    ra, rb = predict_pitch(p, a), predict_pitch(p, b)
    return {
        "a": ra, "b": rb,
        "delta_stuff_plus": round(ra["stuff_plus"] - rb["stuff_plus"], 1),
        "delta_ivb": round(ra["movement_expected"]["ivb"] - rb["movement_expected"]["ivb"], 2),
        "delta_hb": round(ra["movement_expected"]["hb"] - rb["movement_expected"]["hb"], 2),
        "demo_data": ra["demo_data"] or rb["demo_data"],
    }
