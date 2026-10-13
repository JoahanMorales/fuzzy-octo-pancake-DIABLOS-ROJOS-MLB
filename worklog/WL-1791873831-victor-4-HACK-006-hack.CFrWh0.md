# worklog/WL-1791873831-victor-4-HACK-006-hack.CFrWh0.md · HACK-006

## Live summary
- Done: arsenal, sequence, tests, report
- Decision: trajectory axes X=toward plate; tunnel_ratio=plate_sep/decision_sep
- Why: verified vs y0/PlateLoc
- Failing: none
- Commands: python -m pytest -q tests/test_features.py
- Next: Wait for review of SHA 744d962

## History
- 1791873831 | CLAIMED | victor-4 | claim; next: `arsenal.primary_fastball(df)` grouped by (pitcher_anon_id, year).
- 1791874039 | REVIEW | victor-4 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/6; evidence: pytest tests/test_features.py exit 0 (5 passed); smoke PASS; trajectory-derived plate pos corr 0.999 with PlateLoc; carries HACK-029/HACK-004 branches; reviewer: -
- 1791874055 | REVIEW | victor-4 | checkpoint; next: Wait for review of SHA 744d962
- 1791874840 | REVIEW | victor-1 | review; approve; SHA 744d96220433b85e685a60274c264c1892cba9ae; reviewer victor-1
