# HACK-075
ID: HACK-075
State: REVIEW
Owner: joahan-5
Branch: feat/hack-075
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-075
Worklog: worklog/WL-1792307292-joahan-5-HACK-075-hack.UIBvPS.md
Priority: P1
Paths: stuffplus/models/stuff.py, stuffplus/models/location.py, stuffplus/models/pitching.py, stuffplus/validation/, reports/validation/, reports/stuff_model/, reports/location_model/, reports/pitching_model/, reports/altitude_delta/, reports/leaderboards/, reports/staff_audit/, reports/business_value/, deploy/bundle/
Depends: HACK-057
Verify: `python -m pytest -q tests/test_validation.py tests/test_model_stuff.py`
Lease-Until: 1792322346
Updated: 1792307946
Task-Base: 3f5831007718de49e0753e04b4288b3ddc454e7d
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-075?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-075?expand=1
Evidence: b87f871: python -m analysis.export_web.run -> WEB_REAL_OK files=571 real=2.1 MB; real/shapes.json now v2 (sweeper -9.60, was -4.64); pytest tests/test_export_web.py pass; web suite 146 passed. Data-only change from committed reports.
Events: 3
Checkpoints: 0
Sessions: 2
Last-Checkpoint: 0
Task-Tip: b87f871ad9203216b8a5d89c1215ea3da8ca1b13
