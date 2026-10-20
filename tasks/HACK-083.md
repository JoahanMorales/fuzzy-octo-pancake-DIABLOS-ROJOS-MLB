# HACK-083
ID: HACK-083
State: INTEGRATED
Owner: joahan-5
Branch: feat/hack-083
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-083
Worklog: worklog/WL-1792381499-joahan-5-HACK-083-hack.o997In.md
Priority: P1
Paths: stuffplus/profile.py, analysis/ideal_profile/, reports/ideal_profile/, tests/test_profile.py
Depends: HACK-077
Verify: `python -m pytest -q tests/test_profile.py`
Lease-Until: 0
Updated: 1792454914
Task-Base: c2ca3385bac249bfdf1e3b72e5901a7c8b0e7fd6
Next: Integrated in main: b025068e024a1c550cdae750c09778b239d011a6; claim next P0
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-083?expand=1
Evidence: 5b64bccb: python analysis/ideal_profile/run.py (full, 29 min, fit_production_stuff from HACK-077) exit 0; pytest tests/test_profile.py pass; profile.md regenerated via _md from the CSVs with the new checklist (ride holds 21.1->5.8, extension 4.3 gap robust, VAA 1.7 gap robust, velocity no threshold); no per-pitch rows
Events: 8
Checkpoints: 0
Sessions: 3
Last-Checkpoint: 0
Task-Tip: 367fb8add203a153f1ae1a45b9c236aabbd65e61
Integration-Proof: ancestry
Merge-Commit: b025068e024a1c550cdae750c09778b239d011a6
Reviewer: victor-1
