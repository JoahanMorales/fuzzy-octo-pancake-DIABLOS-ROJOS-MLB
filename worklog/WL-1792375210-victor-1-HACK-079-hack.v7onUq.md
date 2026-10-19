# worklog/WL-1792375210-victor-1-HACK-079-hack.v7onUq.md · HACK-079

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_export_trees.py && npm --prefix web test -- --run src/model src/features/simulador`
- Next: mirror `export_composite` for the Pitching+ components + weights.

## History
- 1792375210 | CLAIMED | victor-1 | claim; next: mirror `export_composite` for the Pitching+ components + weights.
- 1792375688 | CLAIMED | victor-1 | pending decision HACK-079-1792375688; option: pitching.json con 120/200/60 rondas (prod 300/200/200 pesa 13.7 MB) ~5.2 MB; fidelidad r vs leaderboard en el JSON; contexto que el panel no da = mediana por familia; fixtures pitching_synthetic*.json y tests en test_export_trees.py fuera de Paths; Why: build web 18.0 MB y check_web_dist limita a 25 MB; las goldens viven en web/src/model/fixtures como en 066
