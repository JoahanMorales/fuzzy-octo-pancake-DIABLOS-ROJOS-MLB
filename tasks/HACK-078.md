# HACK-078
ID: HACK-078
State: REVIEW
Owner: joahan-1
Branch: feat/hack-078
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-078
Worklog: worklog/WL-1792378780-joahan-1-HACK-078-hack.Z7UU6b.md
Priority: P1
Paths: stuffplus/value.py, analysis/business_value/, reports/business_value/, tests/test_value.py
Depends: None
Verify: `python -m pytest -q tests/test_value.py`
Lease-Until: 1792395604
Updated: 1792381204
Task-Base: c2ca3385bac249bfdf1e3b72e5901a7c8b0e7fd6
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-078?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-078?expand=1
Evidence: 08c73b33: python analysis/business_value/run.py (5 production v2 fits OOF, 21 min) exit 0; pytest tests/test_value.py pass; stuff_scale_calibration model_version stuff_v2, cross-check 8.69e-4 vs direct 8.68e-4; runs_per_win.csv and pythagorean.csv unchanged; per point 7.24e-4 -> 8.68e-4, +10 Stuff+ HH wins 1.26 -> 1.51, 1 SD 0.69 -> 0.77 wins
Events: 3
Checkpoints: 0
Sessions: 2
Last-Checkpoint: 0
Task-Tip: 08c73b33dfaac8685be874122b39c75a48dfcfe9
