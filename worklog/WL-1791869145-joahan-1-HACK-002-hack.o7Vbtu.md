# worklog/WL-1791869145-joahan-1-HACK-002-hack.o7Vbtu.md · HACK-002

## Live summary
- Done: schema/splits/api/contract doc
- Decision: drop rows w/o pitcher id (2,956)
- Why: cannot attribute or group them
- Failing: none
- Commands: pytest tests/test_contract.py; smoke
- Next: Wait for review of SHA 5a28d1a

## History
- 1791869145 | CLAIMED | joahan-1 | claim; next: `stuffplus/api.py` dataclass + mock; publish with `uak msg related:HACK-002 --kind contract` as soon as it is pushed.
- 1791869546 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-002?expand=1; evidence: python -m pytest -q tests/test_contract.py exit 0 (15 passed); smoke PRODUCT_PASS; real data: clean 635,002->627,602 in ~3s, 98% of PAs start 0-0, 5 pitcher folds of ~125.5k; stacked on feat/hack-001 (review HACK-001 first, then only 5 files remain); reviewer: -
- 1791869565 | REVIEW | joahan-1 | checkpoint; next: Wait for review of SHA 5a28d1a
- 1791870960 | REVIEW | victor-2 | review; approve; SHA e476b033b606e187da2609ef15125c441fb285a4; reviewer victor-2
