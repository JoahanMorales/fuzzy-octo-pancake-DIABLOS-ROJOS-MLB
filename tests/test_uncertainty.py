"""HACK-055: density ratio, importance-weighted skill and (weighted) split conformal intervals."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stuffplus import uncertainty as un


def _frame(n=6000, shift=1.0, seed=0):
    rng = np.random.default_rng(seed)
    tgt = rng.random(n) < 0.3
    x = rng.normal(0, 1, n) + shift * tgt
    return pd.DataFrame({"x": x, "z": rng.normal(0, 1, n), "pitcher_anon_id": [f"p{i % 300}" for i in range(n)]}), tgt


def test_density_ratio_detects_a_planted_shift_and_reports_overlap():
    df, tgt = _frame(shift=1.0)
    w, d = un.density_ratio(df, ["x", "z"], tgt, rounds=60)
    assert d["auc"] > 0.65 and d["ess"] < d["n_source"]
    src = ~tgt
    assert np.corrcoef(df.x[src], w[src])[0, 1] > 0.5  # source rows that look like the target weigh more


def test_density_ratio_is_flat_without_shift():
    df, tgt = _frame(shift=0.0, seed=1)
    _, d = un.density_ratio(df, ["x", "z"], tgt, rounds=60)
    assert d["auc"] < 0.6 and d["ess_share"] > 0.8


def test_weighted_skill_reduces_to_plain_skill_with_unit_weights():
    rng = np.random.default_rng(2)
    y = rng.normal(size=500)
    pred, base = y + rng.normal(0, .5, 500), np.zeros(500)
    assert un.weighted_skill(y, pred, base) == pytest.approx(un.weighted_skill(y, pred, base, np.ones(500)))
    assert un.weighted_skill(y, base, base) == pytest.approx(0.0)


def test_weighted_quantile():
    assert un.weighted_quantile([1, 2, 3, 4], [1, 1, 1, 1], 0.5) == 2
    assert un.weighted_quantile([1, 2, np.inf], [1, 1, 10], 0.5) == np.inf


def test_conformal_covers_iid_and_weighted_fixes_covariate_shift():
    rng = np.random.default_rng(3)
    n = 4000
    x_cal = rng.normal(0, 1, n)
    x_tst = rng.normal(1.2, 1, n)  # shifted target
    noise = lambda x: rng.normal(0, 0.2 + 0.6 * (x > 0.8), len(x))  # larger errors where the target lives
    r_cal, r_tst = noise(x_cal), noise(x_tst)
    plain = un.split_conformal(r_cal, alpha=0.1)
    assert un.coverage(noise(rng.normal(0, 1, n)), 0, plain) == pytest.approx(0.9, abs=0.03)  # iid: valid
    assert un.coverage(r_tst, 0, plain) < 0.85  # shift: under-covers
    dens = lambda x, m: np.exp(-0.5 * (x - m) ** 2)
    w_cal, w_tst = dens(x_cal, 1.2) / dens(x_cal, 0), dens(x_tst[:800], 1.2) / dens(x_tst[:800], 0)
    hw = un.split_conformal(r_cal, alpha=0.1, w_cal=w_cal, w_test=w_tst)
    assert un.coverage(r_tst[:800], np.zeros(800), hw) == pytest.approx(0.9, abs=0.04)
