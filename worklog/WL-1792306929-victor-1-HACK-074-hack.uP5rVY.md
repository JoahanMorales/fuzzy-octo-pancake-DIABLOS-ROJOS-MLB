# worklog/WL-1792306929-victor-1-HACK-074-hack.uP5rVY.md · HACK-074

## Live summary
- Done: bands recalibrated on v2 scores
- Decision: commit only uncertainty files; real/ refresh belongs to HACK-075
- Why: avoid clobbering HACK-075
- Failing: none
- Commands: python -m stuffplus.score; python -m analysis.export_web.uncertainty
- Next: Integrated in main: 1d8c9e23b6573fd4b1478942169cc10f069167c5 (recorded by victor-1)

## History
- 1792306929 | CLAIMED | victor-1 | claim; next: Implement HACK-074 and run: `python -m pytest -q tests/test_check_web_dist.py && npm --prefix web test -- --run src/features/leaderboard src/features/pitcher`
- 1792309696 | REVIEW | victor-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/72; evidence: pytest test_check_web_dist 10 passed; vitest leaderboard+pitcher 13 passed; check_no_raw_data PASS; smoke PRODUCT_PASS; reviewer: -
- 1792309707 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA af35c869
- 1792309822 | REVIEW | victor-2 | review; approve; SHA af35c8693c6cc8e99a78f7450a6cc86a37e74302; reviewer victor-2
- 1792310305 | INTEGRATED | victor-1 | integrate; recorded by victor-1; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/72; merged 1d8c9e23b6573fd4b1478942169cc10f069167c5; proof ancestry
