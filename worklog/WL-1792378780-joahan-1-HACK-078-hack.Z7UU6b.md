# worklog/WL-1792378780-joahan-1-HACK-078-hack.Z7UU6b.md · HACK-078

## Live summary
- Done: 08c73b33: python analysis/business_value/run.py (5 production v2 fits OOF, 21 min) exit 0; pytest tests/test_value.py pass; stuff_scale_calibration model_version stuff_v2, cross-check 8.69e-4 vs direct 8.68e-4; runs_per_win.csv and pythagorean.csv unchanged; per point 7.24e-4 -> 8.68e-4, +10 Stuff+ HH wins 1.26 -> 1.51, 1 SD 0.69 -> 0.77 wins
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_value.py`
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-078?expand=1; run .uak/bin/smoke

## History
- 1792378780 | CLAIMED | joahan-1 | claim; next: replace `stuff_run.StuffModel().oof` and `bundle.scalers["stuff"]` in run.py:85-92 with the production v2 OOF and scaler.
- 1792381204 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-078?expand=1; evidence: 08c73b33: python analysis/business_value/run.py (5 production v2 fits OOF, 21 min) exit 0; pytest tests/test_value.py pass; stuff_scale_calibration model_version stuff_v2, cross-check 8.69e-4 vs direct 8.68e-4; runs_per_win.csv and pythagorean.csv unchanged; per point 7.24e-4 -> 8.68e-4, +10 Stuff+ HH wins 1.26 -> 1.51, 1 SD 0.69 -> 0.77 wins; reviewer: -
