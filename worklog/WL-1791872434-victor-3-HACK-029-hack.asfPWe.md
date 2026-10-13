# worklog/WL-1791872434-victor-3-HACK-029-hack.asfPWe.md · HACK-029

## Live summary
- Done: identity, shapes, reports
- Decision: rule-based shapes on sea-level-translated movement
- Why: interpretable thresholds from real quantiles
- Failing: usage shift 0.70pp > 0.5pp target
- Commands: python -m pytest -q tests/test_shapes.py
- Next: Wait for review of SHA ec1c280

## History
- 1791872434 | CLAIMED | victor-3 | claim; next: reproduce the label shift table, then fit the per pitcher-season mixture.
- 1791873352 | REVIEW | victor-3 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/4; evidence: pytest tests/test_shapes.py exit 0; smoke PASS; 99.3% pitches assigned a shape; family usage shift max 0.70pp vs 3.33pp AutoPitchType (target 0.5 not met); carries HACK-004 physics (PR #3); reviewer: -
- 1791873359 | REVIEW | victor-3 | checkpoint; next: Wait for review of SHA ec1c280
- 1791873838 | REVIEW | joahan-1 | review; reject; SHA ec1c28064799e019969e291309e86602f158310d; reviewer joahan-1
