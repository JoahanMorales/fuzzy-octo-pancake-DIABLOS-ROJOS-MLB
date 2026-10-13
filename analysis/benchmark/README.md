# GAM benchmark (HACK-026)

From the repository root with requirements.txt installed:

```bash
python -m pytest -q tests/test_benchmark.py
python -m analysis.benchmark.run --demo --fast
python -m analysis.benchmark.run  # requires the private ISAC parquet
```

Outputs go to `reports/benchmark/demo/` or `reports/benchmark/real/`.
Only aggregate metrics, calibration bins, fold counts and metadata are written.
Demo results are marked `demo_data: true` in metadata and every CSV.

The GAM predicts precomputed `rv_x` with smooth velocity, IVB and arm-side HB,
plus an IVB × density tensor. Joint ridge-penalized shape intercepts provide
partial pooling; unseen shapes use the population smooth. Penalties are fixed
before evaluation. Median imputation and the shape vocabulary use training rows
only. Defaults use `AutoPitchType`, a tracker-derived shape proxy that can shift
with altitude. The Python interface accepts another prepared `shape_col`.

Pitcher CV, season holdout and altitude-bucket holdout use `stuffplus.splits`.
Each compares the GAM, component LightGBM StuffModel, count baseline and fixed
50/50 blend on the same eligible rows with shared metrics and paired
pitcher-cluster bootstrap intervals. Empty folds, missing contact training data
and nonfinite predictions fail explicitly. The blend is diagnostic, not a
selected ensemble; no deployment or claimed winner follows from these scores.

**Exploratory/transductive limitation:** the shared `prepare` pipeline estimates
run-value tables, contact targets, arsenal means and density normalization
before splitting. This benchmark isolates model fitting but does not certify
fully nested out-of-sample robustness. Altitude buckets are not named stadiums.
The GAM and LightGBM also use different feature sets and outcome formulations,
so this is a system comparison, not a controlled model-class ablation.
Synthetic results establish execution only; real-data validation remains needed.

References: [pyGAM terms and penalties](https://pygam.readthedocs.io/en/latest/notebooks/quick_start.html),
[tensor interactions](https://pygam.readthedocs.io/en/latest/notebooks/tour_of_pygam.html).
