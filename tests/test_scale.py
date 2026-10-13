"""HACK-013: plus scale, flavours, persistence and shrinkage."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stuffplus.scale import GLOBAL, PlusScaler, aggregate, plus_to_percentile, shrinkage_k


@pytest.fixture
def preds():
    rng = np.random.default_rng(0)
    n = 30_000
    year = rng.choice([2024, 2025, 2026], n)
    # different league level per season: the per-season reference must absorb it
    xrv = rng.normal(0.0, 0.02, n) + (year - 2025) * 0.005
    return pd.DataFrame({"year": year, "xrv": xrv, "family": rng.choice(["FB", "BB", "OS"], n)})


def test_each_season_has_mean_100_sd_10(preds):
    plus = PlusScaler().fit_transform(preds, "xrv")
    by_year = plus.groupby(preds.year)
    assert np.allclose(by_year.mean(), 100, atol=1e-9)
    assert np.allclose(by_year.std(ddof=0), 10, atol=1e-9)


def test_lower_xrv_is_better():
    df = pd.DataFrame({"year": [2025] * 3, "xrv": [-0.05, 0.0, 0.05]})
    plus = PlusScaler().fit_transform(df, "xrv")
    assert plus.iloc[0] > plus.iloc[1] > plus.iloc[2]


def test_percentiles():
    assert plus_to_percentile(100) == pytest.approx(50)
    assert plus_to_percentile(120) == pytest.approx(97.72, abs=0.01)
    assert plus_to_percentile(80) == pytest.approx(2.28, abs=0.01)


def test_environment_flavour_uses_the_neutral_reference(preds):
    """Scoring worse predictions (e.g. at CDMX air) with the sea-level scaler gives lower plus, same ruler."""
    sc = PlusScaler().fit(preds, "xrv")
    cdmx = preds.assign(xrv=preds.xrv + 0.004)
    delta = sc.transform(cdmx, "xrv") - sc.transform(preds, "xrv")
    assert (delta < 0).all()
    assert delta.mean() == pytest.approx(-0.004 / 0.02 * 10, rel=0.05)


def test_unseen_group_and_single_values_fall_back(preds):
    sc = PlusScaler().fit(preds, "xrv")
    new = pd.DataFrame({"year": [2030], "xrv": [preds.xrv.mean()]})
    assert sc.transform(new, "xrv").iloc[0] == pytest.approx(100, abs=1e-6)
    m = sc.stats["2025"]["mean"]
    assert sc.scale_value(m, group=[2025]) == pytest.approx(100)
    assert sc.scale_value(m - sc.stats["2025"]["sd"], group=[2025]) == pytest.approx(110)


def test_by_year_and_family(preds):
    sc = PlusScaler(by=("year", "family")).fit(preds, "xrv")
    assert len(sc.stats) == 1 + 9
    plus = sc.transform(preds, "xrv")
    assert np.allclose(plus.groupby([preds.year, preds.family]).mean(), 100, atol=1e-9)


def test_json_round_trip(preds, tmp_path):
    sc = PlusScaler().fit(preds, "xrv")
    sc.save(tmp_path / "scaler.json")
    back = PlusScaler.load(tmp_path / "scaler.json")
    assert back.stats == sc.stats and back.by == sc.by
    assert np.allclose(back.transform(preds, "xrv"), sc.transform(preds, "xrv"))
    with pytest.raises(RuntimeError):
        PlusScaler().transform(preds, "xrv")
    assert GLOBAL in back.stats


def test_shrinkage_pulls_small_samples_harder():
    rng = np.random.default_rng(1)
    rows = []
    for p in range(200):
        true = rng.normal(100, 4)
        n = 20 if p < 100 else 1500
        rows.append(pd.DataFrame({"pitcher_anon_id": f"p{p}", "year": 2025, "plus": rng.normal(true, 10, n)}))
    df = pd.concat(rows, ignore_index=True)
    k = shrinkage_k(df, "plus", ["pitcher_anon_id", "year"])
    assert 2 < k < 20  # within var 100 / true var 16 ≈ 6
    agg = aggregate(df, "plus", k=k)
    small, big = agg[agg.n == 20], agg[agg.n == 1500]
    assert ((small.shrunk - 100).abs() <= (small.raw - 100).abs()).all()
    assert (small.shrunk - 100).abs().mean() / (small.raw - 100).abs().mean() < 0.8
    assert (big.shrunk - big.raw).abs().max() < 0.2
    assert agg.percentile.between(0, 100).all()
