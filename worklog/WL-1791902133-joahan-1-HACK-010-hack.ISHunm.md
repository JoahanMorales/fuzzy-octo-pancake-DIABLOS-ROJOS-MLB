# worklog/WL-1791902133-joahan-1-HACK-010-hack.ISHunm.md · HACK-010

## Live summary
- Done: pytest tests/test_model_stuff.py exit 0 (8 passed); full suite passed; smoke exit 0 PRODUCT_PASS. Real data (analysis/stuff_model/run.py, 173s, bundle v1): first 50 pitches -> rest of season r=0.230 vs own results 0.051 (4.5x); split-half 0.80 vs 0.18; per-pitch skill +0.07% vs pitch-type baseline, -0.03% vs count baseline (pure stuff excludes count, documented); distill R2 0.92; altitude by type: CH -14.9 .. FC -5.0. Scope note: stuffplus/serving.py (HACK-031, mine, integrated) builds arm_angle + fastball diffs from PitchInput.arsenal. Branch from main, single merge base.
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_model_stuff.py`
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-010?expand=1; run .uak/bin/smoke

## History
- 1791902133 | CLAIMED | joahan-1 | claim; next: feature matrix builder using `train_lgbm_oof` from `models/common.py`.
- 1791902976 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-010?expand=1; evidence: pytest tests/test_model_stuff.py exit 0 (8 passed); full suite passed; smoke exit 0 PRODUCT_PASS. Real data (analysis/stuff_model/run.py, 173s, bundle v1): first 50 pitches -> rest of season r=0.230 vs own results 0.051 (4.5x); split-half 0.80 vs 0.18; per-pitch skill +0.07% vs pitch-type baseline, -0.03% vs count baseline (pure stuff excludes count, documented); distill R2 0.92; altitude by type: CH -14.9 .. FC -5.0. Scope note: stuffplus/serving.py (HACK-031, mine, integrated) builds arm_angle + fastball diffs from PitchInput.arsenal. Branch from main, single merge base.; reviewer: -
