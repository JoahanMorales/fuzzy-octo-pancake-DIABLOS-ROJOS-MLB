# worklog/WL-1791871016-joahan-1-HACK-005-hack.hSdC2P.md · HACK-005

## Live summary
- Done: baselines, metrics, compare, oof, predictiveness, report
- Decision: skill = % RMSE/logloss reduction, pitcher-cluster bootstrap
- Why: pitches of one pitcher are not independent
- Failing: none
- Commands: pytest tests/test_evaluate.py; python -m stuffplus.baseline
- Next: Wait for review of SHA ba49eba

## History
- 1791871016 | CLAIMED | joahan-1 | claim; next: `CountBaseline.fit/predict` with groupby on `count`.
- 1791871344 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-005?expand=1; evidence: pytest tests/test_evaluate.py exit 0 (9 passed); smoke PRODUCT_PASS; real data python -m stuffplus.baseline 58s -> reports/baseline/baseline_metrics.csv: rv RMSE 0.2673 (count), park holdout bias +0.012 runs/pitch in Extreme; t_whiff AUC 0.53 count / 0.60 count x family; stacked on hack-013; reviewer: -
- 1791871406 | REVIEW | joahan-1 | checkpoint; next: Wait for review of SHA ba49eba
