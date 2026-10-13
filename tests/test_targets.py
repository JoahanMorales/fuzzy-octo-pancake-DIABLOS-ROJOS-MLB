"""HACK-030: run expectancy, LMB linear weights, pitch run value and t_* targets."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stuffplus import schema, targets


@pytest.fixture
def built(synthetic_pitches):
    return targets.build(schema.clean(synthetic_pitches))


def test_run_expectancy_shape_and_direction(built):
    _, re, _ = built
    assert len(re) == 36 and re["re"].notna().all()
    by_strikes = re.groupby(level="Strikes").re.mean()
    by_outs = re.groupby(level="Outs").re.mean()
    assert by_strikes[0.0] > by_strikes[2.0]
    assert by_outs[0.0] > by_outs[1.0] > by_outs[2.0]


def test_runs_to_end_of_half_counts_every_run(synthetic_pitches):
    df = schema.clean(synthetic_pitches)
    r = targets.runs_to_end_of_half(df)
    half = targets._half_key(df)
    first = r.groupby(half).first()
    total = df.RunsScored.groupby(half).sum()
    assert np.allclose(first.sort_index(), total.sort_index())


def test_linear_weights_order(built):
    _, _, lw = built
    w = lw["lw"]
    assert w["HomeRun"] > w["Single"] > 0
    assert w["Walk"] > 0
    assert w["Strikeout"] < 0 and w["Out"] < 0


def test_pa_run_values_telescope_to_the_event_weight(built):
    df, _, lw = built
    ends = df[df.event.notna()]
    starts_00 = df.groupby("pa_id")["count"].first().eq("0-0")
    complete = ends[ends.pa_id.map(starts_00)]
    pa_sum = df.groupby("pa_id").rv.sum().reindex(complete.pa_id)
    expected = complete.event.map(lw["lw"]).to_numpy()
    assert np.mean(np.isclose(pa_sum.to_numpy(), expected, atol=1e-9)) > 0.95


def test_rv_is_finite_and_centered(built):
    df, _, _ = built
    assert np.isfinite(df.rv).all()
    assert abs(df.rv.mean()) < 0.05
    assert df.rv.corr(df.rv_delta) > 0.4


def test_rv_x_replaces_only_balls_in_play_and_is_less_noisy(built):
    df, _, lw = built
    in_play = df.PitchCall.astype(str) == "InPlay"
    assert np.allclose(df.rv_x[~in_play], df.rv[~in_play])
    assert df.rv_x.notna().all() and df.xlw[in_play].notna().all() and df.xlw[~in_play].isna().all()
    assert df.rv_x[in_play].std() < df.rv[in_play].std()
    observed = df.event[in_play].map(lw["lw"]).astype(float)
    assert observed.corr(df.xlw[in_play]) > 0.3


def test_hard_hit_balls_are_worth_more(built):
    df, _, _ = built
    ip = df[df.xlw.notna() & df.ExitSpeed.notna()]
    hard = ip[ip.ExitSpeed >= 100].xlw.mean()
    soft = ip[ip.ExitSpeed < 80].xlw.mean()
    assert hard > soft


def test_targets_respect_their_denominators(built):
    df, _, _ = built
    assert df.t_whiff[df.is_swing == 0].isna().all()
    assert df.t_whiff[df.is_swing == 1].notna().all()
    assert df.t_chase[df.outside_strike_zone == 0].isna().all()
    assert df.t_called_strike[df.is_swing == 1].isna().all()
    in_play = df.PitchCall.astype(str) == "InPlay"
    assert df.t_groundball[~in_play].isna().all()
    for name in targets.TARGETS:
        vals = df[name].dropna()
        assert len(vals) > 0 and vals.isin([0.0, 1.0]).all(), name
    assert (df.groupby("pa_id").t_out_in_pa.nunique(dropna=False) == 1).all()


def test_targets_are_rejected_as_features():
    with pytest.raises(schema.LeakError):
        schema.assert_no_target_leak(list(targets.TARGETS))
    with pytest.raises(schema.LeakError):
        schema.assert_no_target_leak(["RelSpeed", "rv", "rv_delta"])


def test_lmb_vs_mlb_is_labelled_unverified(built):
    df, _, lw = built
    t = targets.lmb_vs_mlb(df, lw)
    assert (~t.mlb_verified).all() and t.mlb_source.str.contains("FanGraphs").all()
    assert t.mlb.notna().all() and len(t) == len(targets.MLB_REFERENCE["weights"]) + 1
    hr = t.set_index("stat").loc["HomeRun runs vs out"]
    assert hr.mlb == pytest.approx(2.050 / 1.242)


def test_reports_are_aggregates_only(built, tmp_path):
    df, re, lw = built
    targets.write_reports(df, re, lw, out_dir=tmp_path)
    files = sorted(p.name for p in tmp_path.glob("*.csv"))
    assert files == ["batted_ball_value_by_altitude.csv", "linear_weights.csv", "lmb_vs_mlb.csv", "re_matrix.csv", "run_environment_by_altitude.csv",
                     "rv_summary.csv", "target_rates.csv"]
    for p in tmp_path.glob("*.csv"):
        t = pd.read_csv(p)
        assert len(t) < 100 and "PitchUID" not in t.columns
