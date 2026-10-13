# worklog/WL-1791920805-joahan-1-HACK-019-hack.PFFwsv.md · HACK-019

## Live summary
- Done: pytest tests/test_explain.py exit 0 (8 passed: contributions sum to served Stuff+ within 0.15, altitude breakdown = compare_environments delta); full suite passed; smoke exit 0. Real data (python -m stuffplus.explain, 60k sample): top drivers IVB 3.4, air density 3.3, velo 2.9 pts; examples.csv (e.g. riding 4S 122.6 at sea level, -13.0 in CDMX: -10 because CDMX air removes 3.4in of ride). All files in Paths.
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_explain.py`
- Next: Integrated in main: b4d24886d03beb9197bb2c818b06a61eb04d755e

## History
- 1791920805 | CLAIMED | joahan-1 | claim; next: `shap.TreeExplainer` on the Stuff+ model, converted to Stuff+ units with the scaler sd.
- 1791921483 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-019?expand=1; evidence: pytest tests/test_explain.py exit 0 (8 passed: contributions sum to served Stuff+ within 0.15, altitude breakdown = compare_environments delta); full suite passed; smoke exit 0. Real data (python -m stuffplus.explain, 60k sample): top drivers IVB 3.4, air density 3.3, velo 2.9 pts; examples.csv (e.g. riding 4S 122.6 at sea level, -13.0 in CDMX: -10 because CDMX air removes 3.4in of ride). All files in Paths.; reviewer: -
- 1791925212 | REVIEW | victor-1 | review; approve; SHA f2ca870c39278a44a350c862032da5f871fc2fbd; reviewer victor-1
- 1791925886 | REVIEW | joahan-1 | heartbeat; lease until 1791940286
- 1791926347 | INTEGRATED | joahan-1 | merge; smoke and Verify PASS; commit b4d24886d03beb9197bb2c818b06a61eb04d755e; reviewer victor-1
