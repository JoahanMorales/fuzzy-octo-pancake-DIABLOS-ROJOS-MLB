"""HACK-031: v0 models → bundle → serving → api.predict_pitch (synthetic data, fast settings)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stuffplus import api, bundle, schema, serving
from stuffplus.models.common import add_arm_side_features

ROOT = Path(__file__).resolve().parent.parent


def _v0():
    spec = importlib.util.spec_from_file_location("v0_run", ROOT / "analysis" / "v0" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def trained(tmp_path_factory, _synthetic_cache):
    v0 = _v0()
    frame = v0.prepare(schema.clean(_synthetic_cache.copy()))
    out = tmp_path_factory.mktemp("bundle")
    res = v0.train_v0(frame, out, fast=True)
    return out, frame, res


@pytest.fixture
def served(trained, monkeypatch):
    out, frame, res = trained
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(out))
    serving.reset_cache()
    yield out, frame, res
    serving.reset_cache()


def _fastball(**kw):
    base = dict(pitch_type="Four-Seam", throws="Right", velo=95.0, spin_rate=2400, spin_axis=210, ivb=17.0, hb=8.0)
    base.update(kw)
    return api.PitchInput(**base)


def test_game_rho_separates_altitudes(trained):
    _, frame, _ = trained
    med = frame.groupby(frame.altitude_category.astype(str)).rho.median()
    assert med["Extreme Altitude"] < med["Medium Altitude"] < med["No Altitude"]
    assert 0.78 < med["Extreme Altitude"] < 0.9


def test_bundle_round_trip(trained):
    out, frame, _ = trained
    b = bundle.load_bundle(out)
    assert {"stuff_xrv", "location_xrv", "pitching_xrv", "stuff_t_whiff"} <= set(b.models)
    assert set(b.scalers) == {"stuff", "location", "pitching"}
    assert b.manifest["version"] == "v0-fast" and "scaler" in b.manifest
    assert "PitchUID" not in b.table("stuff_by_pitch_type_v0").columns


def test_serving_unavailable_without_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(tmp_path / "missing"))
    assert not serving.available()
    assert api.predict_pitch(_fastball())["demo_data"] is True


def test_api_dispatches_to_real_models(served):
    out = api.predict_pitch(_fastball(plate_x=0.5, plate_z=3.2, balls=0, strikes=2, batter_side="Right"))
    assert out["demo_data"] is False and out["model_version"] == "v0-fast"
    assert set(out) == set(api.PREDICTION_KEYS)
    assert set(out["probs"]) == set(api.PROB_KEYS)
    assert out["location_plus"] is not None
    assert all(0 <= v <= 1 for v in out["probs"].values())
    assert 40 < out["stuff_plus"] < 160


def test_altitude_translation_and_flavours(served):
    p = _fastball()
    cdmx, sea = api.predict_pitch(p, 0.81), api.predict_pitch(p, "sea_level")
    assert cdmx["movement_expected"]["ivb"] == pytest.approx(17.0 * 0.81, abs=0.01)
    assert sea["movement_expected"]["ivb"] == pytest.approx(17.0, abs=0.01)
    assert cdmx["stuff_plus_neutral"] == sea["stuff_plus_neutral"] == sea["stuff_plus"]
    assert api.predict_pitch(p, 0.81, flavour="neutral")["stuff_plus"] == sea["stuff_plus"]
    no_loc = api.predict_pitch(p)
    assert no_loc["location_plus"] is None and no_loc["pitching_plus"] == no_loc["stuff_plus"]


def test_predict_frame_matches_single_pitch(served):
    _, frame, _ = served
    row = frame.iloc[[10]]
    batch = serving.predict_frame(row, rho=1.0, year_col=None)
    single = serving.predict_frame(row.copy(), rho=1.0, year_col=None)
    assert np.allclose(batch.xrv_stuff, single.xrv_stuff)
    full = serving.predict_frame(frame.head(300))
    assert {"stuff_plus", "stuff_plus_neutral", "location_plus", "pitching_plus", "p_whiff"} <= set(full.columns)
    assert np.isfinite(full.stuff_plus).all()


def test_v0_reports_skill_vs_baseline(trained):
    _, _, res = trained
    cmp = res["compare"].set_index("model")
    assert {"baseline", "stuff_v0"} <= set(cmp.index)
    assert np.isfinite(cmp.loc["stuff_v0", "rmse"])
    assert cmp.loc["baseline", "skill_vs_baseline"] == pytest.approx(0)


def test_arm_side_features_mirror_lefties():
    df = pd.DataFrame({"PitcherThrows": ["Right", "Left"], "HorzBreak": [8.0, -8.0], "RelSide": [1.6, -1.6],
                       "SpinAxis": [210.0, 150.0], "PlateLocSide": [0.5, -0.5]})
    out = add_arm_side_features(df)
    assert out.hb_arm.tolist() == [8.0, 8.0] and out.rel_side_arm.tolist() == [1.6, 1.6]
    assert out.spin_axis_arm.tolist() == [210.0, 210.0] and out.plate_x_arm.tolist() == [0.5, 0.5]
