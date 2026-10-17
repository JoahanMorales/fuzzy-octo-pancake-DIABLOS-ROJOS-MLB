# HACK-048
ID: HACK-048
State: REVIEW
Owner: victor-1
Branch: feat/hack-048
Worktree: /Users/victor/Documents/Proyectos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-048
Worklog: worklog/WL-1792267811-victor-1-HACK-048-hack.MMMl7p.md
Priority: P1
Paths: web/src/features/staff/, web/src/features/prospecto/, web/src/features/laboratorio/
Depends: HACK-037
Verify: `npm --prefix web test -- --run src/features/staff src/features/prospecto src/features/laboratorio`
Lease-Until: 1792283640
Updated: 1792269240
Task-Base: 2c31f417dc5ba2a54788629a58085214c2bc47bd
Next: Wait for review of SHA 840be9d
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/57
Evidence: vitest staff+prospecto+laboratorio 17 passed (profiler = Python golden <1e-6, no network on upload); tsc+build OK; smoke PRODUCT_PASS; design-critic P1s fixed
Events: 3
Checkpoints: 1
Sessions: 1
Last-Checkpoint: 1792269240
Task-Tip: 840be9d3df3776d2b937ebd62d0868f64c665036
