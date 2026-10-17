# HACK-038
ID: HACK-038
State: REVIEW
Owner: luis-1
Branch: feat/hack-038
Worktree: /Users/FerV/Documents/HackDiablos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-038
Worklog: worklog/WL-1792202861-luis-1-HACK-038-hack.j7hzcf.md
Priority: P0
Paths: docs/CONTRACT-WEB.md, web/src/contract/, web/public/data/mock/, stuffplus/export_web.py, tests/test_export_web.py
Depends: HACK-037
Verify: `python -m pytest -q tests/test_export_web.py && npm --prefix web test -- --run src/contract`
Lease-Until: 1792218027
Updated: 1792203627
Task-Base: 455e796b50a15fc590d0487647db8692739b9379
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/49; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/49
Evidence: pytest tests/test_export_web.py exit 0; npm --prefix web test -- --run src/contract exit 0; smoke exit 0; 20 parques, stuff_v2 leído de reports/stuff_v2/altitude.csv
Events: 5
Checkpoints: 0
Sessions: 1
Last-Checkpoint: 0
Task-Tip: 92aef6e91044046918482ae606e65e59ea3edfef
