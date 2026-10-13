# worklog/WL-1791919921-joahan-1-HACK-015-hack.6mDoz8.md · HACK-015

## Live summary
- Done: pytest tests/test_altitude.py exit 0 (6 passed); full suite passed; smoke exit 0. Real data: league ΔStuff+ -10.3 at rho 0.819; sweeper -4.6 [-5.4,-3.9] best, riding 4S -16.0 [-16.3,-15.6] worst; triangulation same sign 7/7 families (within-pitcher Extreme vs No, model and results). Uses pitch_family (invariant), per-family proportional physics. Branch from main, single merge base; all files in Paths.
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_altitude.py`
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-015?expand=1; run .uak/bin/smoke

## History
- 1791919921 | CLAIMED | joahan-1 | claim; next: `altitude.counterfactual_scores(df, bundle, rho_a, rho_b)`.
- 1791920712 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-015?expand=1; evidence: pytest tests/test_altitude.py exit 0 (6 passed); full suite passed; smoke exit 0. Real data: league ΔStuff+ -10.3 at rho 0.819; sweeper -4.6 [-5.4,-3.9] best, riding 4S -16.0 [-16.3,-15.6] worst; triangulation same sign 7/7 families (within-pitcher Extreme vs No, model and results). Uses pitch_family (invariant), per-family proportional physics. Branch from main, single merge base; all files in Paths.; reviewer: -
