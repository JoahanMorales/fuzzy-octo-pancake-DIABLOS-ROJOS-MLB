# HACK-012
ID: HACK-012
State: REVIEW
Owner: joahan-1
Branch: feat/hack-012
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-012
Worklog: worklog/WL-1791926449-joahan-1-HACK-012-hack.lhpbMP.md
Priority: P0
Paths: stuffplus/models/pitching.py, stuffplus/models/multitarget.py, analysis/pitching_model/, reports/pitching_model/, tests/test_model_pitching.py
Depends: HACK-010, HACK-011
Verify: `python -m pytest -q tests/test_model_pitching.py`
Lease-Until: 1791942685
Updated: 1791928285
Task-Base: b4d24886d03beb9197bb2c818b06a61eb04d755e
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-012?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-012?expand=1
Evidence: pytest tests/test_model_pitching.py exit 0 (6 passed); full suite passed; smoke exit 0. Real data OOF by pitcher: combined Pitching+ skill vs count baseline +3.88% [3.78,4.00] on rv_x, +2.17% on rv; R2 0.078 vs 0.002; 8 targets calibrated (ECE .003-.017; called strike AUC .974 vs .685); first 200 pitches -> rest of season r .333 vs .110; next season .283 vs .202; split-half .742. Bundle pitching_xrv distilled R2 .942. All files in Paths; branch from main.
Events: 3
Checkpoints: 0
Sessions: 2
Last-Checkpoint: 0
Task-Tip: 0d7dd05ec4ca9f83bc867e62a5ee31fb7cb36fd6
