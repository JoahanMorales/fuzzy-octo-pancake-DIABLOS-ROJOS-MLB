"""Pre-treatment controls, grouped splitting, support and an actual DML recovery check."""
import json

import numpy as np
import pandas as pd
import pytest

from analysis.causal.run import (
    X_COLS, W_COLS, bootstrap_contrast, fit_analysis, grouped_folds,
    pre_pitch_covariates, sample_games, treatment_frame,
)


@pytest.fixture
def causal_frame():
    rng = np.random.default_rng(13)
    n = 3600
    balls, strikes = rng.integers(0,4,n), rng.integers(0,3,n)
    propensity = 1/(1+np.exp(-(.35*(strikes-balls))))
    t = rng.binomial(1, propensity)
    d = pd.DataFrame({"Balls":balls,"Strikes":strikes,"same_side":rng.integers(0,2,n),
                      "rho":rng.choice([1.,.9,.82],n),"rv_x":.2*balls-.15*strikes+1.5*t+rng.normal(0,.1,n),
                      "pitch_family":np.where(t,"Slider","Changeup"),
                      "pitcher_anon_id":[f"PRIVATE_P{i%30}" for i in range(n)],
                      "year":np.repeat([2024,2025,2026],n//3)})
    d["altitude_category"] = d.rho.map({1.:"No Altitude",.9:"Medium Altitude",.82:"Extreme Altitude"})
    for col in W_COLS:
        d[col] = 0.0
    return d


def test_treatment_mapping_and_feature_guard(causal_frame):
    d = treatment_frame(causal_frame)
    assert d[d.treatment.eq(1)].pitch_family.eq("Slider").all()
    assert d[d.treatment.eq(0)].pitch_family.eq("Changeup").all()
    assert not set(X_COLS+W_COLS) & {"rv_x","treatment","pitcher_anon_id","PlateLocHeight","RelSpeed","SpinRate"}
    broken = causal_frame.copy()
    broken.loc[0,"rv_x"] = np.nan
    broken.loc[1,"pitch_family"] = "Four-Seam"
    assert len(treatment_frame(broken)) == len(causal_frame)-2


def test_missing_columns_raise(causal_frame):
    with pytest.raises(ValueError,match="missing causal columns"):
        treatment_frame(causal_frame.drop(columns="rho"))


def test_grouped_nuisances_never_share_pitchers(causal_frame):
    d = treatment_frame(causal_frame)
    for tr,te in grouped_folds(d[d.year.ne(2026)].reset_index(drop=True)):
        assert not set(d.iloc[tr].pitcher_anon_id) & set(d.iloc[te].pitcher_anon_id)


def test_single_treatment_rejected(causal_frame):
    d = treatment_frame(causal_frame[causal_frame.pitch_family.eq("Slider")])
    with pytest.raises(ValueError,match="both treatment"):
        grouped_folds(d)


def test_prior_controls_never_use_current_or_future_physics():
    frame = pd.DataFrame({"pitcher_anon_id":["p"]*3,"year":[2025]*3,"pa_id":["pa"]*3,
                          "AutoPitchType":["Four-Seam","Slider","Four-Seam"],
                          "RelSpeed":[90.,80.,95.],"Inning":[1]*3})
    original = pre_pitch_covariates(frame)
    altered = frame.copy()
    altered.loc[1,"RelSpeed"] = 100.
    altered.loc[2,"RelSpeed"] = 110.
    changed = pre_pitch_covariates(altered)
    assert original.loc[1,"prior_fb_velo"] == changed.loc[1,"prior_fb_velo"] == 90.
    assert original.loc[1,"prev_velo"] == changed.loc[1,"prev_velo"] == 90.
    assert original.loc[0,"prior_fb_missing"] == 1


def test_sampling_keeps_whole_games_and_is_outcome_independent():
    d = pd.DataFrame({"game_anon_id":np.repeat(np.arange(30),10),"rv_x":np.arange(300)})
    a = sample_games(d,110)
    b = sample_games(d.assign(rv_x=-999),110)
    assert a.index.equals(b.index) and a.index.is_monotonic_increasing
    assert a.groupby("game_anon_id").size().eq(10).all()
    assert len(a) >= 110


def test_cluster_bootstrap_handles_constant_effect_and_small_groups():
    lo,hi = bootstrap_contrast(np.full(12,2.),np.repeat(["a","b","c"],4),40)
    assert lo == hi == 2.
    lo,hi = bootstrap_contrast([1.,2.],["a","b"],40)
    assert np.isnan(lo) and np.isnan(hi)


def test_econml_recovers_known_effect_on_future_year_without_raw_exports(causal_frame,tmp_path):
    pytest.importorskip("econml",reason="optional research extra; install analysis/causal/requirements.txt")
    table,meta = fit_analysis(causal_frame,tmp_path,demo_data=True,fast=True,min_cell=10)
    supported = table[table.status.eq("exploratory")]
    assert not supported.empty
    assert supported.contrast_bb_minus_offspeed.between(1.,2.).all()
    assert meta["train_rows"] == 2400 and meta["test_rows"] == 1200
    assert meta["promotion_allowed"] is False
    assert meta["test_year"] == 2026
    for f in tmp_path.iterdir():
        assert "PRIVATE_P" not in f.read_text()
    saved = json.loads((tmp_path/"provenance.json").read_text())
    assert saved["demo_data"] is True and saved["evidence"] == "observational_transductive"


@pytest.mark.parametrize("limit",["0","50"])
def test_cli_invalid_sampling_limit_rejected(limit,monkeypatch):
    from analysis.causal import run
    monkeypatch.setattr("sys.argv",["causal","--max-rows",limit])
    with pytest.raises(SystemExit) as e:
        run.main()
    assert e.value.code == 2


def test_prepared_synthetic_frame_keeps_demo_source_without_sampling(causal_frame,tmp_path,monkeypatch):
    from analysis.causal import run
    source=tmp_path/"prepared.parquet"
    causal_frame.to_parquet(source)
    out=tmp_path/"out"

    def fake_fit(frame,destination,**kw):
        assert len(frame)==len(causal_frame) and kw["demo_data"] is True
        destination.mkdir()
        table=pd.DataFrame([dict(altitude="No Altitude",count_bucket="even",n_supported=0,
                                 contrast_bb_minus_offspeed=np.nan,status="insufficient_support")])
        return table,dict(demo_data=kw["demo_data"])

    monkeypatch.setattr(run,"fit_analysis",fake_fit)
    monkeypatch.setattr("sys.argv",["causal","--prepared",str(source),"--demo","--fast","--out",str(out)])
    run.main()
    meta=json.loads((out/"provenance.json").read_text())
    assert meta["demo_data"] is True and meta["game_sample_limit"] is None
