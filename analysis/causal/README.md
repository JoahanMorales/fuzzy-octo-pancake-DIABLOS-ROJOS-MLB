# HACK-027: exploratory pitch-selection contrasts

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt -r analysis/causal/requirements.txt
OMP_NUM_THREADS=2 .venv/bin/python -m analysis.causal.run --demo --fast
OMP_NUM_THREADS=2 .venv/bin/python -m analysis.causal.run --fast
```

EconML 0.16.0 (MIT) requires scikit-learn <1.7; use this isolated environment
instead of modifying another task's interpreter. It is an optional research
dependency. Base CI tests preparation/support; the forest recovery test is skipped
unless the extra is installed. Full local Verify must include that extra.

The actual `CausalForestDML` API uses `discrete_treatment=True`, grouped nuisance
cross-fitting and a held-out 2026 evaluation cohort. See the
[primary API documentation](https://www.pywhy.org/EconML/_autosummary/econml.dml.CausalForestDML.html).
Treatment is breaking (Slider/Curveball) minus offspeed (Changeup/Splitter).
Negative contrast means lower modelled xRV for breaking pitches; it does not
identify what would happen if a coach changed pitch selection.

Covariates are count, batter/pitcher handedness, game density, prior fastball
velocity, the preceding pitch and game state. Current-pitch physics, location,
outcomes and model scores are excluded. Past-only profile construction uses
available sampled history; unavailable history has an explicit indicator.
Pitch-family mixtures, air-density reference and proxy run-value targets are
globally prepared, hence **transductive**. Unassigned families fall back to the
recorded pitch label and the fraction is reported. This can introduce label bias.
Reconstructed density uses whole-game observations and is not verified as
available before a coach selects the pitch; this is a retrospective diagnostic.

Forest/nuisance fit calls use 2024/2025 rows, with 2026 rows held out. Globally
prepared training labels can nevertheless depend on 2026 outcomes; this prevents
an honest inductive holdout claim and is included in the transductive warning.
Nuisance folds keep pitchers together. Propensities are group-OOF in training
and train-fitted in the test cohort. Support is restricted to [0.1,0.9], a chosen
diagnostic threshold, with >=30 pitches of EACH treatment and >=5 pitchers per
reported cell. Other cells are labelled insufficient; no recommendation is made.

Fast mode samples about 12,000 rows by selecting seeded whole games before
preparation, preserving row chronology and half-innings. Sampling never examines
outcomes and can exceed the limit by the last game's size. The selected games
may not cover every park/year well. `--max-rows` changes this cap; full mode uses
all games. Reduced contact/forest/nuisance settings are labelled `fast=true`.

`--prepared PATH --outcome rv_x_oof` accepts a local prepared parquet with a true
OOF outcome column and the listed covariates. No OOF column is silently invented.
Use `--prepared PATH --demo` when the supplied frame is synthetic; it retains
the demo source flag. Prepared inputs are not sampled and reject `--max-rows`.
Default raw input uses the existing expected-run-value proxy (`rv_x`), not the
HACK-012 prediction. Its origin is explicit in provenance; true OOF sourcing is
a remaining stronger-evidence path, not a causal-identification fix.

Outputs in `reports/causal/{demo,official_fast,official}/` contain only nine
count/altitude aggregate cells, support counts, contrast summaries and provenance.
Conditional CIs resample test pitchers with the fitted forest fixed; they do
not include model-estimation uncertainty, shared-game dependence or unmeasured
confounding. Forest row-based intervals are deliberately not exported as valid
pitcher-cluster causal intervals. No individual pitchers/pitches or raw parquet
are committed. `promotion_allowed=false` prevents interpreting these outputs
as a validated tactical policy. No betting use.
