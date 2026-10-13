"""Clean table schema: the single entry point from raw rows to modelling rows.

``clean(load_raw())`` is what every model, analysis and test starts from. Sequence columns are built on
the raw order BEFORE any row is dropped, so dropping an odd pitch never breaks a plate appearance.
Column roles follow ``data/stuff_plus_data_dictionary.csv``.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

HANDS = ("Right", "Left")
ALTITUDE_LEVELS = ("No Altitude", "Medium Altitude", "Extreme Altitude")
DROP_PITCH_TYPES = frozenset({"Other", "OneSeamFastBall", "TwoSeamFastBall", "Knuckleball"})
PITCH_TYPE_MAP = {"Sweeper": "Slider"}  # 588 rows in the raw data; too few for its own class
PITCH_TYPES = ("Four-Seam", "Sinker", "Cutter", "Slider", "Curveball", "Changeup", "Splitter")
FASTBALL_TYPES = ("Four-Seam", "Sinker", "Cutter")
PA_ENDING_CALLS = frozenset({"InPlay", "HitByPitch"})
REQUIRED_PHYSICS = ("RelSpeed", "InducedVertBreak", "HorzBreak")

ID_COLUMNS = ["PitchUID", "game_anon_id", "pitcher_anon_id", "batter_anon_id", "catcher_anon_id", "pa_id"]

# Physical properties at release: the only inputs of pure Stuff+ (plus arsenal features and air density).
PHYSICAL_FEATURES = [
    "RelSpeed", "SpinRate", "SpinAxis", "InducedVertBreak", "HorzBreak",
    "RelHeight", "RelSide", "Extension", "VertRelAngle", "HorzRelAngle",
]
# Derived from the full flight; allowed in Stuff+ only with a written justification (they encode location).
FLIGHT_FEATURES = [
    "EffectiveVelo", "ZoneSpeed", "SpeedDrop", "ZoneTime", "VertApprAngle", "HorzApprAngle", "VertBreak",
    "x0", "y0", "z0", "vx0", "vy0", "vz0", "ax0", "ay0", "az0", "pfxx", "pfxz",
    "PitchTrajectoryXc0", "PitchTrajectoryXc1", "PitchTrajectoryXc2",
    "PitchTrajectoryYc0", "PitchTrajectoryYc1", "PitchTrajectoryYc2",
    "PitchTrajectoryZc0", "PitchTrajectoryZc1", "PitchTrajectoryZc2",
]
LOCATION_FEATURES = ["PlateLocHeight", "PlateLocSide", "in_strike_zone", "outside_strike_zone"]
CONTEXT_FEATURES = [
    "year", "Balls", "Strikes", "Outs", "Inning", "is_rhp", "batter_is_right", "same_side",
    "pitch_number_in_pa", "pitch_idx_in_game", "home_batting",
]
TARGET_COLUMNS = [
    "PitchCall", "KorBB", "play_result", "hit_type", "ExitSpeed", "Angle", "Direction", "Distance",
    "is_swing", "is_whiff", "is_contact", "is_called_strike", "is_swinging_strike", "is_ball_in_play",
    "is_batted", "is_hit", "single", "double", "triple", "home_run", "base_on_balls", "strikeout",
    "is_hit_by_pitch", "RunsScored", "OutsOnPlay", "swung_outside_strike_zone",
    # added by stuffplus.targets (HACK-030)
    "rv", "pa_ends", "out_in_pa",
]


class LeakError(ValueError):
    """A model feature list contains an outcome or identifier column."""


def assert_no_target_leak(features: Iterable[str], allow_location: bool = True) -> None:
    """Raise if ``features`` contains targets or IDs (and location, when ``allow_location`` is False).

    Pure Stuff+ calls this with ``allow_location=False``; Location+ and Pitching+ with the default.
    """
    feats = set(features)
    bad = feats & (set(TARGET_COLUMNS) | set(ID_COLUMNS))
    if not allow_location:
        bad |= feats & (set(LOCATION_FEATURES) | {"Balls", "Strikes", "Outs", "count"})
    if bad:
        raise LeakError(f"features leak outcome/ID/location information: {sorted(bad)}")


def _add_sequence(df: pd.DataFrame) -> pd.DataFrame:
    """Plate-appearance ids and pitch order, on the raw row order (rows are in game order in the data)."""
    call = df["PitchCall"].astype(str)
    ended = call.isin(PA_ENDING_CALLS) | df["KorBB"].astype(str).isin(("Strikeout", "Walk"))
    game = df["game_anon_id"].astype(str)
    new_game = game.ne(game.shift())
    new_pa = (
        new_game
        | df["batter_anon_id"].astype(str).ne(df["batter_anon_id"].astype(str).shift())
        | ended.shift(fill_value=True)
        | df["Inning"].ne(df["Inning"].shift())
        | df["Top/Bottom"].astype(str).ne(df["Top/Bottom"].astype(str).shift())
    )
    pa_seq = new_pa.groupby(game, sort=False).cumsum()
    out = df.copy()
    out["pa_id"] = game + "_pa" + pa_seq.astype(int).astype(str).str.zfill(3)
    out["pitch_number_in_pa"] = out.groupby("pa_id", sort=False).cumcount() + 1
    out["pitch_idx_in_game"] = out.groupby(game, sort=False).cumcount()
    out["pa_ends"] = ended.astype(float)
    return out


def clean(df: pd.DataFrame, drop_missing_physics: bool = True) -> pd.DataFrame:
    """Raw rows → modelling rows. Returns a new frame; ``out.attrs['clean_report']`` counts every drop.

    Drops: unknown altitude, missing pitcher id, ``Undefined``/missing hands, ``Undefined`` pitch calls, pitch types in
    ``DROP_PITCH_TYPES`` and (by default) rows without velocity or movement. Maps Sweeper → Slider and
    Switch batters to the side they faced. Adds ids, handedness and game-state helpers.
    """
    report: dict[str, int] = {"rows_in": int(len(df))}
    out = _add_sequence(df.reset_index(drop=True))

    out["AutoPitchType"] = out["AutoPitchType"].astype(str).replace(PITCH_TYPE_MAP)
    switch = out["BatterSide"].astype(str).eq("Switch")
    out.loc[switch, "BatterSide"] = np.where(out.loc[switch, "PitcherThrows"].astype(str).eq("Right"), "Left", "Right")
    report["switch_batters_mapped"] = int(switch.sum())

    masks = {
        "altitude_missing": ~out["altitude_category"].isin(ALTITUDE_LEVELS),
        "pitcher_id_missing": out["pitcher_anon_id"].isna(),
        "pitcher_hand_unknown": ~out["PitcherThrows"].isin(HANDS),
        "batter_side_unknown": ~out["BatterSide"].isin(HANDS),
        "pitch_call_undefined": out["PitchCall"].astype(str).eq("Undefined"),
        "pitch_type_dropped": out["AutoPitchType"].isin(DROP_PITCH_TYPES) | ~out["AutoPitchType"].isin(PITCH_TYPES),
    }
    if drop_missing_physics:
        masks["physics_missing"] = out[list(REQUIRED_PHYSICS)].isna().any(axis=1)
    drop = np.zeros(len(out), dtype=bool)
    for name, m in masks.items():
        m = m.to_numpy() & ~drop
        report[name] = int(m.sum())
        drop |= m
    out = out.loc[~drop].reset_index(drop=True)

    out["EffectiveVelo"] = pd.to_numeric(out["EffectiveVelo"], errors="coerce")
    out["AutoPitchType"] = pd.Categorical(out["AutoPitchType"], categories=PITCH_TYPES)
    out["altitude_category"] = pd.Categorical(out["altitude_category"], categories=ALTITUDE_LEVELS, ordered=True)
    out["PitcherThrows"] = out["PitcherThrows"].astype(str)
    out["BatterSide"] = out["BatterSide"].astype(str)
    out["is_rhp"] = out["PitcherThrows"].eq("Right").astype(int)
    out["batter_is_right"] = out["BatterSide"].eq("Right").astype(int)
    out["same_side"] = out["is_rhp"].eq(out["batter_is_right"]).astype(int)
    out["home_batting"] = out["Top/Bottom"].astype(str).eq("Bottom").astype(int)
    out["is_fastball"] = out["AutoPitchType"].isin(FASTBALL_TYPES).astype(int)

    report["rows_out"] = int(len(out))
    out.attrs["clean_report"] = report
    return out


def feature_frame(df: pd.DataFrame, features: Iterable[str], allow_location: bool = True) -> pd.DataFrame:
    """Select model inputs after the leak check (categoricals kept as pandas categories for LightGBM)."""
    feats = list(features)
    assert_no_target_leak(feats, allow_location=allow_location)
    missing = [f for f in feats if f not in df.columns]
    if missing:
        raise KeyError(f"missing feature columns: {missing}")
    return df[feats]
