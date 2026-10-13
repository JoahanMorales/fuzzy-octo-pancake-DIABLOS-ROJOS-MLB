# Benchmark evidence

Run `python -m analysis.benchmark.run --demo --fast` for explicitly synthetic
execution evidence in `demo/`. Run without `--demo` for private-data aggregates
in `real/`. No raw rows, IDs or fitted models are exported.

Read each run's `metadata.json` before citing its metrics. All results are
exploratory/transductive because shared target and feature preparation precedes
splitting. Synthetic metrics are not evidence of LMB model quality. No real-data
result has been verified in this checkout.
