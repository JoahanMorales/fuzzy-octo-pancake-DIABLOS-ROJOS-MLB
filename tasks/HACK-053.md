# HACK-053
ID: HACK-053
State: INTEGRATED
Owner: joahan-3
Branch: feat/hack-053
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-053
Worklog: worklog/WL-1792188686-joahan-1-HACK-053-hack.E5VXY7.md
Priority: P0
Paths: stuffplus/calibration.py, analysis/calibration/, reports/calibration/, tests/test_calibration.py
Depends: None
Verify: `python -m pytest -q tests/test_calibration.py`
Lease-Until: 0
Updated: 1792267092
Task-Base: a0232b0d58994189a12ead5ca44d132290fe62b7
Next: Integrated in main: 2c31f417dc5ba2a54788629a58085214c2bc47bd; claim next P0
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-053?expand=1
Evidence: db0f5f6: tests/test_calibration.py 7 passed; smoke PRODUCT_PASS; methods.csv now has Pitching+ components and Stuff+ v2 (log-loss, ECE, xRV slope, skill, first-N r, split-half); decision: Stuff+ v1 none, Location+ temperature, Pitching+ none, Stuff+ v2 temperature
Events: 9
Checkpoints: 0
Sessions: 6
Last-Checkpoint: 0
Task-Tip: db0f5f67bfec63825f5956a7e1b5cb9f3e31312e
Integration-Proof: ancestry
Merge-Commit: 2c31f417dc5ba2a54788629a58085214c2bc47bd
Reviewer: luis-2
