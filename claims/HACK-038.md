# HACK-038
ID: HACK-038
State: CLAIMED
Owner: luis-1
Branch: feat/hack-038
Worktree: /Users/FerV/Documents/HackDiablos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-038
Worklog: worklog/WL-1792202861-luis-1-HACK-038-hack.j7hzcf.md
Priority: P0
Paths: docs/CONTRACT-WEB.md, web/src/contract/, web/public/data/mock/, stuffplus/export_web.py, tests/test_export_web.py
Depends: HACK-037
Verify: `python -m pytest -q tests/test_export_web.py && npm --prefix web test -- --run src/contract`
Lease-Until: 1792205580
Updated: 1792202880
Task-Base: 455e796b50a15fc590d0487647db8692739b9379
Next: write types.ts from the bundle tables in deploy/bundle/tables/ and reports/
PR: -
Evidence: -
