# HACK-079
ID: HACK-079
State: CLAIMED
Owner: victor-1
Branch: feat/hack-079
Worktree: /Users/victor/Documents/Proyectos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-079
Worklog: worklog/WL-1792375210-victor-1-HACK-079-hack.v7onUq.md
Priority: P1
Paths: stuffplus/export_trees.py, web/public/data/models/pitching.json, web/src/model/predict.ts, web/src/model/predict.test.ts, web/src/features/simulador/panel/
Depends: HACK-045
Verify: `python -m pytest -q tests/test_export_trees.py && npm --prefix web test -- --run src/model src/features/simulador`
Lease-Until: 1792377910
Updated: 1792375210
Task-Base: 9ccaf7a4bdeb8f877bf6e90839394b3953512ef4
Next: mirror `export_composite` for the Pitching+ components + weights.
PR: -
Evidence: -
Events: 1
Checkpoints: 0
Sessions: 1
Last-Checkpoint: 0
