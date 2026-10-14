"""Adapters for fitting the final model families inside each outer holdout.

Pitching+ combination weights use inner pitcher-held-out predictions from the
outer training set. Outer test rows cannot enter any of these estimator fits.
Shared target/feature preparation remains exploratory and is disclosed separately.
"""
from __future__ import annotations

from stuffplus import splits
from stuffplus.models import multitarget as mt
from stuffplus.models.pitching import (
    PITCHING_FEATURES, PitchingComponents, batter_table, run_oof, with_batter,
)
from stuffplus.models.stuff import StuffModel


class PitchingEstimator:
    def __init__(self, fast=False):
        self.class_rounds = 10 if fast else 300
        self.contact_rounds = 8 if fast else 200
        self.target_rounds = 8 if fast else 200
        self.inner_k = 2 if fast else 5

    def fit(self, frame):
        train = frame.reset_index(drop=True).copy()
        k = min(self.inner_k, train.pitcher_anon_id.nunique())
        if k < 2:
            raise ValueError("Pitching+ requires >=2 training pitchers for inner combination fitting")
        folds = list(splits.pitcher_group_kfold(train, k=k))
        oof = run_oof(train, folds, self.class_rounds, self.contact_rounds, self.target_rounds)
        self.combiner = mt.Combiner().fit(oof["rates"], train.rv_x.to_numpy(float))
        self.batters, self.priors = batter_table(train)
        training = with_batter(train, self.batters, self.priors)
        self.component = PitchingComponents(
            class_rounds=self.class_rounds, contact_rounds=self.contact_rounds).fit(training)
        self.targets = mt.fit_targets(training, PITCHING_FEATURES, rounds=self.target_rounds)
        return self

    def predict_xrv(self, frame):
        # Same neutral-batter scoring used by the HACK-012 reported Pitching+.
        test = with_batter(frame, self.batters, self.priors, neutral=True)
        comp = self.component.predict_components(test)
        probs = mt.predict_targets(self.targets, test, PITCHING_FEATURES)
        rates = mt.event_rates(probs, test, comp.p_in_play.to_numpy(float), comp.xrv.to_numpy(float))
        return self.combiner.predict(rates)


class PhysicsNeutralEstimator:
    """Fit HACK-004 movement translation on outer training rows, then neutralize.

    This is an ablation of representation and density, not a causal experiment.
    """
    def __init__(self, features, rounds):
        self.features = features
        self.rounds = rounds

    def fit(self, frame):
        from stuffplus.altitude import physics_translator
        from stuffplus.features.shapes import fit_shapes

        shapes, _ = fit_shapes(frame)
        self.translate = physics_translator(shapes)
        self.model = StuffModel(features=self.features, **self.rounds)
        self.model.fit(self.translate(frame, 1.0, frame.rho.to_numpy(float)))
        return self

    def predict_xrv(self, frame):
        return self.model.predict_xrv(self.translate(frame, 1.0, frame.rho.to_numpy(float)))
