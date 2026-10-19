# worklog/WL-1792375210-victor-1-HACK-079-hack.v7onUq.md · HACK-079

## Live summary
- Done: pytest tests/test_export_trees.py 10 passed; vitest 176 passed (src/model + src/features/simulador 31); build WEB_DIST_OK 22.7 MB; RAW_DATA_CHECK_PASS; pitching.json 3.13 MB r 0.976 vs leaderboard; Playwright /simulador Pitching+ 115.0/108.7 sin errores
- Decision: pitching.json con 120/200/60 rondas (prod 300/200/200 pesa 13.7 MB) ~5.2 MB; fidelidad r vs leaderboard en el JSON; contexto que el panel no da = mediana por familia; fixtures pitching_synthetic*.json y tests en test_export_trees.py fuera de Paths
- Why: build web 18.0 MB y check_web_dist limita a 25 MB; las goldens viven en web/src/model/fixtures como en 066
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_export_trees.py && npm --prefix web test -- --run src/model src/features/simulador`
- Next: Integrated in main: 49fb471f4e8b9841aa699a6f34bfa33927bbfed6 (recorded by victor-1)

## History
- 1792375210 | CLAIMED | victor-1 | claim; next: mirror `export_composite` for the Pitching+ components + weights.
- 1792375688 | CLAIMED | victor-1 | pending decision HACK-079-1792375688; option: pitching.json con 120/200/60 rondas (prod 300/200/200 pesa 13.7 MB) ~5.2 MB; fidelidad r vs leaderboard en el JSON; contexto que el panel no da = mediana por familia; fixtures pitching_synthetic*.json y tests en test_export_trees.py fuera de Paths; Why: build web 18.0 MB y check_web_dist limita a 25 MB; las goldens viven en web/src/model/fixtures como en 066
- 1792376368 | REVIEW | victor-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/79; evidence: pytest tests/test_export_trees.py 10 passed; vitest 176 passed (src/model + src/features/simulador 31); build WEB_DIST_OK 22.7 MB; RAW_DATA_CHECK_PASS; pitching.json 3.13 MB r 0.976 vs leaderboard; Playwright /simulador Pitching+ 115.0/108.7 sin errores; reviewer: -
- 1792378018 | REVIEW | scheduler | deadline decision HACK-079-1792375688; option: pitching.json con 120/200/60 rondas (prod 300/200/200 pesa 13.7 MB) ~5.2 MB; fidelidad r vs leaderboard en el JSON; contexto que el panel no da = mediana por familia; fixtures pitching_synthetic*.json y tests en test_export_trees.py fuera de Paths; Why: build web 18.0 MB y check_web_dist limita a 25 MB; las goldens viven en web/src/model/fixtures como en 066
- 1792379008 | REVIEW | joahan-4 | review; approve; SHA 886d1142d40434c33d2106044c9ad65d40389e7f; reviewer joahan-4
- 1792381727 | REVIEW | victor-1 | merge rechazado; Edits a file outside Paths: tests/test_export_trees.py (Paths of HACK-040). Revert that file on the branch (git checkout origin/main -- tests/test_export_trees.py), or the human merges the PR
- 1792381773 | INTEGRATED | victor-1 | integrate; recorded by victor-1; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/79; merged 49fb471f4e8b9841aa699a6f34bfa33927bbfed6; proof ancestry
