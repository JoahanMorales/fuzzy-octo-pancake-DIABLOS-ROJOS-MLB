# HACK-015
ID: HACK-015
State: REVIEW
Owner: joahan-1
Branch: feat/hack-015
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-015
Worklog: worklog/WL-1791919921-joahan-1-HACK-015-hack.6mDoz8.md
Priority: P0
Paths: stuffplus/altitude.py, analysis/altitude_delta/, reports/altitude_delta/, tests/test_altitude.py
Depends: HACK-004, HACK-010, HACK-013
Verify: `python -m pytest -q tests/test_altitude.py`
Lease-Until: 1791935112
Updated: 1791920712
Task-Base: f0de095681b4c572ce62e45430de89a9f89dce77
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-015?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-015?expand=1
Evidence: pytest tests/test_altitude.py exit 0 (6 passed); full suite passed; smoke exit 0. Real data: league ΔStuff+ -10.3 at rho 0.819; sweeper -4.6 [-5.4,-3.9] best, riding 4S -16.0 [-16.3,-15.6] worst; triangulation same sign 7/7 families (within-pitcher Extreme vs No, model and results). Uses pitch_family (invariant), per-family proportional physics. Branch from main, single merge base; all files in Paths.
Events: 2
Checkpoints: 0
Sessions: 1
Last-Checkpoint: 0
Task-Tip: 922fc4466817cbf827e787efe90376bfbddcd5a0
