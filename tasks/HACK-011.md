# HACK-011
ID: HACK-011
State: REVIEW
Owner: joahan-1
Branch: feat/hack-011
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-011
Worklog: worklog/WL-1791903779-joahan-1-HACK-011-hack.gGGfVs.md
Priority: P0
Paths: stuffplus/models/location.py, analysis/location_model/, reports/location_model/, tests/test_model_location.py
Depends: HACK-031
Verify: `python -m pytest -q tests/test_model_location.py`
Lease-Until: 1791918894
Updated: 1791904494
Task-Base: d3c88b00ebb306065689b723ab37348ea7b7ac8c
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-011?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-011?expand=1
Evidence: pytest tests/test_model_location.py exit 0 (7 passed); full suite passed; smoke exit 0. Real data (analysis/location_model/run.py): per-pitch skill vs count baseline +2.9% [2.82,2.98]; 5-outcome logloss 1.028 vs count 1.451; Location+ split-half 0.57 vs observed 0.25; altitude by zone in altitude_by_zone.csv; heatmaps (blue=good). Stacked on HACK-010 (merge 010 first) + main merged.
Events: 3
Checkpoints: 0
Sessions: 2
Last-Checkpoint: 0
Task-Tip: 6a4741e7ba9bda1e2c5cc8cbbd2fb9f1d70d0699
