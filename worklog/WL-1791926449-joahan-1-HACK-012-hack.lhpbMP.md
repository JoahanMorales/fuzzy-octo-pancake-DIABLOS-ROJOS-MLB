# worklog/WL-1791926449-joahan-1-HACK-012-hack.lhpbMP.md · HACK-012

## Live summary
- Done: pytest tests/test_model_pitching.py exit 0 (6 passed); full suite passed; smoke exit 0. Real data OOF by pitcher: combined Pitching+ skill vs count baseline +3.88% [3.78,4.00] on rv_x, +2.17% on rv; R2 0.078 vs 0.002; 8 targets calibrated (ECE .003-.017; called strike AUC .974 vs .685); first 200 pitches -> rest of season r .333 vs .110; next season .283 vs .202; split-half .742. Bundle pitching_xrv distilled R2 .942. All files in Paths; branch from main.
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_model_pitching.py`
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-012?expand=1; run .uak/bin/smoke

## History
- 1791926449 | CLAIMED | joahan-1 | claim; next: loop over targets with `train_lgbm_oof`.
- 1791928285 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-012?expand=1; evidence: pytest tests/test_model_pitching.py exit 0 (6 passed); full suite passed; smoke exit 0. Real data OOF by pitcher: combined Pitching+ skill vs count baseline +3.88% [3.78,4.00] on rv_x, +2.17% on rv; R2 0.078 vs 0.002; 8 targets calibrated (ECE .003-.017; called strike AUC .974 vs .685); first 200 pitches -> rest of season r .333 vs .110; next season .283 vs .202; split-half .742. Bundle pitching_xrv distilled R2 .942. All files in Paths; branch from main.; reviewer: -
- 1791930606 | REVIEW | victor-1 | review; approve; SHA 0d7dd05ec4ca9f83bc867e62a5ee31fb7cb36fd6; reviewer victor-1
