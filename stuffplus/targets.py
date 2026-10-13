"""Model targets and the LMB-calibrated run value per pitch (HACK-030).

The data has no base-runner state, so classic RE24 is impossible. Instead:

* ``RE(o, b, s)``: mean runs scored from this pitch to the end of the half-inning, by outs and count, on
  complete half-innings. Observed future runs already average over the runners on base.
* ``LW[event]``: linear weight of each plate-appearance outcome, relative to the start of a PA:
  ``mean(runs_to_end | event) - RE(o, 0, 0)``. Runner advancement is included through the future runs.
* Pitch run value (batter's view; negative is good for the pitcher):
  - non-terminal pitch: ``RE(o, b', s') - RE(o, b, s)`` (count transition; a 2-strike foul is 0);
  - PA-ending pitch: ``LW[event] - (RE(o, b, s) - RE(o, 0, 0))``.
  Summed over a PA this telescopes to ``LW[event]``. Using expected values per state and event (not the
  observed runs of each pitch) is what makes it a stable "xRunValue".
* ``rv_delta``: the noisy observed version (runs on the pitch + RE of the next observed state - RE now).

Targets are named ``t_*`` and defined on their natural denominator (NaN elsewhere): e.g. ``t_whiff`` only on
swings. Unconditional rates follow by multiplication, e.g. P(whiff) = P(swing) · P(whiff | swing).

``python -m stuffplus.targets`` writes the LMB tables to ``reports/targets/``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stuffplus.config import REPORTS_DIR

OUT_EVENTS = ("Strikeout", "Out", "FieldersChoice", "Sacrifice")
HIT_EVENTS = ("Single", "Double", "Triple", "HomeRun")
EVENTS = HIT_EVENTS + ("Walk", "HitByPitch", "Error") + OUT_EVENTS
WEAK_EV, HARD_EV, HARD_LA = 88.0, 95.0, (8.0, 32.0)

# MLB 2024 wOBA linear weights (runs relative to an out, times wOBAScale). UNVERIFIED: taken from a web-search
# snapshot of the FanGraphs Guts! table on 2026-10-13; fangraphs.com blocked direct access. Re-check before
# quoting: https://www.fangraphs.com/tools/guts?type=cn
MLB_REFERENCE = {
    "season": 2024, "wOBAScale": 1.242, "R/PA": 0.117,
    "weights": {"Walk": 0.689, "HitByPitch": 0.720, "Single": 0.882, "Double": 1.254, "Triple": 1.590, "HomeRun": 2.050},
    "source": "FanGraphs Guts! wOBA and FIP constants, 2024 (web-search snapshot)",
    "verified": False,
}

TARGETS = {  # name: (description, denominator)
    "t_swing": ("batter swings", "all pitches"),
    "t_whiff": ("swing and miss", "swings"),
    "t_chase": ("swing at a pitch outside the zone", "pitches outside the zone"),
    "t_called_strike": ("called strike", "takes (no swing)"),
    "t_weak_contact": (f"exit velocity < {WEAK_EV:.0f} mph or popup", "balls in play with tracking"),
    "t_groundball": ("ground ball", "balls in play (bunts excluded)"),
    "t_hard_contact": (f"EV >= {HARD_EV:.0f} mph and launch angle {HARD_LA[0]:.0f}-{HARD_LA[1]:.0f} deg", "balls in play with tracking"),
    "t_out_in_pa": ("the plate appearance ends in an out", "pitches of PAs with a known ending"),
}


def _state(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(outs, balls, strikes) clipped to valid ranges (a few raw rows have 3 outs before the pitch)."""
    return (df["Outs"].clip(0, 2).to_numpy(float), df["Balls"].clip(0, 3).to_numpy(float),
            df["Strikes"].clip(0, 2).to_numpy(float))


def _half_key(df: pd.DataFrame) -> pd.Series:
    return df["game_anon_id"].astype(str) + "|" + df["Inning"].astype(int).astype(str) + "|" + df["Top/Bottom"].astype(str)


def pa_event(df: pd.DataFrame) -> pd.Series:
    """Event that ends the PA on this pitch (None for non-terminal pitches)."""
    call = df["PitchCall"].astype(str)
    result = df["play_result"].astype(str)
    korbb = df["KorBB"].astype(str)
    ev = pd.Series(None, index=df.index, dtype=object)
    in_play = call.eq("InPlay")
    ev[in_play] = np.where(result[in_play].isin(EVENTS), result[in_play], "Out")
    ev[call.eq("HitByPitch")] = "HitByPitch"
    ev[korbb.eq("Walk")] = "Walk"
    ev[korbb.eq("Strikeout")] = "Strikeout"
    return ev


