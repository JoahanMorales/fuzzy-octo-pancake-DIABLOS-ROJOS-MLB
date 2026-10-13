"""Synthetic pitch-by-pitch data with the SAME 84 columns and dtypes as the ISAC parquet.

No real row is used. Games are simulated in order (count, outs, runners, runs), so every downstream
module can be tested without the raw data:

* 6 teams, each with a home park: 2 "No Altitude", 2 "Medium Altitude", 2 "Extreme Altitude".
  Park air density ``rho`` (sea level = 1.0) scales drag and Magnus break, like the real data
  (Extreme games show ~16 % less drag and ~3.7" less four-seam ride for the same pitcher).
* Fixed 9-man lineups (+1 bench bat) so teams can be recovered from batter co-appearance (HACK-003).
  The home team pitches the Top half and bats the Bottom half.
* Pitchers have stable arsenals; whiff probability depends on velocity and break, so models can learn.
* A few edge cases that ``schema.clean`` must handle: one game with NaN altitude, ``Undefined`` hands,
  a ``Switch`` batter, ``Sweeper`` and ``Other`` pitch types.

Trackman frame note (true for the real file too): ``PitchTrajectory{X,Y,Z}c*`` use X = distance toward
the plate, Y = height, Z = side (Zc0 ~ -RelSide), unlike ``x0/y0/z0`` (x = side, y = toward plate = 50 ft,
z = height). ``c2`` coefficients are half the acceleration.

Run as a script to write a parquet for local demos: ``python -m tests.fixtures.synthetic out.parquet``.
"""
from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

G = 32.174  # ft/s^2
KD_SEA = 0.0016  # drag coefficient proxy (1/ft) at sea level, matches the real data's median
DICT = pa.dictionary(pa.int8(), pa.string())

SCHEMA = pa.schema([
    ("year", pa.int32()), ("PitchUID", pa.string()), ("game_anon_id", pa.string()),
    ("pitcher_anon_id", pa.string()), ("batter_anon_id", pa.string()), ("catcher_anon_id", pa.string()),
    ("PitcherThrows", pa.string()), ("BatterSide", pa.string()), ("altitude_category", pa.string()),
    ("AutoPitchType", DICT), ("RelSpeed", pa.float64()), ("EffectiveVelo", pa.string()),
    ("ZoneSpeed", pa.float64()), ("SpinRate", pa.float64()), ("SpinAxis", pa.float64()), ("Tilt", pa.string()),
    ("RelHeight", pa.float64()), ("RelSide", pa.float64()), ("Extension", pa.float64()),
    ("VertBreak", pa.float64()), ("InducedVertBreak", pa.float64()), ("HorzBreak", pa.float64()),
    ("VertRelAngle", pa.float64()), ("HorzRelAngle", pa.float64()), ("VertApprAngle", pa.float64()),
    ("HorzApprAngle", pa.float64()), ("SpeedDrop", pa.float64()), ("ZoneTime", pa.float64()),
    ("x0", pa.float64()), ("y0", pa.float64()), ("z0", pa.float64()),
    ("vx0", pa.float64()), ("vy0", pa.float64()), ("vz0", pa.float64()),
    ("ax0", pa.float64()), ("ay0", pa.float64()), ("az0", pa.float64()),
    ("pfxx", pa.float64()), ("pfxz", pa.float64()),
    ("PitchTrajectoryXc0", pa.float64()), ("PitchTrajectoryXc1", pa.float64()), ("PitchTrajectoryXc2", pa.float64()),
    ("PitchTrajectoryYc0", pa.float64()), ("PitchTrajectoryYc1", pa.float64()), ("PitchTrajectoryYc2", pa.float64()),
    ("PitchTrajectoryZc0", pa.float64()), ("PitchTrajectoryZc1", pa.float64()), ("PitchTrajectoryZc2", pa.float64()),
    ("PitchCall", DICT), ("KorBB", pa.string()), ("play_result", DICT), ("hit_type", pa.string()),
    ("ExitSpeed", pa.float64()), ("Angle", pa.float64()), ("Direction", pa.float64()), ("Distance", pa.float64()),
    ("is_swing", pa.float64()), ("is_whiff", pa.float64()), ("is_contact", pa.float64()),
    ("is_called_strike", pa.float64()), ("is_swinging_strike", pa.float64()), ("is_ball_in_play", pa.float64()),
    ("is_batted", pa.float64()), ("is_hit", pa.float64()), ("single", pa.float64()), ("double", pa.float64()),
    ("triple", pa.float64()), ("home_run", pa.float64()), ("base_on_balls", pa.float64()),
    ("strikeout", pa.float64()), ("is_hit_by_pitch", pa.float64()), ("RunsScored", pa.float64()),
    ("OutsOnPlay", pa.float64()), ("Inning", pa.float64()), ("Top/Bottom", DICT), ("Outs", pa.float64()),
    ("Balls", pa.float64()), ("Strikes", pa.float64()), ("count", pa.string()),
    ("PlateLocHeight", pa.float64()), ("PlateLocSide", pa.float64()), ("in_strike_zone", pa.int32()),
    ("outside_strike_zone", pa.float64()), ("swung_outside_strike_zone", pa.float64()),
])

