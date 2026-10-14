# Validation evidence (HACK-014, exploratory)

The CSV/JSON/Markdown files directly in this directory are synthetic smoke
evidence (`demo_data=true`). `official_fast/` contains the real-data diagnostic
run (`demo_data=false`, `fast=true`). Both sets are explicitly
`evidence=exploratory_transductive` and `acceptance_complete=false`.

Official command, run against implementation SHA `9ee6af7`:

```sh
OMP_NUM_THREADS=2 python -m analysis.validation.run --fast --out reports/validation/official_fast
```

The command exited 0 after 1,325 seconds. Input was the human-provided parquet
in the main checkout's git-ignored `data/raw/`: 635,002 rows and 84 columns.
Cleaning retained 627,602 rows. The run evaluates all six model/ablation/baseline
entries on identical scored rows within each of 23 splits: pitcher folds, season,
extreme altitude and 20 leave-one-inferred-park-out splits. Inferred franchise
labels are not independently verified stadium IDs. LOPO test sets collectively
cover 627,449 rows; 153 prepared rows lack a recovered park ID and are excluded
from those park tests. They remain in the main pitcher/season/altitude evaluation.
Identity fallback coverage
is recorded in provenance (about 0.696% of prepared rows).

## Fast diagnostic results

Positive skill means fractional RMSE reduction against the train-fitted mean
rv_x by count; the following table converts it to percent. Confidence intervals
use 30 paired pitcher-cluster bootstrap draws and are conditional on the globally
prepared labels/features. This reduced run is not final model-quality evidence.

| Split | Scored rows | Model | RMSE | RMSE reduction vs count |
|---|---:|---|---:|---:|
| Pitcher folds | 627,602 | Baseline | 0.19776 | 0% |
| Pitcher folds | 627,602 | Stuff+ | 0.19778 | -0.009% |
| Pitcher folds | 627,602 | Location+ | 0.19329 | 2.260% |
| Pitcher folds | 627,602 | Pitching+ | 0.19176 | 3.032% |
| 2026 season | 129,570 | Baseline | 0.20071 | 0% |
| 2026 season | 129,570 | Stuff+ | 0.20075 | -0.018% |
| 2026 season | 129,570 | Location+ | 0.19621 | 2.243% |
| 2026 season | 129,570 | Pitching+ | 0.19478 | 2.956% |
| Extreme altitude | 181,032 | Baseline | 0.20516 | 0% |
| Extreme altitude | 181,032 | Stuff+ | 0.20516 | approximately 0% |
| Extreme altitude | 181,032 | Location+ | 0.20122 | 1.920% |
| Extreme altitude | 181,032 | Pitching+ | 0.19993 | 2.550% |

Stuff+ does not show a meaningful gain in this fast run. The neutral-physics
ablation has negative skill on these three splits. This does not prove the
physics layer helps, and no ensemble, serving artifact or deployment is promoted.

QA checked finite RMSE/MAE, equal denominators for all models within a split,
complete split/model coverage, explicit real-data flags, and aggregate-only CSV
columns. Full values and intervals are in `official_fast/validation_table.csv`;
calibration, stability and split status are in the adjacent files.

## Remaining acceptance

Shared target/feature preparation still uses global run expectancy, event weights,
contact target estimates, density normalization, identity and arsenal statistics.
These can inflate apparent generalization and stability. Model fitting, Pitching+
combination weights and this physics translation are training-only, but that does
not remove preprocessing transduction. The documented fold-preparation contract
and final settings must be implemented/run and independently reviewed before
claiming complete C1/C2 evidence or prospective sample-size requirements.
