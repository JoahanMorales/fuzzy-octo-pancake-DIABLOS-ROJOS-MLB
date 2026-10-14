# HACK-014
ID: HACK-014
State: REVIEW
Owner: joahan-1
Branch: feat/hack-014
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-014
Worklog: worklog/WL-1791920599-sebastian-1-HACK-014-hack.Q6gbOp.md
Priority: P0
Paths: stuffplus/validation/, analysis/validation/, reports/validation/, tests/test_validation.py
Depends: HACK-005, HACK-010
Verify: `python -m pytest -q tests/test_validation.py`
Lease-Until: 1791964430
Updated: 1791950030
Task-Base: f0de095681b4c572ce62e45430de89a9f89dce77
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-014?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-014?expand=1
Evidence: pytest tests/test_validation.py exit 0 (19 passed); full suite passed; smoke exit 0. Production real-data holdouts (official_full, acceptance_complete true): Pitching+ season +3.74% [3.54,3.94], park +3.28% [3.15,3.39]; pitcher kfold +3.88% (HACK-012); LOPO 20/20 parks >0 (fast). Altitude bias in Extreme with model never trained there: baseline +0.0109, Stuff+ no density +0.0046, Stuff+ +0.0025, Pitching+ +0.0020 runs/pitch. summary.md generated from CSVs. Continues sebastian-1's runner.
Events: 15
Checkpoints: 5
Sessions: 4
Last-Checkpoint: 1791941516
Task-Tip: 5c3e8ecf943d0183238fdce93d519f38871b8416