PARKS = [  # (altitude bucket, park air density relative to sea level)
    ("No Altitude", 1.00), ("No Altitude", 1.02), ("Medium Altitude", 0.90),
    ("Medium Altitude", 0.88), ("Extreme Altitude", 0.84), ("Extreme Altitude", 0.81),
]
# pitch type: (velo offset vs FB, spin, IVB at sea level, HB arm-side at sea level, spin axis for RHP)
PITCH_SHAPES = {
    "Four-Seam": (0.0, 2300, 16.0, 8.0, 210),
    "Sinker": (-1.0, 2150, 7.0, 15.0, 235),
    "Cutter": (-4.5, 2400, 9.0, -2.0, 180),
    "Slider": (-8.0, 2450, 1.0, -6.0, 90),
    "Curveball": (-13.0, 2550, -9.0, -7.0, 40),
    "Changeup": (-8.5, 1750, 6.0, 14.0, 240),
    "Splitter": (-7.5, 1400, 3.0, 9.0, 220),
}
SECONDARIES = ["Slider", "Curveball", "Changeup", "Cutter", "Splitter"]


def _pitchers(rng, n_teams, per_team):
    out = {}
    for t in range(n_teams):
        for i in range(per_team):
            pid = f"pitcher_{t * per_team + i:05d}"
            throws = "Right" if rng.random() < 0.75 else "Left"
            fb = "Four-Seam" if rng.random() < 0.65 else "Sinker"
            sec = list(rng.choice(SECONDARIES, size=int(rng.integers(2, 4)), replace=False))
            types = [fb] + sec
            usage = np.array([0.5] + [0.5 / len(sec)] * len(sec))
            out[pid] = dict(
                team=t, throws=throws, types=types, usage=usage, velo=rng.normal(92.5, 2.2),
                rel_h=rng.normal(5.8, 0.3), rel_s=abs(rng.normal(1.8, 0.4)), ext=rng.normal(6.1, 0.35),
                ride=rng.normal(1.0, 0.12), sweep=rng.normal(1.0, 0.15), spin=rng.normal(1.0, 0.06),
            )
    return out


def _tilt(axis):
    minutes = round(((axis / 30.0 + 6.0) % 12.0) * 60 / 15) * 15
    h, m = divmod(int(minutes) % 720, 60)
    return f"{h or 12}:{m:02d}"


