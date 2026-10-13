# HACK-010
ID: HACK-010
State: REVIEW
Owner: joahan-1
Branch: feat/hack-010
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-010
Worklog: worklog/WL-1791902133-joahan-1-HACK-010-hack.ISHunm.md
Priority: P0
Paths: stuffplus/models/stuff.py, analysis/stuff_model/, reports/stuff_model/, tests/test_model_stuff.py
Depends: HACK-031
Verify: `python -m pytest -q tests/test_model_stuff.py`
Lease-Until: 1791917398
Updated: 1791902998
Task-Base: d3c88b00ebb306065689b723ab37348ea7b7ac8c
Next: Wait for review of SHA 58d27aa
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-010?expand=1
Evidence: pytest tests/test_model_stuff.py exit 0 (8 passed); full suite passed; smoke exit 0 PRODUCT_PASS. Real data (analysis/stuff_model/run.py, 173s, bundle v1): first 50 pitches -> rest of season r=0.230 vs own results 0.051 (4.5x); split-half 0.80 vs 0.18; per-pitch skill +0.07% vs pitch-type baseline, -0.03% vs count baseline (pure stuff excludes count, documented); distill R2 0.92; altitude by type: CH -14.9 .. FC -5.0. Scope note: stuffplus/serving.py (HACK-031, mine, integrated) builds arm_angle + fastball diffs from PitchInput.arsenal. Branch from main, single merge base.
Events: 3
Checkpoints: 1
Sessions: 1
Last-Checkpoint: 1791902998
Task-Tip: 58d27aa89b96f608ff2a5bda9141af9ce70faec0
