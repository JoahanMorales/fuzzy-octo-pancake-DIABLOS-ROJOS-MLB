"""HACK-011: Location+ (marginal value of location), zones, heatmaps and bundle update."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stuffplus import api, schema, serving
from stuffplus.models import location

ROOT = Path(__file__).resolve().parent.parent


def _load(rel):
    spec = importlib.util.spec_from_file_location(rel.replace("/", "_"), ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def setup(tmp_path_factory, _synthetic_cache):
    stuff_run = _load("analysis/stuff_model/run.py")
    loc_run = _load("analysis/location_model/run.py")
    frame = location.add_pitch_family(stuff_run.prepare(schema.clean(_synthetic_cache.copy())))
    bundle = tmp_path_factory.mktemp("bundle_loc")
    stuff_run.train(frame, bundle, fast=True, write_reports=False)
    res = loc_run.train(frame, fast=True, out_dir=bundle, write_reports=False)
    return frame, res, bundle


def test_zone_labels():
    df = pd.DataFrame({"plate_x_arm": [0.6, 0.0, -0.6, 0.0, 1.0, 2.5], "PlateLocHeight": [3.3, 2.5, 1.7, 0.8, 2.5, 2.5]})
    assert location.zone_label(df).tolist() == ["1", "5", "9", "chase", "shadow", "waste"]


def test_count_buckets():
    df = pd.DataFrame({"count": ["0-2", "1-1", "3-1", "9-9"]})
    assert location.count_bucket(df).tolist() == ["ahead", "even", "behind", "even"]


def test_location_value_is_centered_by_count_and_type(setup):
    frame, res, _ = setup
    m = res["model"]
    lv = pd.Series(m.location_value(frame), index=frame.index)
    by_cell = lv.groupby([frame["count"].astype(str), frame.pitch_family.astype(str)]).mean()
    assert by_cell.abs().max() < 1e-9


def test_location_features_exclude_physics():
    assert not {"RelSpeed", "SpinRate", "InducedVertBreak", "HorzBreak"} & set(location.LOCATION_FEATURES)


def test_heatmap_grid_and_middle_vs_edge(setup):
    _, res, _ = setup
    grid = res["grid"]
    assert {"pitch_family", "count", "rho", "plate_x_arm", "PlateLocHeight", "loc_value"} <= set(grid.columns)
    assert grid.loc_value.notna().all() and set(grid.rho.round(3)) == {1.0, round(api.resolve_rho("harp_helu"), 3)}


def test_reports_tables(setup):
    _, res, _ = setup
    assert set(res["metrics"].model) == {"baseline", "location_v1"}
    assert {"family_group", "count_bucket", "zone", "location_value", "observed_rv_x"} <= set(res["zones"].columns)
    assert {"pitch_family", "zone", "sea_level", "harp_helu", "delta_cdmx"} <= set(res["altitude"].columns)
    assert "location_model" in res["reliability"].columns
    assert "PitchUID" not in res["zones"].columns


def test_location_never_uses_trackman_labels():
    assert "AutoPitchType" not in location.LOCATION_FEATURES


def test_bundle_location_model_replaced_and_served(setup, monkeypatch):
    frame, res, bundle = setup
    man = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert man["models"]["location_xrv"]["task"] == "HACK-011"
    assert man["models"]["location_xrv"]["features"] == location.LOCATION_FEATURES
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(bundle))
    serving.reset_cache()
    p = api.PitchInput(pitch_type="Four-Seam", throws="Right", velo=95, spin_rate=2400, spin_axis=210, ivb=17, hb=8,
                       plate_x=0.0, plate_z=2.5, balls=0, strikes=0, batter_side="Right")
    r = api.predict_pitch(p)
    assert r["location_plus"] is not None and np.isfinite(r["location_plus"])
    serving.reset_cache()


def test_unfitted_model_and_missing_columns_raise(setup):
    frame, res, _ = setup
    with pytest.raises(RuntimeError):
        location.LocationModel().location_value(frame.head(5))
    with pytest.raises(KeyError):
        res["model"].location_value(frame.head(5).drop(columns=["plate_x_arm"]))


def test_unassigned_family_falls_back_to_trackman_label(setup):
    frame, _, _ = setup
    probe = frame.head(2).copy()
    probe["pitch_family"] = [None, "Slider"]
    out = location.add_pitch_family(probe)
    assert out["pitch_family"].iloc[0] == str(probe["AutoPitchType"].iloc[0])
    assert out["pitch_family_assigned"].tolist() == [False, True]
