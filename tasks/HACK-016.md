# HACK-016
ID: HACK-016
State: REVIEW
Owner: joahan-1
Branch: feat/hack-016
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-016
Worklog: worklog/WL-1791932819-joahan-1-HACK-016-hack.UPHsIq.md
Priority: P0
Paths: stuffplus/score.py, analysis/scoring/, reports/leaderboards/, tests/test_score.py
Depends: HACK-012, HACK-013
Verify: `python -m pytest -q tests/test_score.py`
Lease-Until: 1791948464
Updated: 1791934064
Task-Base: dcb3f2809a47993e919f4c7e426890a561f21376
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-016?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-016?expand=1
Evidence: pytest tests/test_score.py exit 0 (3 passed); full suite passed; smoke exit 0. Real data (python -m stuffplus.score): 623,231 pitches scored OOF by pitcher -> artifacts/scores/pitch_scores.parquet (git-ignored, email deliverable); leaderboards 818 pitcher-seasons, 3,546 pitcher x pitch; by_park: air effect +4.3 (rho 1.06) .. -10.7 (rho 0.81), r=0.996 with rho; README numbers checked vs CSVs. All files in Paths.
Events: 2
Checkpoints: 0
Sessions: 1
Last-Checkpoint: 0
Task-Tip: a1296c796fd0d4475232b65b0775adbb9f2e8be0
