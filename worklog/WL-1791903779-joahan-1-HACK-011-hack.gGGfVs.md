# worklog/WL-1791903779-joahan-1-HACK-011-hack.gGGfVs.md · HACK-011

## Live summary
- Done: reject fixed (docs vs CSV, fallback documented, caveat, error tests); tests/test_model_location.py 10 passed; full suite passed; smoke exit 0
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_model_location.py`
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-011?expand=1; run .uak/bin/smoke

## History
- 1791903779 | CLAIMED | joahan-1 | claim; next: 2-D smoothed target encoding vs LightGBM on (x, z, count); pick by OOF RMSE.
- 1791904494 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-011?expand=1; evidence: pytest tests/test_model_location.py exit 0 (7 passed); full suite passed; smoke exit 0. Real data (analysis/location_model/run.py): per-pitch skill vs count baseline +2.9% [2.82,2.98]; 5-outcome logloss 1.028 vs count 1.451; Location+ split-half 0.57 vs observed 0.25; altitude by zone in altitude_by_zone.csv; heatmaps (blue=good). Stacked on HACK-010 (merge 010 first) + main merged.; reviewer: -
- 1791907000 | REVIEW | victor-1 | review; approve; SHA 6a4741e7ba9bda1e2c5cc8cbbd2fb9f1d70d0699; reviewer victor-1
- 1791907182 | REVIEW | victor-1 | review; reject; SHA 6a4741e7ba9bda1e2c5cc8cbbd2fb9f1d70d0699; reviewer victor-1
- 1791919385 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-011?expand=1; evidence: reject fixed: pitch_family (identity) replaces AutoPitchType as feature and reference key; full suite 123 passed; smoke exit 0; real data skill +2.78% [2.70,2.87] vs count baseline, split-half 0.58; main merged, single merge base. Includes HACK-010 commits (merge 010 first) + 2-line support in common.py/serving.py for pitch_family.; reviewer: -
- 1791921163 | REVIEW | sebastian-2 | review; reject; SHA c452e395e49cb6f9516811b3de426155fadf75a9; reviewer sebastian-2
- 1791921886 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-011?expand=1; evidence: reject fixed (docs vs CSV, fallback documented, caveat, error tests); tests/test_model_location.py 10 passed; full suite passed; smoke exit 0; reviewer: -
- 1791925208 | REVIEW | victor-1 | review; approve; SHA 639e4b0bad4c539e4d360ac995021ff9a4bbc02e; reviewer victor-1
- 1791925375 | REVIEW | joahan-1 | heartbeat; lease until 1791939775
