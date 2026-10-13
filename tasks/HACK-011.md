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
Lease-Until: 1791933785
Updated: 1791919385
Task-Base: d3c88b00ebb306065689b723ab37348ea7b7ac8c
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-011?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-011?expand=1
Evidence: reject fixed: pitch_family (identity) replaces AutoPitchType as feature and reference key; full suite 123 passed; smoke exit 0; real data skill +2.78% [2.70,2.87] vs count baseline, split-half 0.58; main merged, single merge base. Includes HACK-010 commits (merge 010 first) + 2-line support in common.py/serving.py for pitch_family.
Events: 5
Checkpoints: 0
Sessions: 2
Last-Checkpoint: 0
Task-Tip: c452e395e49cb6f9516811b3de426155fadf75a9