def _physics(rng, p, ptype, rho):
    """One pitch's release, movement and 9-parameter trajectory at air density rho."""
    dv, spin, ivb0, hb0, axis = PITCH_SHAPES[ptype]
    hand = 1.0 if p["throws"] == "Right" else -1.0
    velo = p["velo"] + dv + rng.normal(0, 0.8)
    spin_rate = spin * p["spin"] + rng.normal(0, 60)
    ivb = (ivb0 * (p["ride"] if ptype in ("Four-Seam", "Sinker") else 1.0) + rng.normal(0, 1.2)) * rho
    hb = hand * (hb0 * (p["sweep"] if ptype in ("Slider", "Sinker") else 1.0) + rng.normal(0, 1.2)) * rho
    axis_deg = (axis if hand > 0 else 360 - axis) + rng.normal(0, 8)
    rel_h = p["rel_h"] + rng.normal(0, 0.08)
    rel_s = hand * p["rel_s"] + rng.normal(0, 0.08)
    ext = p["ext"] + rng.normal(0, 0.1)

    v0 = velo * 1.46667  # ft/s
    vx0 = -rel_s * 1.6 + hand * rng.normal(1.5, 1.0)
    vz0 = rng.normal(-3.3, 1.2)
    vy0 = -math.sqrt(max(v0 ** 2 - vx0 ** 2 - vz0 ** 2, 1.0))
    t_flight = 50.0 / abs(vy0)
    mag_x = 2 * (hb / 12.0) / t_flight ** 2
    mag_z = 2 * (ivb / 12.0) / t_flight ** 2
    kd = KD_SEA * rho * (1 + rng.normal(0, 0.03))
    ax0 = -kd * v0 * vx0 + mag_x
    ay0 = -kd * v0 * vy0
    az0 = -kd * v0 * vz0 + mag_z - G
    speed_drop = velo * (1 - math.exp(-kd * 55.0))
    vy_p, vz_p, vx_p = vy0 + ay0 * t_flight, vz0 + az0 * t_flight, vx0 + ax0 * t_flight
    zone_speed = velo - speed_drop
    return dict(
        RelSpeed=velo, EffectiveVelo=f"{velo + (ext - 6.0) * 0.8:.5f}", ZoneSpeed=zone_speed,
        SpinRate=spin_rate, SpinAxis=axis_deg % 360, Tilt=_tilt(axis_deg % 360),
        RelHeight=rel_h, RelSide=rel_s, Extension=ext,
        VertBreak=ivb - 0.5 * G * t_flight ** 2 * 12, InducedVertBreak=ivb, HorzBreak=hb,
        VertRelAngle=math.degrees(math.atan2(vz0, abs(vy0))), HorzRelAngle=math.degrees(math.atan2(vx0, abs(vy0))),
        VertApprAngle=math.degrees(math.atan2(vz_p, abs(vy_p))), HorzApprAngle=math.degrees(math.atan2(vx_p, abs(vy_p))),
        SpeedDrop=speed_drop, ZoneTime=55.0 / ((velo + zone_speed) / 2 * 1.46667),
        x0=-rel_s, y0=50.0, z0=rel_h - 0.1, vx0=vx0, vy0=vy0, vz0=vz0, ax0=ax0, ay0=ay0, az0=az0,
        pfxx=hb * 0.5, pfxz=ivb * 0.5,
        PitchTrajectoryXc0=60.5 - ext, PitchTrajectoryXc1=vy0, PitchTrajectoryXc2=ay0 / 2,
        PitchTrajectoryYc0=rel_h, PitchTrajectoryYc1=vz0, PitchTrajectoryYc2=az0 / 2,
        PitchTrajectoryZc0=-rel_s, PitchTrajectoryZc1=vx0, PitchTrajectoryZc2=ax0 / 2,
    )


def _advance(bases, kind):
    """Return (new bases, runs) for a simple base-running model."""
    b1, b2, b3 = bases
    if kind == "HomeRun":
        return (0, 0, 0), 1 + b1 + b2 + b3
    if kind == "Triple":
        return (0, 0, 1), b1 + b2 + b3
    if kind == "Double":
        return (0, 1, b1), b2 + b3
    if kind == "Single":
        return (1, b1, b2), b3
    if kind == "Walk":  # also HBP: forced runners only
        return (1, int(b1 or b2), int(b3 or (b1 and b2))), int(b1 and b2 and b3)
    return bases, 0


