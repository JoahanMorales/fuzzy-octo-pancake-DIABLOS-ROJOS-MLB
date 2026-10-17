"""HACK-054: location-netted approach angles and primary-fastball diffs by batter hand (synthetic data)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stuffplus import schema
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.features.relative import HAND_FEATURES, NET_FEATURES, ApproachResidual, add_hand_diffs

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def frame(_synthetic_cache):
    spec = importlib.util.spec_from_file_location("alt_run", ROOT / "analysis" / "altitude_delta" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _, d = mod.prepare(schema.clean(_synthetic_cache.copy()))
    return d.reset_index(drop=True)


def test_net_vaa_is_orthogonal_to_location_on_training_rows(frame):
    ar = ApproachResidual().fit(frame)
    out = ar.transform(frame)
    for fam, g in out.groupby(out.pitch_family.astype(str)):
        if len(g) < 30:
            continue
        ok = g[["vaa_net", "PlateLocHeight"]].notna().all(axis=1)
        assert abs(np.corrcoef(g.vaa_net[ok], g.PlateLocHeight[ok])[0, 1]) < 1e-6
    assert set(NET_FEATURES) <= set(out.columns)


def test_transform_uses_training_coefficients_only(frame):
    half = frame.pitcher_anon_id.isin(frame.pitcher_anon_id.unique()[::2])
    ar = ApproachResidual().fit(frame[half])
    before = {k: v.copy() for k, v in ar.coef.items()}
    ar.transform(frame[~half])
    assert all(np.array_equal(before[k], ar.coef[k]) for k in before)
    t = ar.r2_table()
    assert {"pitch_family", "angle", "r2_location_release"} <= set(t.columns)
    assert t.r2_location_release.dropna().between(-1e-9, 1 + 1e-9).all()


def test_planted_location_dependence_is_removed():
    rng = np.random.default_rng(0)
    n = 3000
    d = pd.DataFrame({"pitch_family": "Four-Seam", "PitcherThrows": "Right", "PlateLocHeight": rng.normal(2.5, .6, n),
                      "RelHeight": rng.normal(6, .3, n), "Extension": rng.normal(6.3, .3, n),
                      "PlateLocSide": rng.normal(0, .7, n), "RelSide": rng.normal(1.8, .3, n),
                      "HorzApprAngle": rng.normal(0, 1, n)})
    stuff = rng.normal(0, 0.3, n)
    d["VertApprAngle"] = -6 + 1.4 * d.PlateLocHeight - 0.9 * d.RelHeight + stuff
    out = ApproachResidual().fit(d).transform(d)
    assert np.corrcoef(out.vaa_net, stuff)[0, 1] > 0.99  # what is left is the non-location part
    assert ApproachResidual().fit(d).r2[("Four-Seam", "vaa")] > 0.8


def test_hand_diffs_are_zero_for_the_primary_fastball_itself():
    d = pd.DataFrame({"pitcher_anon_id": "p1", "year": 2026, "BatterSide": ["Left", "Left", "Right", "Right"],
                      "pitch_family": ["Four-Seam", "Slider", "Four-Seam", "Slider"], "PitcherThrows": "Left",
                      "RelSpeed": [94.0, 85.0, 93.0, 84.0], "InducedVertBreak": [17.0, 2.0, 16.0, 1.0],
                      "HorzBreak": [-8.0, 4.0, -7.0, 5.0], "PlateLocSide": 0.0, "RelSide": -1.8,
                      "HorzApprAngle": 0.0, "pitch_id": [1, 2, 1, 2], "primary_fb_id": 1})
    out = add_hand_diffs(d)
    assert np.allclose(out.loc[[0, 2], HAND_FEATURES], 0)
    assert out.loc[1, "velo_diff_fb_hand"] == pytest.approx(-9.0) and out.loc[3, "velo_diff_fb_hand"] == pytest.approx(-9.0)


def test_relative_features_pass_the_pure_stuff_guard_but_location_does_not():
    from stuffplus.schema import LeakError, assert_no_target_leak

    assert_no_target_leak(list(STUFF_FEATURES_INVARIANT) + NET_FEATURES + HAND_FEATURES, allow_location=False)
    with pytest.raises(LeakError):
        assert_no_target_leak(list(STUFF_FEATURES_INVARIANT) + ["PlateLocHeight"], allow_location=False)
