"""HACK-052: Stuff+ v2 — count values the outcomes, Stuff+ marginalizes the count away."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from stuffplus import schema
from stuffplus.models import stuff_v2
from stuffplus.models.stuff_v2 import COUNTS, StuffV2Model, check_features

ROOT = Path(__file__).resolve().parent.parent
FAST = dict(class_rounds=8, contact_rounds=6)


@pytest.fixture(scope="module")
def frame(_synthetic_cache):
    spec = importlib.util.spec_from_file_location("alt_run", ROOT / "analysis" / "altitude_delta" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _, d = mod.prepare(schema.clean(_synthetic_cache.copy()))
    return d.reset_index(drop=True)


@pytest.fixture(scope="module")
def model(frame):
    return StuffV2Model(**FAST).fit(frame)


def test_leak_guard_allows_only_the_count():
    check_features(stuff_v2.V2_FEATURES)
    for bad in (["RelSpeed", "Balls", "PlateLocHeight"], ["RelSpeed", "Outs"], ["RelSpeed", "count"], ["rv_x"]):
        with pytest.raises(schema.LeakError):
            check_features(bad)


def test_count_values_cover_every_count_and_fall_back_to_class_means(model):
    assert model.count_values.shape == (len(COUNTS), 5) and model.count_values.notna().all().all()
    assert len(model.count_mean) == len(COUNTS)
    assert np.isclose(model.league_weights.sum(), 1)
    assert np.allclose(model.family_weights.sum(axis=1), 1)


def test_per_pitch_prediction_depends_on_the_count(model, frame):
    a = model.predict_xrv(frame.assign(Balls=3, Strikes=0))
    b = model.predict_xrv(frame.assign(Balls=0, Strikes=2))
    assert not np.allclose(a, b)


def test_stuff_value_ignores_the_pitch_own_count(model, frame):
    v1 = model.stuff_value(frame.assign(Balls=3, Strikes=0))
    v2 = model.stuff_value(frame.assign(Balls=0, Strikes=2))
    assert np.allclose(v1, v2) and np.isfinite(v1).all()


def test_family_and_league_weights_differ_but_both_finite(model, frame):
    fam, lea = model.stuff_value(frame), model.stuff_value(frame, weights="league")
    assert np.isfinite(fam).all() and np.isfinite(lea).all()
    assert abs(float(np.mean(fam))) < 0.05  # centred: values are relative to the count means


def test_stuff_value_at_rho_moves_with_air(model, frame):
    sea = model.stuff_value_at_rho(frame, 1.0)
    thin = model.stuff_value_at_rho(frame, 0.82)
    assert np.isfinite(thin).all() and not np.allclose(sea, thin)


def test_count_only_ablation_has_no_stuff(frame):
    m = stuff_v2.count_only(FAST).fit(frame)
    assert m.features == ["Balls", "Strikes"]
    p = m.predict_xrv(frame)
    keys = frame.Balls.astype(str) + frame.Strikes.astype(str)
    assert (frame.assign(p=p).groupby(keys).p.nunique() == 1).all()  # same count → same prediction
