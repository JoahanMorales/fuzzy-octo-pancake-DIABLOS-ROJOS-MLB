import numpy as np
import pandas as pd
import pytest
from stuffplus.sensitivity import summarize_sensitivity


def pitches():
    rows = []
    for pitcher, delta in (("anon-a", -6), ("anon-b", 2), ("anon-c", -2), ("anon-d", 6)):
        for game in range(8):
            high = game < 4
            for pitch, count, shift in (("fast", 30, delta), ("break", 10, 0)):
                for i in range(count):
                    rows.append(dict(pitcher_anon_id=pitcher, year=2024, pitch_key=f"{pitcher}-{pitch}",
                                     game_anon_id=f"{pitcher}-{game}", pitch_family=pitch,
                                     altitude_category="Extreme Altitude" if high else "No Altitude",
                                     stuff_b=100., stuff_a=100 + shift + (game % 4 - 1.5) * .1,
                                     observed_stuff_plus=100 + (shift if high else 0) + (game % 4 - 1.5) * .2,
                                     delta_ivb_in=-1, delta_hb_arm_in=-.5))
    return pd.DataFrame(rows)


def test_usage_weighted_arsenal_and_driver():
    result = summarize_sensitivity(pitches())
    t = result["pitchers"].set_index("pitcher_anon_id")
    assert t.loc["anon-a", "delta_stuff"] == pytest.approx(-4.5)
    assert t.loc["anon-b", "observed_delta"] == pytest.approx(1.5)
    assert t.loc["anon-a", "driver_family"] == "fast"
    assert result["pitches"].groupby(["pitcher_anon_id", "year"]).usage.sum().eq(1).all()
    assert set(result["top15"].pitcher_anon_id) == {"anon-b", "anon-d"}
    assert set(result["bottom15"].pitcher_anon_id) == {"anon-a", "anon-c"}
    assert (t.index_lo <= t.altitude_proof_index).all()
    assert (t.index_hi >= t.altitude_proof_index).all()


def test_missing_split_and_single_game_are_not_fabricated():
    d = pitches()
    d.loc[d.pitcher_anon_id == "anon-a", "altitude_category"] = "No Altitude"
    d.loc[d.pitcher_anon_id == "anon-b", "game_anon_id"] = "only-game"
    t = summarize_sensitivity(d)["pitchers"].set_index("pitcher_anon_id")
    assert np.isnan(t.loc["anon-a", "observed_eb"])
    assert t.loc["anon-a", "split_usage_coverage"] == 0
    assert not t.loc["anon-b", "eligible"]


def test_matched_usage_removes_composition_change():
    d = pitches()
    # Equal pitch-specific quality in each environment, unequal arsenal composition.
    d["observed_stuff_plus"] = np.where(d.pitch_family == "fast", 110., 90.)
    d = d.drop(d[(d.altitude_category == "No Altitude") & (d.pitch_family == "fast")].index[::2])
    t = summarize_sensitivity(d)["pitchers"]
    assert np.allclose(t.observed_delta, 0)


def test_shrinkage_and_season_isolation():
    d = pitches()
    noisy = d.pitcher_anon_id == "anon-a"
    d.loc[noisy, "stuff_a"] += d.loc[noisy, "game_anon_id"].str[-1].astype(int).map(lambda i: (-1)**i * 5)
    t = summarize_sensitivity(d)["pitchers"].set_index("pitcher_anon_id")
    assert t.loc["anon-a", "delta_weight"] < t.loc["anon-b", "delta_weight"]
    other = pitches().assign(year=2025, stuff_a=lambda x: x.stuff_a + 20)
    combined = summarize_sensitivity(pd.concat([d, other]))["pitchers"]
    first = combined[combined.year == 2024].set_index("pitcher_anon_id")
    assert np.allclose(first.delta_eb, t.delta_eb)


@pytest.mark.parametrize("change", ["missing", "nan", "inf", "duplicate", "empty"])
def test_reject_bad_input(change):
    d = pitches()
    if change == "missing": d = d.drop(columns="stuff_a")
    if change == "nan": d.loc[0, "stuff_a"] = np.nan
    if change == "inf": d.loc[0, "stuff_b"] = np.inf
    if change == "duplicate": d["PitchUID"] = "same"
    if change == "empty": d = d.head(0)
    with pytest.raises(ValueError): summarize_sensitivity(d)


def test_top_bottom_are_fifteen_and_do_not_overlap():
    frames = []
    base = pitches().query('pitcher_anon_id == "anon-a"')
    for i in range(40):
        p = base.copy()
        p["pitcher_anon_id"] = f"anon-{i:02d}"
        p["pitch_key"] = p.pitch_family.map(lambda x: f"anon-{i:02d}-{x}")
        p["game_anon_id"] = p.game_anon_id.map(lambda x: f"anon-{i:02d}-{x}")
        p["stuff_a"] += i
        frames.append(p)
    result = summarize_sensitivity(pd.concat(frames, ignore_index=True))
    assert len(result["top15"]) == len(result["bottom15"]) == 15
    assert not set(result["top15"].pitcher_anon_id) & set(result["bottom15"].pitcher_anon_id)
    assert result["top15"].iloc[0].pitcher_anon_id == "anon-39"


def test_degenerate_prior_and_unsupported_pitch():
    d = pitches()
    d["stuff_a"] = 100.
    d = d[~((d.altitude_category == "No Altitude") & (d.pitch_family == "break"))]
    t = summarize_sensitivity(d)["pitchers"]
    assert t.delta_weight.eq(0).all()
    assert t.altitude_proof_index.eq(100).all()
    assert np.allclose(t.split_usage_coverage, 240 / 280)
    assert t.observed_delta.notna().all()


def test_missing_optional_family_keeps_report_usable():
    d = pitches()
    d["pitch_family"] = np.nan
    result = summarize_sensitivity(d)
    assert result["pitches"].pitch_family.eq("unknown").all()
