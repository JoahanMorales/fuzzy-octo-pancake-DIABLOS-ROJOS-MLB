# Validation diagnostics (HACK-014, partial)

Run `python -m analysis.validation.run --demo --fast` for a reproducible smoke run.
Run `python -m analysis.validation.run --data /path/to/stuff_model_df.parquet`
for official input. Without `--demo`, missing input fails; synthetic input is never
selected automatically. `--out` changes the aggregate output directory. Fast mode
uses fewer boosting rounds and bootstrap draws, not different holdout rules.

Outputs: `validation_table.csv` (model × split × metric), `calibration.csv`,
`stability.csv`, `status.csv`, `provenance.json`, and `validation.md`. No individual
pitches, pitcher IDs, game IDs, fitted models or raw data are exported.
All tables encode `demo_data` and `evidence=exploratory_transductive`.

Model fits and count means use training rows only. The existing shared preparation
fits run expectancy, event weights, expected contact values, density reference,
arsenal statistics and pitch identity globally. Thus even official input produces
exploratory diagnostics, not honest inductive OOS evidence. No ensemble or serving
artifact is changed. Physics ablations do not estimate a causal altitude effect.
Calibration means are in run-value units. Skill is fractional RMSE reduction;
its 95% CI uses paired pitcher-cluster bootstrap draws, conditional on preparation.

Pitching+ uses HACK-012 outcome models and fitted combination. Its weights are
estimated on inner pitcher-held-out predictions from the outer training set;
the component and target models then fit on the outer training rows only.
Batter adjustment is train-fitted and scoring uses neutral batters. The Stuff+
variants use altitude-invariant pitch_family (including the reported fallback);
the physics-neutral ablation fits HACK-004 movement translation on outer training
rows and transforms training and test movement to sea level without density as
a feature. This is a predictive ablation, not an isolated causal physics effect.

Consumers can inject a `ModelSpec` with `fit(train_frame)` and
`predict_xrv(test_frame)`. Missing Pitching+ in a custom registry is explicit.
Every estimator is created fresh per fold. Exceptions and missing predictions fail rather than silently
changing the shared scored cohort. Missing split keys fail; empty season/altitude
splits and absent park IDs get explicit status rows. Inferred HACK-003 franchise
IDs supply leave-one-park-out splits; these are not independently verified stadiums.

Stability reports odd/even games within pitcher-season, adjacent-year correlations,
next-year observed RV with raw RV/whiff comparators and first N versus disjoint next
N pitches. At least three nonconstant paired samples are required; other rows say
`insufficient`. Input order must be chronological (the raw loader preserves it).
OOF scores use full-season feature summaries, so sample curves do not determine how
many pitches are sufficient prospectively. A pitcher's seasons share the same
pitcher-held-out model, which can train on future seasons of other pitchers;
this is not a frozen-model future-season forecast.

## Required fold-preparation contract before OOS promotion

The current suite does **not** implement this contract. A future preparer must fit
only on raw training rows and return `(prepared_train, prepared_test, provenance)`
in the original positional order. Run-expectancy/linear-weight tables, the contact
target estimator, density normalization, pitch identity and arsenal reference
statistics must remain frozen when transforming held-out rows. Unknown pitchers,
pitch families and parks need training-only fallback rules. Test outcomes may
define evaluation labels through frozen target transforms but cannot fit them.
Chronological evaluation must construct arsenal prefixes without future pitches.
Tests must perturb held-out outcomes and features and show every fitted parameter
is unchanged; estimator row-isolation checks alone cannot prove this.

Keep `acceptance_complete=false` until that contract and the official-data run
have been independently verified. This PR delivers the runner,
aggregate outputs and explicit missing-evidence states, not complete C1/C2 evidence.
