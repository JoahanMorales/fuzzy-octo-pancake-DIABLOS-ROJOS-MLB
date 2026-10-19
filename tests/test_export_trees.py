"""HACK-040: tree export for the browser (contract JSON, pure evaluator parity, Plus scaler, size budget)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stuffplus import export_trees as et
from stuffplus import schema
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.models.location import add_pitch_family
from stuffplus.models.stuff import OUTCOMES, StuffModel, magnus_translate
from stuffplus.scale import PlusScaler

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def exported(_synthetic_cache):
    spec = importlib.util.spec_from_file_location("stuff_run", ROOT / "analysis" / "stuff_model" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    d = add_pitch_family(mod.prepare(schema.clean(_synthetic_cache.copy())))
    m = StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=magnus_translate, class_rounds=30,
                   contact_rounds=20).fit(d)
    sc = PlusScaler().fit(d.assign(x=m.predict_at_rho(d, 1.0)["xrv"].to_numpy()), "x")
    payload = et.export_composite(m, sc, "stuff", model_version="test", sources=["tests"], demo_data=True)
    return m, sc, d, payload


def test_payload_has_contract_fields_and_booster_category_order(exported):
    _, _, _, p = exported
    assert p["model"] == "pitch_family Stuff+ composite" and p["translation"] == "physics_translator"
    assert all("packed" in t for t in p["outcome"]["trees"])
    assert "AutoPitchType" not in p["features"] and "pitch_family" in p["features"]
    assert p["categories"]["pitch_family"] == list(schema.PITCH_TYPES)  # code order, not alphabetical
    assert [c["outcome"] for c in p["class_values"]] == list(OUTCOMES)
    assert p["outcome"]["num_class"] == 5 and len(p["outcome"]["trees"]) % 5 == 0
    assert p["plus"]["reference"] == "park-neutral" and p["plus"]["sign"] == -1 and "__all__" in p["plus"]["stats"]


def test_stripped_trees_keep_only_evaluation_fields(exported):
    m, sc, _, _ = exported
    p = et.export_composite(m, sc, "stuff", model_version="test", sources=["tests"], demo_data=True, packed=False)
    allowed = {"split_feature", "threshold", "decision_type", "default_left", "missing_type", "left_child",
               "right_child", "leaf_value"}

    def walk(n):
        assert set(n) <= allowed
        for c in ("left_child", "right_child"):
            if c in n:
                walk(n[c])

    for t in p["outcome"]["trees"] + p["contact"]["trees"]:
        walk(t["tree_structure"])


def test_json_evaluator_matches_lightgbm_with_nans_and_unseen_categories(exported):
    m, _, d, p = exported
    rows = pd.concat([d[p["features"]].sample(80, random_state=1).reset_index(drop=True),
                      et.random_rows(p, 60, d, seed=3)], ignore_index=True)
    assert rows.isna().any().any() and (rows.pitch_family == "Knuckle-Curve").any()
    g = et.golden(m, p, rows)
    out = et.evaluate(json.loads(json.dumps(et._nan_to_none(p))), rows)
    assert np.abs(out[[f"p_{o}" for o in OUTCOMES]].to_numpy() - np.array(g["probs"])).max() < 1e-9
    assert np.abs(out["xrv"].to_numpy() - np.array(g["xrv"])).max() < 1e-9


def test_packed_round_trips_to_nested_and_stays_within_1e6(exported):
    m, sc, d, p = exported
    nested = et.export_composite(m, sc, "stuff", model_version="test", sources=["tests"], demo_data=True, packed=False)
    t = nested["outcome"]["trees"][0]["tree_structure"]
    back = et.unpack_tree(et.pack_tree(t))
    assert back["split_feature"] == t["split_feature"] and back["threshold"] == t["threshold"]
    rows = et.random_rows(p, 80, d, seed=5)
    g = et.golden(m, p, rows)
    assert np.abs(et.evaluate(p, rows)["xrv"].to_numpy() - np.array(g["xrv"])).max() < 1e-6
    assert len(json.dumps(p, separators=(",", ":"))) < len(json.dumps(nested, separators=(",", ":")))


def test_plus_scaler_round_trip_on_park_neutral_predictions(exported):
    m, sc, d, p = exported
    xrv = m.predict_at_rho(d, 1.0)["xrv"].to_numpy()
    st = p["plus"]["stats"]["__all__"]
    plus = 100 + 10 * -1 * (xrv - st["mean"]) / st["sd"]
    assert plus.mean() == pytest.approx(100, abs=1e-6) and plus.std() == pytest.approx(10, rel=1e-6)
    assert sc.scale_value(float(xrv[0])) == pytest.approx(plus[0])


def test_write_json_is_strict_json_and_committed_files_fit_the_budget(exported, tmp_path):
    _, _, _, p = exported
    p = dict(p, plus=dict(p["plus"], stats={"__all__": {"mean": float("nan"), "sd": 1.0, "n": 1}}))
    et.write_json(p, tmp_path / "m.json")
    assert json.loads((tmp_path / "m.json").read_text())["plus"]["stats"]["__all__"]["mean"] is None
    models = ROOT / "web" / "public" / "data" / "models"
    total = sum(f.stat().st_size for f in models.glob("*.json")) / 1e6 if models.exists() else 0.0
    assert total <= et.SIZE_BUDGET_MB
    for f in [*models.glob("*.json"), *(ROOT / "web" / "src" / "model" / "fixtures").glob("*.json")]:
        assert "PitchUID" not in f.read_text()[:200000]


@pytest.fixture(scope="module")
def production(exported):
    """Production Stuff+ v2 (count-neutral value + temperature) on the synthetic fixture (HACK-066)."""
    _, _, d, _ = exported
    m, sc = et.fit_stuff(d, magnus_translate, k_inner=2, class_rounds=20, contact_rounds=15)
    return m, sc, d, et.export_composite(m, sc, "stuff", model_version="test_v2", sources=["tests"], demo_data=True)


def test_production_payload_carries_temperature_and_count_block(production):
    m, _, _, p = production
    assert p["calibration"]["method"] == "temperature" and p["calibration"]["T"] == pytest.approx(m.model._calibrator.T)
    cb = p["count"]
    assert cb["value"] == "count_neutral" and cb["counts"][0] == "0-0" and len(cb["counts"]) == 12
    assert len(cb["values"]) == 12 and all(len(r) == 5 for r in cb["values"])
    assert cb["offset"] == pytest.approx(m.model.count_offset.reindex(cb["counts"]).tolist())  # calibrated offsets
    assert {"Balls", "Strikes"} <= set(p["features"])


def test_json_evaluator_matches_count_neutral_production_model(production):
    m, _, d, p = production
    rows = pd.concat([d[p["features"]].sample(40, random_state=2).reset_index(drop=True),
                      et.random_rows(p, 30, d, seed=7)], ignore_index=True)
    g = et.golden(m, p, rows)
    out = et.evaluate(json.loads(json.dumps(et._nan_to_none(p))), rows)
    assert np.abs(out[[f"p_{o}" for o in OUTCOMES]].to_numpy() - np.array(g["probs"])).max() < 1e-9
    assert np.abs(out["xrv_at_count"].to_numpy() - np.array(g["xrv_at_count"])).max() < 1e-9
    assert np.abs(out["xrv"].to_numpy() - np.asarray(m.predict_xrv(rows))).max() < 1e-9
    moved = rows.assign(Balls=3, Strikes=0)
    assert np.allclose(et.evaluate(p, moved)["xrv"], out["xrv"], atol=1e-12)  # the count never moves Stuff+
    no_count = et.evaluate(p, rows.drop(columns=["Balls", "Strikes"]))  # e.g. the prospect profiler
    assert np.allclose(no_count["xrv"], out["xrv"], atol=1e-12) and no_count["xrv_at_count"].isna().all()


@pytest.fixture(scope="module")
def pitching(exported):
    """Pitching+ (HACK-079): components + 8 target boosters + combination on the synthetic fixture."""
    from stuffplus.models.pitching import build_features

    _, _, d, _ = exported
    pf = build_features(d)
    m, sc = et.fit_pitching(pf, k=2, class_rounds=15, contact_rounds=10, target_rounds=10)
    return m, sc, pf, et.export_pitching(m, sc, model_version="test", sources=["tests"], demo_data=True,
                                         fill=et.panel_fill(pf))


def test_pitching_payload_carries_targets_combination_zone_and_neutral_batter(pitching):
    m, _, pf, p = pitching
    assert set(p["targets"]) == {"swing", "whiff", "chase", "called_strike", "weak_contact", "groundball",
                                 "hard_contact", "out_in_pa"}
    assert p["combination"]["weights"]["xrv_components"] >= 0 and p["combination"]["weights"]["whiff_rate"] <= 0
    assert p["neutral"]["batter"] == pytest.approx(m.batter) and set(p["neutral"]["league"]) == set(et.PANEL_FILL)
    assert p["zone"]["z_low"] < p["zone"]["z_high"] and p["zone"]["x"] > 0
    assert "calibration" not in p and "count" not in p and p["plus"]["stats"]["__all__"]["sd"] > 0


def test_json_evaluator_matches_pitching_model(pitching):
    m, _, pf, p = pitching
    pb = et.with_batters(pf)
    rows = pd.concat([pb[p["features"]].sample(40, random_state=3).reset_index(drop=True),
                      et.random_rows(p, 30, pb, seed=8)], ignore_index=True)
    out = et.evaluate_pitching(json.loads(json.dumps(et._nan_to_none(p))), rows)
    assert np.abs(out - m.predict_xrv(rows)).max() < 1e-9
