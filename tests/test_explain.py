"""HACK-019: SHAP explanations add up to the served Stuff+ and read well in Spanish."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from stuffplus import api, explain, schema, serving

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def bundle_dir(tmp_path_factory, _synthetic_cache):
    spec = importlib.util.spec_from_file_location("stuff_run", ROOT / "analysis" / "stuff_model" / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    frame = run.prepare(schema.clean(_synthetic_cache.copy()))
    out = tmp_path_factory.mktemp("bundle_explain")
    run.train(frame, out, fast=True, write_reports=False)
    return out, frame


@pytest.fixture
def served(bundle_dir, monkeypatch):
    out, frame = bundle_dir
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(out))
    serving.reset_cache()
    yield frame
    serving.reset_cache()


FB = api.PitchInput("Four-Seam", "Right", 96, 2450, 210, 19, 8, extension=6.6)
SL = api.PitchInput("Slider", "Left", 84, 2650, 280, 0, 15, arsenal={"fb_velo": 94, "fb_ivb": 16, "fb_hb": -8})


@pytest.mark.parametrize("p", [FB, SL])
@pytest.mark.parametrize("rho", ["sea_level", "harp_helu"])
def test_contributions_add_up_to_served_stuff_plus(served, p, rho):
    e = explain.explain_pitch(p, rho, top=50)
    served_value = api.predict_pitch(p, rho)["stuff_plus"]
    assert e["stuff_plus"] == pytest.approx(served_value, abs=0.15)
    total = e["base"] + sum(i["points"] for i in e["contributions"]) + e["other_points"]
    assert total == pytest.approx(e["stuff_plus"], abs=0.15)


def test_top_contributions_are_sorted_and_in_spanish(served):
    e = explain.explain_pitch(FB, "sea_level", top=5)
    pts = [abs(i["points"]) for i in e["contributions"]]
    assert pts == sorted(pts, reverse=True) and len(pts) == 5
    for i in e["contributions"]:
        assert i["text"][0] in "+-" and " por " in i["text"]


def test_altitude_breakdown_matches_compare_environments(served):
    a = explain.altitude_breakdown(FB, "harp_helu")
    cmp = api.compare_environments(FB, "harp_helu", "sea_level")
    assert a["delta_stuff_plus"] == pytest.approx(cmp["delta_stuff_plus"], abs=0.15)
    assert all("aire de la CDMX" in i["text"] for i in a["items"])
    ivb = [i for i in a["items"] if i["feature"] == "InducedVertBreak"]
    if ivb:
        assert "quita" in ivb[0]["text"]  # thinner air removes ride from a four-seam


def test_global_importance(served):
    frame = served.head(400).copy()
    imp, points = explain.global_importance(serving.get_bundle(), frame)
    assert set(imp.feature) == set(points.columns)
    assert (imp.mean_abs_points >= 0).all() and imp.mean_abs_points.is_monotonic_decreasing


def test_describe_handles_categories_and_nan():
    assert explain._describe("AutoPitchType", "Slider").startswith("por tipo de pitch")
    assert "desconocido" in explain._describe("velo_diff_fb", float("nan"))
    assert explain._describe("hb_arm", -12.0).endswith("guante")
