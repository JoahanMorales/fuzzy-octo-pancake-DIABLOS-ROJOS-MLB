"""HACK-019: SHAP explanations add up to the served Stuff+ and read well in Spanish."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
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


# --- HACK-080: production Stuff+ v2 ------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def v2(_synthetic_cache):
    from stuffplus.altitude import physics_translator
    from stuffplus.models.stuff import fit_production_stuff
    from stuffplus.scale import PlusScaler

    spec = importlib.util.spec_from_file_location("alt_run_explain", ROOT / "analysis" / "altitude_delta" / "run.py")
    alt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(alt)
    shape_model, d = alt.prepare(schema.clean(_synthetic_cache.copy()))
    d = d.reset_index(drop=True)
    m = fit_production_stuff(d, translate=physics_translator(shape_model), k_inner=2, class_rounds=20, contact_rounds=15)
    sc = PlusScaler().fit(d.assign(x=m.predict_at_rho(d, 1.0)["xrv"].to_numpy()), "x")
    fit_rows, hold = d.iloc[: len(d) // 2], d.iloc[len(d) // 2:]
    ex = explain.fit_v2_explainer(m, sc, fit_rows, rounds=150)
    return ex, d, hold


def test_v2_points_add_up_to_the_surrogate_and_ignore_the_count(v2):
    ex, d, hold = v2
    rows = hold.head(50)
    e = explain.explain_v2(ex, rows, 1.0, top=50)
    for r in e:
        assert r["base"] + sum(i["points"] for i in r["contributions"]) + r["other_points"] == pytest.approx(
            r["surrogate_stuff_plus"], abs=0.15)
    assert "Balls" not in ex.features and "Strikes" not in ex.features
    p0, _ = ex.points(rows)
    p1, _ = ex.points(rows.assign(Balls=3, Strikes=0))
    assert (p0.to_numpy() == p1.to_numpy()).all()


def test_v2_surrogate_tracks_the_real_value_on_unseen_pitches(v2):
    ex, d, hold = v2
    fid = explain.fidelity(ex, hold).set_index("target")
    assert set(fid.index) == {f"rho_{1.0:.3f}", f"rho_{explain.RHO_HARP_HELU:.3f}", "delta_cdmx"}
    assert (fid.loc[[f"rho_{1.0:.3f}", f"rho_{explain.RHO_HARP_HELU:.3f}"], "corr"] > 0.8).all()
    assert fid.loc["delta_cdmx", "corr"] > 0.5
    a = explain.altitude_v2(ex, hold.head(30))
    real = np.array([r["delta_stuff_plus"] for r in a])
    sur = np.array([r["surrogate_delta"] for r in a])
    assert np.abs(sur.mean() - real.mean()) < 2.0


def test_v2_text_is_spanish_and_examples_are_shape_medians(v2):
    ex, d, hold = v2
    ex_rows = explain.shape_examples(d, min_n=5)
    assert len(ex_rows) >= 1 and (ex_rows["n"] >= 5).all()
    e = explain.explain_v2(ex, ex_rows, 1.0, top=3)[0]
    assert all(i["text"][0] in "+-" and " por " in i["text"] for i in e["contributions"])
    a = explain.altitude_v2(ex, ex_rows)[0]
    assert all("aire de la CDMX" in i["text"] for i in a["items"])
