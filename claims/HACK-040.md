# HACK-040
ID: HACK-040
State: REVIEW
Owner: victor-1
Branch: feat/hack-040
Worktree: /Users/victor/Documents/Proyectos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-040
Worklog: worklog/WL-1792204412-victor-1-HACK-040-hack.nH6Fna.md
Priority: P0
Paths: web/src/model/, stuffplus/export_trees.py, tests/test_export_trees.py, web/public/data/models/
Depends: HACK-037
Verify: `python -m pytest -q tests/test_export_trees.py && npm --prefix web test -- --run src/model`
Lease-Until: 1792220114
Updated: 1792205714
Task-Base: 455e796b50a15fc590d0487647db8692739b9379
Next: Wait for review of SHA 3e7b85e; luis-1 schema update
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/51
Evidence: -
