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
