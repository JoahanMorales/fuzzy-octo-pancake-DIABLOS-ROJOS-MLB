# worklog/WL-1792291003-victor-1-HACK-069-hack.SZabAt.md · HACK-069

## Live summary
- Done: pytest 10 passed; vitest leaderboard+pitcher 13, suite 141 passed; build OK; smoke PRODUCT_PASS
- Decision: compute width by n in export_web from OOF pitch scores
- Why: reports/uncertainty has only global widths
- Failing: none
- Commands: python -m stuffplus.score; python -m analysis.export_web.uncertainty; python -m analysis.export_web.run
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/69; run .uak/bin/smoke

## History
- 1792291003 | CLAIMED | victor-1 | claim; next: read reports/uncertainty/README.md and its CSVs.
- 1792293056 | REVIEW | victor-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/69; evidence: pytest test_check_web_dist 10 passed; vitest leaderboard+pitcher 13 passed; check_no_raw_data + check_web_dist OK; smoke PRODUCT_PASS; reviewer: -
- 1792293062 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA f7f2e7ee; recompute after HACK-057
- 1792293736 | REVIEW | victor-2 | review; approve; SHA f7f2e7ee1943ff4c33466407a7bdc47934cd334f; reviewer victor-2
- 1792294290 | REVIEW | victor-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/69; evidence: pytest 10 passed; vitest leaderboard+pitcher 13, suite 141 passed; build OK; smoke PRODUCT_PASS; reviewer: -
- 1792294353 | REVIEW | victor-2 | review; approve; SHA 03beec9a58d777e5556f602561538f225e4b53b8; reviewer victor-2
