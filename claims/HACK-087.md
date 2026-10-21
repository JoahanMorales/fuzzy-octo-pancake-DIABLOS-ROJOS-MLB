# HACK-087
ID: HACK-087
State: CLAIMED
Owner: joahan-7
Branch: feat/hack-087
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-087
Worklog: worklog/WL-1792547297-joahan-7-HACK-087-hack.EsU6z7.md
Priority: P0
Paths: stuffplus/export_web.py, web/public/data/real/validation.json, tests/test_export_highlights.py, tests/test_export_web.py
Depends: HACK-050
Verify: `python -m pytest -q --tb=short -x tests/test_export_highlights.py tests/test_export_web.py && npm --prefix web run build && npm --prefix web test -- --run`
Lease-Until: 1792549997
Updated: 1792547297
Task-Base: 1f99f873f59d362982b34a4b6a89bfa33684e917
Next: change `_validation` in stuffplus/export_web.py (~line 222), re-export real/ to a scratch dir and copy only validation.json.
PR: -
Evidence: -
