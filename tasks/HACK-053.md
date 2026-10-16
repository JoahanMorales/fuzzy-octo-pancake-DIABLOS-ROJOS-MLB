# HACK-053
ID: HACK-053
State: REVIEW
Owner: joahan-1
Branch: feat/hack-053
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-053
Worklog: worklog/WL-1792188686-joahan-1-HACK-053-hack.E5VXY7.md
Priority: P0
Paths: stuffplus/calibration.py, analysis/calibration/, reports/calibration/, tests/test_calibration.py
Depends: None
Verify: `python -m pytest -q tests/test_calibration.py`
Lease-Until: 1792204165
Updated: 1792189765
Task-Base: a0232b0d58994189a12ead5ca44d132290fe62b7
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-053?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-053?expand=1
Evidence: eaaa1b0: pytest tests/test_calibration.py 6 passed; real nested run (5 outer, 3 inner pitcher folds): Stuff+ v1 none (isotonic slope 0.69->0.88 but split-half 0.807->0.781), Location+ temperature (logloss 1.0419->1.0417, skill +2.783->+2.791%); Stuff+ v2 runs with --models stuff_v2 after HACK-052
Events: 2
Checkpoints: 0
Sessions: 1
Last-Checkpoint: 0
Task-Tip: eaaa1b03727e1fdbd3acea1638c2aea3d5c07377
