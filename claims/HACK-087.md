# HACK-087
ID: HACK-087
State: REVIEW
Owner: joahan-7
Branch: feat/hack-087
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-087
Worklog: worklog/WL-1792547297-joahan-7-HACK-087-hack.EsU6z7.md
Priority: P0
Paths: stuffplus/export_web.py, web/public/data/real/validation.json, tests/test_export_highlights.py, tests/test_export_web.py
Depends: HACK-050
Verify: `python -m pytest -q --tb=short -x tests/test_export_highlights.py tests/test_export_web.py && npm --prefix web run build && npm --prefix web test -- --run`
Lease-Until: 1792562389
Updated: 1792547989
Task-Base: 1f99f873f59d362982b34a4b6a89bfa33684e917
Next: Recover lease with token; then apply option: update 5 literal asserts that pin the old familia source/value (tests/test_export_web.py:24-25, story.test.ts:21, landing.test.tsx:39,70) to the production value -13.0; regenerate mock/validation.json (test_write_mock requires it)
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-087?expand=1
Evidence: -
