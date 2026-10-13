# HACK-019
ID: HACK-019
State: REVIEW
Owner: joahan-1
Branch: feat/hack-019
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-019
Worklog: worklog/WL-1791920805-joahan-1-HACK-019-hack.PFFwsv.md
Priority: P1
Paths: stuffplus/explain.py, reports/explain/, tests/test_explain.py
Depends: HACK-010
Verify: `python -m pytest -q tests/test_explain.py`
Lease-Until: 1791935883
Updated: 1791921483
Task-Base: f0de095681b4c572ce62e45430de89a9f89dce77
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-019?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-019?expand=1
Evidence: pytest tests/test_explain.py exit 0 (8 passed: contributions sum to served Stuff+ within 0.15, altitude breakdown = compare_environments delta); full suite passed; smoke exit 0. Real data (python -m stuffplus.explain, 60k sample): top drivers IVB 3.4, air density 3.3, velo 2.9 pts; examples.csv (e.g. riding 4S 122.6 at sea level, -13.0 in CDMX: -10 because CDMX air removes 3.4in of ride). All files in Paths.
Events: 3
Checkpoints: 0
Sessions: 2
Last-Checkpoint: 0
Task-Tip: f2ca870c39278a44a350c862032da5f871fc2fbd