def _next_count(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    call = df["PitchCall"].astype(str).to_numpy()
    _, b, s = _state(df)
    ball = np.isin(call, ("BallCalled", "BallinDirt", "BallIntentional", "AutomaticBall"))
    strike = np.isin(call, ("StrikeCalled", "StrikeSwinging", "AutomaticStrike"))
    foul = np.char.startswith(call.astype(str), "FoulBall")
    b2 = np.where(ball, b + 1, b)
    s2 = np.where(strike, s + 1, np.where(foul, np.minimum(s + 1, 2), s))
    return np.minimum(b2, 3), np.minimum(s2, 2)


def runs_to_end_of_half(df: pd.DataFrame) -> pd.Series:
    """Runs scored from this pitch (included) to the end of its half-inning, in row order."""
    half = _half_key(df)
    runs = df["RunsScored"].fillna(0.0)
    return runs[::-1].groupby(half[::-1], sort=False).cumsum()[::-1]


def complete_halves(df: pd.DataFrame) -> pd.Series:
    """True for rows of half-innings that reach 3 outs (walk-off and truncated halves are excluded)."""
    half = _half_key(df)
    final_outs = (df["Outs"] + df["OutsOnPlay"].fillna(0)).groupby(half).transform("max")
    return final_outs >= 3


def fit_run_expectancy(df: pd.DataFrame, min_n: int = 30) -> pd.DataFrame:
    """RE table indexed by (Outs, Balls, Strikes) with columns re, n."""
    ok = complete_halves(df)
    o, b, s = _state(df)
    d = pd.DataFrame({"Outs": o, "Balls": b, "Strikes": s, "r": runs_to_end_of_half(df).to_numpy()})[ok.to_numpy()]
    re = d.groupby(["Outs", "Balls", "Strikes"]).r.agg(re="mean", n="size")
    full = pd.MultiIndex.from_product([[0.0, 1.0, 2.0], [0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 2.0]], names=re.index.names)
    re = re.reindex(full)
    sparse = re["n"].fillna(0) < min_n  # back off to the outs-level mean for unseen / rare states
    re.loc[sparse, "re"] = d.groupby("Outs").r.mean().reindex(re.index.get_level_values("Outs"))[sparse.to_numpy()].to_numpy()
    re["n"] = re["n"].fillna(0).astype(int)
    return re


def fit_linear_weights(df: pd.DataFrame, re: pd.DataFrame) -> pd.DataFrame:
    """Linear weight per PA event, relative to the RE at the start of a PA with the same outs."""
    ok = complete_halves(df)
    ev = pa_event(df)
    r_end = runs_to_end_of_half(df)
    start = re["re"].xs((0.0, 0.0), level=("Balls", "Strikes"))
    val = r_end - pd.Series(_state(df)[0], index=df.index).map(start)
    d = pd.DataFrame({"event": ev, "val": val})[ok & ev.notna()]
    lw = d.groupby("event").val.agg(lw="mean", sd="std", n="size")
    lw["se"] = lw["sd"] / np.sqrt(lw["n"])
    return lw.drop(columns="sd").reindex([e for e in EVENTS if e in lw.index])


def add_run_value(df: pd.DataFrame, re: pd.DataFrame | None = None, lw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return a copy with ``event``, ``re_before``, ``rv`` (stable, expected) and ``rv_delta`` (observed)."""
    out = df.copy()
    re = fit_run_expectancy(out) if re is None else re
    lw = fit_linear_weights(out, re) if lw is None else lw
    re_map = re["re"].to_dict()
    o, b, s = _state(out)
    re_now = np.array([re_map[k] for k in zip(o, b, s)])
    re_start = np.array([re_map[(k, 0.0, 0.0)] for k in o])
    b2, s2 = _next_count(out)
    re_next = np.array([re_map[k] for k in zip(o, b2, s2)])
    ev = pa_event(out)
    lw_map = lw["lw"].to_dict()
    terminal = ev.notna().to_numpy()
    lw_val = ev.map(lw_map).astype(float).to_numpy()
    rv = np.where(terminal, lw_val - (re_now - re_start), re_next - re_now)
    out["event"] = ev
    out["re_before"] = re_now
    out["rv"] = rv

    # observed version: runs on the pitch + RE of the next row's state (same half) - RE now
    half = _half_key(out)
    same_half_next = half.eq(half.shift(-1)).to_numpy()
    re_next_obs = np.where(same_half_next, np.roll(re_now, -1), 0.0)
    out["rv_delta"] = out["RunsScored"].fillna(0.0).to_numpy() + re_next_obs - re_now
    return out


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with every ``t_*`` target (NaN outside its denominator). Needs ``pa_id`` (schema.clean)."""
    out = df.copy()
    call = out["PitchCall"].astype(str)
    swing = out["is_swing"].astype(float)
    outside = out["outside_strike_zone"].astype(float).eq(1.0)
    in_play = call.eq("InPlay")
    ev_speed, la = out["ExitSpeed"].astype(float), out["Angle"].astype(float)
    ht = out["hit_type"].astype(object)
    tracked = in_play & ev_speed.notna()

    out["t_swing"] = swing
    out["t_whiff"] = out["is_whiff"].astype(float).where(swing.eq(1.0))
    out["t_chase"] = swing.where(outside)
    out["t_called_strike"] = out["is_called_strike"].astype(float).where(swing.eq(0.0))
    weak = (ev_speed < WEAK_EV) | ht.eq("Popup")
    out["t_weak_contact"] = weak.astype(float).where(tracked | (in_play & ht.eq("Popup")))
    out["t_groundball"] = ht.eq("GroundBall").astype(float).where(in_play & ht.notna() & ht.ne("Bunt"))
    hard = (ev_speed >= HARD_EV) & la.between(*HARD_LA)
    out["t_hard_contact"] = hard.astype(float).where(tracked)

    ev = pa_event(out)
    pa_out = ev.isin(OUT_EVENTS).astype(float).where(ev.notna())
    out["t_out_in_pa"] = pa_out.groupby(out["pa_id"]).transform("last")
    return out


def lmb_vs_mlb(df: pd.DataFrame, lw: pd.DataFrame) -> pd.DataFrame:
    """Event values relative to an out: LMB (this data) vs MLB 2024 (``MLB_REFERENCE``, flagged unverified).

    FanGraphs wOBA weights are linear weights relative to an out, scaled by wOBAScale, so
    ``w / wOBAScale`` is comparable with ``LW[event] - LW[Out]`` from the LMB data.
    """
    ref = MLB_REFERENCE
    rows = []
    for event, w in ref["weights"].items():
        lmb = float(lw.loc[event, "lw"] - lw.loc["Out", "lw"]) if event in lw.index and "Out" in lw.index else np.nan
        mlb = w / ref["wOBAScale"]
        rows.append({"stat": f"{event} runs vs out", "lmb": lmb, "mlb": mlb, "lmb_over_mlb": lmb / mlb})
    n_pa = int(df["pa_ends"].sum()) if "pa_ends" in df else int(pa_event(df).notna().sum())
    rpa = float(df["RunsScored"].sum()) / max(n_pa, 1)
    rows.append({"stat": "runs per PA", "lmb": rpa, "mlb": ref["R/PA"], "lmb_over_mlb": rpa / ref["R/PA"]})
    out = pd.DataFrame(rows)
    out["mlb_source"] = ref["source"]
    out["mlb_verified"] = ref["verified"]
    return out


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Targets + run value on a cleaned frame. Returns (frame, RE table, linear weights)."""
    re = fit_run_expectancy(df)
    lw = fit_linear_weights(df, re)
    return add_targets(add_run_value(df, re, lw)), re, lw


def write_reports(df: pd.DataFrame, re: pd.DataFrame, lw: pd.DataFrame, out_dir=None) -> None:
    """Aggregated LMB tables only (no pitch-level rows)."""
    out_dir = (REPORTS_DIR / "targets") if out_dir is None else out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    re.round(4).to_csv(out_dir / "re_matrix.csv")
    lmb_vs_mlb(df, lw).round(4).to_csv(out_dir / "lmb_vs_mlb.csv", index=False)
    lw.round(4).to_csv(out_dir / "linear_weights.csv")
    by_alt = []
    for alt, d in df.groupby("altitude_category", observed=True):
        r = fit_run_expectancy(d)
        w = fit_linear_weights(d, r)
        row = {"altitude_category": alt, "pitches": len(d), "re_inning_start": r.loc[(0.0, 0.0, 0.0), "re"]}
        row.update({f"lw_{e}": w.loc[e, "lw"] for e in ("HomeRun", "Single", "Walk", "Strikeout", "Out") if e in w.index})
        by_alt.append(row)
    pd.DataFrame(by_alt).round(4).to_csv(out_dir / "run_environment_by_altitude.csv", index=False)
    rates = {name: df[name].mean() for name in TARGETS}
    pd.DataFrame({"target": list(rates), "rate": list(rates.values()),
                  "denominator_n": [int(df[n].notna().sum()) for n in rates],
                  "definition": [TARGETS[n][0] for n in rates], "denominator": [TARGETS[n][1] for n in rates]}
                 ).round(4).to_csv(out_dir / "target_rates.csv", index=False)
    pd.DataFrame({"stat": ["rv_mean", "rv_sd", "rv_delta_mean", "rv_delta_sd", "corr_rv_rv_delta"],
                  "value": [df.rv.mean(), df.rv.std(), df.rv_delta.mean(), df.rv_delta.std(), df.rv.corr(df.rv_delta)]}
                 ).round(5).to_csv(out_dir / "rv_summary.csv", index=False)


if __name__ == "__main__":
    from stuffplus.io import load_raw
    from stuffplus.schema import clean

    frame, re_table, weights = build(clean(load_raw()))
    write_reports(frame, re_table, weights)
    print(weights.round(3).to_string())
    print(f"RE(0 outs, 0-0) = {re_table.loc[(0.0, 0.0, 0.0), 're']:.3f} runs per half-inning")
