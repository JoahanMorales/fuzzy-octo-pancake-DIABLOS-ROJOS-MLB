# worklog/WL-1791872434-victor-3-HACK-029-hack.asfPWe.md · HACK-029

## Live summary
- Done: 95a9d95: SpinRate fuera de identidad; label shift pitch_family max 0.49pp (null 0.40), APT 3.33; riding4S -0.15; tests 12 passed
- Decision: rule-based shapes on sea-level-translated movement
- Why: interpretable thresholds from real quantiles
- Failing: usage shift 0.70pp > 0.5pp target
- Commands: python -m pytest -q tests/test_shapes.py
- Next: Humano: Smoke red or product unverified

## History
- 1791872434 | CLAIMED | victor-3 | claim; next: reproduce the label shift table, then fit the per pitcher-season mixture.
- 1791873352 | REVIEW | victor-3 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/4; evidence: pytest tests/test_shapes.py exit 0; smoke PASS; 99.3% pitches assigned a shape; family usage shift max 0.70pp vs 3.33pp AutoPitchType (target 0.5 not met); carries HACK-004 physics (PR #3); reviewer: -
- 1791873359 | REVIEW | victor-3 | checkpoint; next: Wait for review of SHA ec1c280
- 1791873838 | REVIEW | joahan-1 | review; reject; SHA ec1c28064799e019969e291309e86602f158310d; reviewer joahan-1
- 1791874779 | REVIEW | victor-1 | review; reject; SHA ec1c28064799e019969e291309e86602f158310d; reviewer victor-1
- 1791903057 | REVIEW | victor-3 | heartbeat; lease until 1791917457
- 1791903064 | REVIEW | victor-3 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/4; evidence: c418ed9: shapes sobre translate proporcional de HACK-004; shape_shift riding 4S -0.22 / 4S +0.05 (antes -2.16/+1.99); label shift max 0.70 pp (criterio 0.5 NO cumplido, reportado); test_shapes 4 passed; reviewer: -
- 1791903995 | REVIEW | victor-3 | heartbeat; lease until 1791918395
- 1791904002 | REVIEW | victor-3 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/4; evidence: 8a85416: merge de main (HACK-004 ya integrada); test_shapes+test_physics 12 passed; label shift 0.70pp documentado; reviewer: -
- 1791905140 | REVIEW | victor-1 | review; reject; SHA 8a85416b72448ad465620eb2a95e432039134c94; reviewer victor-1
- 1791905674 | REVIEW | victor-3 | heartbeat; lease until 1791920074
- 1791905681 | REVIEW | victor-3 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/4; evidence: 95a9d95: SpinRate fuera de identidad; label shift pitch_family max 0.49pp (null 0.40), APT 3.33; riding4S -0.15; tests 12 passed; reviewer: -
- 1791905791 | REVIEW | victor-1 | review; approve; SHA 95a9d95e0a4031f314b7c413c2317f15ca2987ad; reviewer victor-1
- 1791905839 | REVIEW | victor-3 | heartbeat; lease until 1791920239
- 1791905857 | REVIEW | victor-3 | merge rechazado; Smoke red or product unverified
