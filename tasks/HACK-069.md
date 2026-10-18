# HACK-069
ID: HACK-069
State: REVIEW
Owner: victor-1
Branch: feat/hack-069
Worktree: /Users/victor/Documents/Proyectos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-069
Worklog: worklog/WL-1792291003-victor-1-HACK-069-hack.SZabAt.md
Priority: P1
Paths: analysis/export_web/, web/public/data/real/, web/src/features/leaderboard/, web/src/features/pitcher/, tests/test_check_web_dist.py
Depends: HACK-064, HACK-065
Verify: `python -m pytest -q tests/test_check_web_dist.py && npm --prefix web test -- --run src/features/leaderboard src/features/pitcher`
Lease-Until: 1792307462
Updated: 1792293062
Task-Base: 02eccdb9fe9e9ef3f6143d477cd8803903994ee4
Next: Wait for review of SHA f7f2e7ee; recompute after HACK-057
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/69
Evidence: pytest test_check_web_dist 10 passed; vitest leaderboard+pitcher 13 passed; check_no_raw_data + check_web_dist OK; smoke PRODUCT_PASS
Events: 3
Checkpoints: 1
Sessions: 1
Last-Checkpoint: 1792293062
Task-Tip: f7f2e7ee1943ff4c33466407a7bdc47934cd334f
