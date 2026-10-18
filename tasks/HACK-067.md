# HACK-067
ID: HACK-067
State: REVIEW
Owner: victor-1
Branch: feat/hack-067
Worktree: /Users/victor/Documents/Proyectos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-067
Worklog: worklog/WL-1792286193-victor-1-HACK-067-hack.Z1S310.md
Priority: P1
Paths: web/src/routes.tsx, web/src/features/cuerpo-tecnico/
Depends: None
Verify: `npm --prefix web test -- --run src/features/cuerpo-tecnico src/shell`
Lease-Until: 1792301147
Updated: 1792286747
Task-Base: 34e2b1fa04961b6bd4fc30f6ccdccf2620c4bd80
Next: Wait for review of SHA d600ecaf
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/64
Evidence: vitest cuerpo-tecnico+shell 11 passed; tsc+build OK; smoke PRODUCT_PASS; design-critic SHIP
Events: 3
Checkpoints: 1
Sessions: 1
Last-Checkpoint: 1792286747
Task-Tip: d600ecafe8087dc89d32f66d1a0148434a336e1d
