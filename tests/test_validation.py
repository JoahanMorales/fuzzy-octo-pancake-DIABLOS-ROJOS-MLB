"""Isolation, paired evaluation, missing evidence and aggregate-only output."""
import json

import numpy as np
import pandas as pd
import pytest

from stuffplus import evaluate
from stuffplus.validation.run_all import ModelSpec, run_all, split_plan, validate_indices
from stuffplus.validation.stability import stability_table


@pytest.fixture
def frame():
    rows = []
    rng = np.random.default_rng(5)
    for year in (2024, 2025, 2026):
        for pitcher in range(9):
            for game in range(4):
                for pitch in range(10):
                    talent = pitcher / 40
                    rows.append(dict(year=year, pitcher_anon_id=f"PRIVATE_P{pitcher}",
                        game_anon_id=f"PRIVATE_G{year}_{pitcher}_{game}",
                        altitude_category=("No Altitude", "Medium Altitude", "Extreme Altitude")[game % 3],
                        park_id=f"PRIVATE_PARK{game % 3}", count=f"{pitch % 4}-{pitch % 3}",
                        rv_x=talent + rng.normal(0, .2), rv=talent + rng.normal(0, .4),
                        t_whiff=float(rng.random() < .3), signal=talent))
    return pd.DataFrame(rows)


class Spy:
    fits = []

    def fit(self, train):
        self.train = train.index.to_numpy()
        self.pitchers = set(train.pitcher_anon_id)
        self.fits.append(self.train)
        return self

    def predict_xrv(self, test):
        assert not set(self.train) & set(test.index)
        return test.signal.to_numpy()


def run(frame, out, **kwargs):
    return run_all(frame, out, demo_data=True, models={"signal": ModelSpec(Spy)},
                   k=3, n_boot=25, min_n=5, sample_sizes=(5, 10), **kwargs)


def test_models_are_refit_and_splits_isolate_groups(frame, tmp_path):
    Spy.fits = []
    result = run(frame, tmp_path)
    assert len(Spy.fits) == 8  # three pitcher folds + season + altitude + three parks
    assert (result["validation_table"].query("metric == 'rmse'").value > 0).all()
    for split, folds in split_plan(frame, k=3):
        for tr, te in folds:
            assert not set(tr) & set(te)
            if split == "pitcher_kfold":
                assert not set(frame.iloc[tr].pitcher_anon_id) & set(frame.iloc[te].pitcher_anon_id)
            if split == "season_holdout":
                assert set(frame.iloc[tr].year) == {2024, 2025}
                assert set(frame.iloc[te].year) == {2026}
            if split.startswith("leave_one"):
                assert not set(frame.iloc[tr].park_id) & set(frame.iloc[te].park_id)


def test_count_baseline_does_not_fit_test_targets(frame, tmp_path):
    # The 2026 signal shift may affect test loss, but never the fitted count mean.
    frame.loc[frame.year == 2026, "rv_x"] += 10
    table = run(frame, tmp_path)["validation_table"]
    bias = table.query("split == 'season_holdout' and model == 'baseline' and metric == 'bias'").value.iloc[0]
    assert bias > 9.8


def test_reports_export_aggregates_and_explicit_pending_evidence(frame, tmp_path):
    tables = run(frame, tmp_path)
    for file in tmp_path.iterdir():
        text = file.read_text()
        assert "PRIVATE_" not in text
        assert "exploratory" in text.lower() or "transductive" in text.lower()
    status = tables["status"]
    assert status.query("model == 'Pitching+' and status == 'unavailable'").shape[0] == 1
    meta = json.loads((tmp_path / "provenance.json").read_text())
    assert meta["demo_data"] is True
    assert meta["evidence"] == "exploratory_transductive"


def test_missing_splits_and_park_maps_are_explicit(frame, tmp_path):
    frame = frame[frame.year != 2026].drop(columns="park_id")
    status = run(frame, tmp_path)["status"]
    assert status.query("split == 'season_holdout'").status.iloc[0] == "skipped"
    assert status.query("split == 'leave_one_park_out'").status.iloc[0] == "unavailable"


def test_all_null_park_maps_are_explicit(frame, tmp_path):
    frame["park_id"] = pd.NA
    status = run(frame, tmp_path)["status"]
    assert status.query("split == 'leave_one_park_out'").status.iloc[0] == "unavailable"


def test_baseline_failure_does_not_shrink_evaluation(frame, tmp_path, monkeypatch):
    from stuffplus.validation import run_all as module

    def broken(self, test, target):
        return np.full(len(test), np.nan)

    monkeypatch.setattr(module.CountBaseline, "predict", broken)
    with pytest.raises(ValueError, match="baseline: expected finite"):
        run(frame, tmp_path)
    assert not (tmp_path / "validation_table.csv").exists()


@pytest.mark.parametrize("folds", [
    [(np.array([0, 1]), np.array([1, 2]))],
    [(np.array([0]), np.array([2])), (np.array([1]), np.array([2]))],
    [(np.array([0, 0]), np.array([1]))],
    [(np.array([0]), np.array([3]))],
])
def test_invalid_folds_fail(folds):
    with pytest.raises(ValueError):
        validate_indices(folds, 3)


