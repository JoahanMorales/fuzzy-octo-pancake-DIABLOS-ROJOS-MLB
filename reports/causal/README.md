# HACK-027 evidence: exploratory selection contrasts

`demo/` is synthetic (`demo_data=true`). `official_fast/` is a seeded sample of
whole games from the human-provided competition parquet (`demo_data=false`).
Both declare `evidence=observational_transductive` and `promotion_allowed=false`.
No raw rows, pitch IDs, pitcher IDs, fitted forests or tactical policy are exported.

Commands actually run in the isolated optional-dependency environment:

```sh
OMP_NUM_THREADS=2 .venv/bin/python -m pytest -q tests/test_causal.py
OMP_NUM_THREADS=2 .venv/bin/python -m analysis.causal.run --demo --fast
OMP_NUM_THREADS=2 .venv/bin/python -m analysis.causal.run --fast
```

Verify passed all eleven tests, including a real CausalForestDML recovery check
with a known simulated treatment effect. Both analysis commands exited 0; the
full product smoke passed. Aggregate QA checked counts, support conditions,
finite reported contrasts and intervals, missing unsupported contrasts, source
flags and absence of identifying columns.

## Official fast cohort

The approximately 12,000-row whole-game sample contains 4,730 eligible
breaking/offspeed observations with finite outcome and controls. The 2024/2025
training cohort has 3,894 rows, of which 3,524 pass group-OOF propensity support.
The 2026 holdout has 836 rows, of which 740 pass train-fitted support. Nine
count/altitude cells are reported; only three have >=30 observations of EACH
treatment and >=5 pitchers. Other contrasts are deliberately missing.

| Supported cell | Rows | Pitchers | BB minus offspeed xRV | Conditional composition interval |
|---|---:|---:|---:|---|
| No altitude, ahead | 130 | 30 | -0.007756 | [-0.009958, -0.005862] |
| No altitude, even | 171 | 31 | -0.009456 | [-0.011911, -0.006956] |
| Extreme altitude, even | 111 | 24 | -0.004597 | [-0.007756, -0.000332] |

These are estimated observational contrasts on a globally prepared proxy xRV,
not demonstrated effects of choosing one pitch instead of another. Intervals
only resample held-out pitchers while keeping the forest fixed; they omit model
uncertainty, shared-game dependence and confounding uncertainty.

**Important sample limitation:** 39.17% of prepared pitches lack enough sampled
history for an identity mixture and use the recorded pitch-label fallback.
Altitude-related label changes can bias these comparisons. The sample and fast
settings are a functionality/research diagnostic, not a recruiting, coaching or
submission-quality tactical result. Stronger evidence requires verified OOF
outcomes, larger/more representative identity coverage, a justified identification
strategy and sensitivity/overlap analysis. See `analysis/causal/README.md` and the
per-run provenance files for controls, preparation, settings and interpretation.
