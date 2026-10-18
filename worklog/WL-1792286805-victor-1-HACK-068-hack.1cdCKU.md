# worklog/WL-1792286805-victor-1-HACK-068-hack.1cdCKU.md · HACK-068

## Live summary
- Done: reclutamiento page + shortlist export
- Decision: exclude staff ids; default max loss = league median
- Why: acceptance: not on the Diablos, small CDMX loss
- Failing: none
- Commands: npm --prefix web test -- --run src/features/reclutamiento
- Next: Wait for review of SHA 34bedb96

## History
- 1792286805 | CLAIMED | victor-1 | claim; next: filters from web/src/features/leaderboard/logic.ts.
- 1792287289 | REVIEW | victor-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/65; evidence: vitest reclutamiento 5 passed; tsc+build OK; smoke PRODUCT_PASS; design-critic SHIP; reviewer: -
- 1792287295 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA 34bedb96
- 1792291621 | REVIEW | victor-2 | review; approve; SHA 34bedb96822b42042c87d5ee5b808f2f2c57ac02; reviewer victor-2
