# HACK-076
ID: HACK-076
State: REVIEW
Owner: joahan-2
Branch: feat/hack-076
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-076
Worklog: worklog/WL-1792370790-joahan-2-HACK-076-hack.qBrYeu.md
Priority: P0
Paths: analysis/pitcher_sensitivity/, reports/pitcher_sensitivity/, stuffplus/sensitivity.py, tests/test_sensitivity.py
Depends: None
Verify: `python -m pytest -q tests/test_sensitivity.py`
Lease-Until: 1792386366
Updated: 1792371966
Task-Base: 1680363b2ac0745f73e9d8a6ecede7060f4f78e3
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-076?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-076?expand=1
Evidence: 72fec960: python analysis/pitcher_sensitivity/run.py (full, 16 min) -> metadata model_version stuff_v2, league_delta -12.95 (production -13.0, within 1.5); pytest tests/test_sensitivity.py pass; 1,277 ranked, index 88.1-109.9; no per-pitch rows (pitches.csv = pitch-identity aggregates as before)
Events: 3
Checkpoints: 0
Sessions: 2
Last-Checkpoint: 0
Task-Tip: 72fec960ba4cd9109f210498d2d7311298a816c8
