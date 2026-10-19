# HACK-079
ID: HACK-079
State: REVIEW
Owner: victor-1
Branch: feat/hack-079
Worktree: /Users/victor/Documents/Proyectos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-079
Worklog: worklog/WL-1792375210-victor-1-HACK-079-hack.v7onUq.md
Priority: P1
Paths: stuffplus/export_trees.py, web/public/data/models/pitching.json, web/src/model/predict.ts, web/src/model/predict.test.ts, web/src/features/simulador/panel/
Depends: HACK-045
Verify: `python -m pytest -q tests/test_export_trees.py && npm --prefix web test -- --run src/model src/features/simulador`
Lease-Until: 1792390768
Updated: 1792376368
Task-Base: 9ccaf7a4bdeb8f877bf6e90839394b3953512ef4
Next: Apply option: pitching.json con 120/200/60 rondas (prod 300/200/200 pesa 13.7 MB) ~5.2 MB; fidelidad r vs leaderboard en el JSON; contexto que el panel no da = mediana por familia; fixtures pitching_synthetic*.json y tests en test_export_trees.py fuera de Paths
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/79
Evidence: pytest tests/test_export_trees.py 10 passed; vitest 176 passed (src/model + src/features/simulador 31); build WEB_DIST_OK 22.7 MB; RAW_DATA_CHECK_PASS; pitching.json 3.13 MB r 0.976 vs leaderboard; Playwright /simulador Pitching+ 115.0/108.7 sin errores
Events: 4
Checkpoints: 0
Sessions: 1
Last-Checkpoint: 0
Task-Tip: 886d1142d40434c33d2106044c9ad65d40389e7f