def test_prediction_failure_is_not_silently_dropped(frame, tmp_path):
    class Broken(Spy):
        def predict_xrv(self, test):
            return np.full(len(test), np.nan)
    with pytest.raises(ValueError, match="finite prediction"):
        run_all(frame, tmp_path, demo_data=True, models={"broken": ModelSpec(Broken)}, k=3)
    assert not (tmp_path / "validation_table.csv").exists()


def test_zero_baseline_loss_rejected(frame, tmp_path):
    frame["rv_x"] = 0.0
    with pytest.raises(ValueError, match="zero baseline loss"):
        run(frame, tmp_path)


def test_cluster_bootstrap_is_paired_and_clustered():
    y = np.array([1., 3., 5., 8., 11., 15.])
    groups = np.repeat(["a", "b", "c"], 2)
    base = y + np.repeat([1., 2., 3.], 2)
    better = y + (base-y) / 2
    table = evaluate.compare({"baseline": base, "half_error": better}, y, groups=groups, n_boot=100)
    # Each cluster draw has exactly half the RMSE; independent draws would not.
    for col in ("skill_vs_baseline", "skill_lo", "skill_hi"):
        assert table.set_index("model").loc["half_error", col] == pytest.approx(.5)
    assert table.set_index("model").loc["baseline", "skill_hi"] == 0


def test_stability_uses_disjoint_samples_and_handles_tiny_groups(frame):
    tab = stability_table(frame, frame.signal, "signal", min_n=5, sample_sizes=(10, 500))
    assert tab.query("check == 'split_half_games' and source == 'pred'").correlation.iloc[0] > .99
    assert tab.query("check == 'sample_stability' and pitches == 500").status.eq("insufficient").all()
    tiny = stability_table(frame.head(1), np.zeros(1), "tiny", min_n=5, sample_sizes=(10,))
    assert tiny.status.eq("insufficient").all()


@pytest.fixture(scope="module")
def prepared(_synthetic_cache):
    from analysis.stuff_model.run import prepare
    from stuffplus import schema
    from stuffplus.models.pitching import build_features

    return build_features(prepare(schema.clean(_synthetic_cache.copy())))


def test_pitching_inner_isolation_alignment_and_target_independence(prepared, monkeypatch):
    from stuffplus import splits
    from stuffplus.validation import models

    tr, te = next(splits.pitcher_group_kfold(prepared, k=3))
    train, test = prepared.iloc[tr].copy(), prepared.iloc[te].copy()
    # Nonconsecutive source indices expose accidental label/position mixing.
    assert not train.index.equals(pd.RangeIndex(len(train)))
    original_oof = models.run_oof
    original_fit = models.mt.Combiner.fit
    calls = []

    def checked_oof(data, folds, *args):
        assert data.index.equals(pd.RangeIndex(len(data)))
        assert set(data.PitchUID) == set(train.PitchUID)
        assert not set(data.PitchUID) & set(test.PitchUID)
        for fit, hold in folds:
            assert not set(data.iloc[fit].pitcher_anon_id) & set(data.iloc[hold].pitcher_anon_id)
        result = original_oof(data, folds, *args)
        assert result["rates"].index.equals(data.index)
        return result

    def checked_combination(self, rates, y):
        assert rates.index.equals(pd.RangeIndex(len(train)))
        assert np.allclose(y, train.rv_x.to_numpy(float), equal_nan=True)
        calls.append(len(y))
        return original_fit(self, rates, y)

    monkeypatch.setattr(models, "run_oof", checked_oof)
    monkeypatch.setattr(models.mt.Combiner, "fit", checked_combination)
    estimator = models.PitchingEstimator(fast=True).fit(train)
    pred = estimator.predict_xrv(test)
    assert calls == [len(train)] and np.isfinite(pred).all()
    tampered = test.copy()
    for col in ["rv_x", "rv", *models.mt.TARGETS]:
        tampered[col] = 999999.0
    assert np.allclose(pred, estimator.predict_xrv(tampered))


def test_cli_preserves_pitch_identity_fallback_provenance(_synthetic_cache, tmp_path, monkeypatch):
    from analysis.validation import run as cli
    from analysis.stuff_model.run import prepare
    from stuffplus import schema
    from stuffplus.features.identity import assign_pitch_id

    initial = assign_pitch_id(prepare(schema.clean(_synthetic_cache.copy()))).assign(signal=0.0)
    initial.loc[initial.index[:5], "pitch_family"] = pd.NA
    initial.loc[initial.index[:5], "pitch_id"] = -1
    initial.loc[initial.index[:5], "pitch_family_assigned"] = False
    monkeypatch.setattr(cli, "prepare", lambda _: initial.copy())
    monkeypatch.setattr(cli, "build_maps", lambda _: {"park_map": pd.DataFrame({
        "game_anon_id": initial.game_anon_id.unique(), "franchise": "test_park"})})
    real_run = cli.run_all

    def custom_run(data, out, **kwargs):
        return real_run(data, out, models={"signal": ModelSpec(Spy)}, **kwargs)

    monkeypatch.setattr(cli, "run_all", custom_run)
    monkeypatch.setattr("sys.argv", ["validation", "--demo", "--fast", "--out", str(tmp_path)])
    cli.main()
    provenance = json.loads((tmp_path / "provenance.json").read_text())
    assert provenance["pitch_family_fallback_fraction"] >= 5 / len(initial)