def make_synthetic_pitches(seed: int = 2240, n_innings: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_teams = len(PARKS)
    pitchers = _pitchers(rng, n_teams, 7)
    staff = {t: [p for p, v in pitchers.items() if v["team"] == t] for t in range(n_teams)}
    batters = {t: [f"batter_{t * 10 + i:05d}" for i in range(10)] for t in range(n_teams)}
    bat_side = {b: ("Right" if rng.random() < 0.6 else "Left") for bs in batters.values() for b in bs}
    bat_side[batters[0][9]] = "Switch"
    rows, game_no, uid = [], 0, 0
    for year in (2024, 2025, 2026):
        for g in range(12):
            home, away = (g % n_teams), (g * 2 + 1 + year) % n_teams
            if away == home:
                away = (home + 1) % n_teams
            game_no += 1
            game = f"game_{game_no:06d}"
            bucket, park_rho = PARKS[home]
            rho = park_rho * (1 + rng.normal(0, 0.015))
            if year == 2025 and g == 0:
                bucket = None  # edge case: unknown altitude
            lineups = {t: list(rng.permutation(batters[t])[:9]) for t in (home, away)}
            spot = {home: 0, away: 0}
            score_arms = {home: list(rng.choice(staff[home], 2, replace=False)),
                          away: list(rng.choice(staff[away], 2, replace=False))}
            for inning in range(1, n_innings + 1):
                for half in ("Top", "Bottom"):
                    bat_team, field_team = (away, home) if half == "Top" else (home, away)
                    pid = score_arms[field_team][0 if inning <= 3 else 1]
                    p = pitchers[pid]
                    catcher = f"catcher_{field_team * 2 + (inning % 2):05d}"
                    outs, bases = 0, (0, 0, 0)
                    while outs < 3:
                        batter = lineups[bat_team][spot[bat_team] % 9]
                        spot[bat_team] += 1
                        side = bat_side[batter]
                        if side == "Switch":
                            side = "Left" if p["throws"] == "Right" else "Right"
                        balls = strikes = 0
                        pa_over = False
                        while not pa_over:
                            uid += 1
                            ptype = str(rng.choice(p["types"], p=p["usage"]))
                            phys = _physics(rng, p, ptype, rho)
                            plate_h, plate_s = rng.normal(2.45, 0.95), rng.normal(0.0, 0.9)
                            in_zone = int(abs(plate_s) < 0.83 and 1.5 < plate_h < 3.5)
                            stuff = 0.09 * (phys["RelSpeed"] - 88) + 0.05 * (abs(phys["InducedVertBreak"]) + abs(phys["HorzBreak"]) - 15)
                            swing_p = (0.66 if in_zone else 0.28) + (0.12 if strikes == 2 else 0.0)
                            swing = rng.random() < swing_p
                            rec = dict(
                                year=year, PitchUID=f"{uid:08x}-0000-11ee-8e28-{game_no:012x}", game_anon_id=game,
                                pitcher_anon_id=pid, batter_anon_id=batter, catcher_anon_id=catcher,
                                PitcherThrows=p["throws"], BatterSide=bat_side[batter], altitude_category=bucket,
                                AutoPitchType=ptype, **phys,
                                Inning=float(inning), **{"Top/Bottom": half}, Outs=float(outs), Balls=float(balls),
                                Strikes=float(strikes), count=f"{balls}-{strikes}", PlateLocHeight=plate_h,
                                PlateLocSide=plate_s, in_strike_zone=in_zone, outside_strike_zone=float(1 - in_zone),
                                KorBB="Undefined", hit_type=None, ExitSpeed=np.nan, Angle=np.nan, Direction=np.nan,
                                Distance=np.nan, RunsScored=0.0, OutsOnPlay=0.0,
                            )
                            for f in ("is_swing", "is_whiff", "is_contact", "is_called_strike", "is_swinging_strike",
                                      "is_ball_in_play", "is_batted", "is_hit", "single", "double", "triple",
                                      "home_run", "base_on_balls", "strikeout", "is_hit_by_pitch"):
                                rec[f] = 0.0
                            rec["is_swing"] = float(swing)
                            rec["swung_outside_strike_zone"] = float(swing and not in_zone)
                            if swing:
                                whiff_p = 1 / (1 + math.exp(-(-1.35 + stuff - (0.5 if in_zone else -0.4))))
                                if rng.random() < whiff_p:
                                    call = "StrikeSwinging"
                                    rec.update(is_whiff=1.0, is_swinging_strike=1.0)
                                    strikes += 1
                                    result = "StrikeSwinging"
                                elif rng.random() < 0.47:
                                    call = "FoulBallNotFieldable" if rng.random() < 0.93 else "FoulBallFieldable"
                                    rec.update(is_contact=1.0, is_batted=1.0)
                                    strikes = min(strikes + 1, 2)
                                    result = "NeutralPlay" if call == "FoulBallNotFieldable" else "FoulBallFieldable"
                                else:
                                    call = "InPlay"
                                    ev, la = rng.normal(87 - 2 * stuff, 12), rng.normal(12, 24)
                                    ht = ("GroundBall" if la < 10 else "LineDrive" if la < 25 else "FlyBall" if la < 50 else "Popup")
                                    hr_p = 1 / (1 + math.exp(-(ev - 101) / 3.0)) * (1 / rho) ** 2 if ht == "FlyBall" else 0.0
                                    hit_p = {"GroundBall": 0.23, "LineDrive": 0.62, "FlyBall": 0.12, "Popup": 0.02}[ht]
                                    if rng.random() < min(hr_p, 0.95):
                                        result = "HomeRun"
                                    elif rng.random() < hit_p:
                                        result = str(rng.choice(["Single", "Double", "Triple"], p=[0.74, 0.23, 0.03]))
                                    else:
                                        result = "Out"
                                    dist = max(0.0, ev * 2.9 * math.sin(math.radians(2 * max(la, 1))) / max(rho, 0.5) ** 0.5)
                                    rec.update(is_contact=1.0, is_batted=1.0, is_ball_in_play=1.0, hit_type=ht,
                                               ExitSpeed=ev, Angle=la, Direction=rng.normal(0, 25), Distance=dist)
                                    if result == "Out":
                                        rec["OutsOnPlay"] = 1.0
                                        outs += 1
                                    else:
                                        rec["is_hit"] = 1.0
                                        rec[{"Single": "single", "Double": "double", "Triple": "triple", "HomeRun": "home_run"}[result]] = 1.0
                                        bases, runs = _advance(bases, result)
                                        rec["RunsScored"] = float(runs)
                                    pa_over = True
                            else:
                                r = rng.random()
                                if in_zone and r < 0.95:
                                    call, result = "StrikeCalled", "NeutralPlay"
                                    rec["is_called_strike"] = 1.0
                                    strikes += 1
                                elif not in_zone and r < 0.012:
                                    call, result = "HitByPitch", "HitByPitch"
                                    rec["is_hit_by_pitch"] = 1.0
                                    bases, runs = _advance(bases, "Walk")
                                    rec["RunsScored"] = float(runs)
                                    pa_over = True
                                else:
                                    call = "BallinDirt" if plate_h < 0.4 else "BallCalled"
                                    result = call
                                    balls += 1
                            if not pa_over and strikes == 3:
                                result = "Strikeout"
                                rec.update(strikeout=1.0, KorBB="Strikeout", OutsOnPlay=1.0)
                                outs += 1
                                pa_over = True
                            elif not pa_over and balls == 4:
                                result = "Walk"
                                rec.update(base_on_balls=1.0, KorBB="Walk")
                                bases, runs = _advance(bases, "Walk")
                                rec["RunsScored"] = float(runs)
                                pa_over = True
                            rec["PitchCall"], rec["play_result"] = call, result
                            rows.append(rec)
                            if outs >= 3:
                                break
    df = pd.DataFrame(rows)
    # edge cases for schema.clean
    edge = rng.choice(len(df), size=12, replace=False)
    df.loc[edge[:4], "PitcherThrows"] = "Undefined"
    df.loc[edge[4:7], "BatterSide"] = "Undefined"
    df.loc[edge[7:12], "AutoPitchType"] = "Other"
    sweeper_pitcher = next(pid for pid, v in pitchers.items() if "Slider" in v["types"])
    df.loc[(df.pitcher_anon_id == sweeper_pitcher) & (df.AutoPitchType == "Slider") & (df.year == 2026), "AutoPitchType"] = "Sweeper"
    table = pa.Table.from_pandas(df[SCHEMA.names], schema=SCHEMA, preserve_index=False)
    return table.to_pandas()


def write_parquet(df: pd.DataFrame, path) -> None:
    """Write with the exact raw schema (pandas alone would write large_string columns)."""
    pq.write_table(pa.Table.from_pandas(df[SCHEMA.names], schema=SCHEMA, preserve_index=False), path)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "synthetic_pitches.parquet"
    write_parquet(make_synthetic_pitches(), out)
    print(f"wrote {out}")
