# worklog/WL-1791870102-joahan-1-HACK-013-hack.P5JEPl.md · HACK-013

## Live summary
- Done: PlusScaler + aggregate + shrinkage_k
- Decision: EB k from within/between variance
- Why: small samples (relievers) must not look elite
- Failing: row-wise key join took 26s: vectorized
- Commands: pytest tests/test_scale.py
- Next: Wait for review of SHA 4673974

## History
- 1791870102 | CLAIMED | joahan-1 | claim; next: `PlusScaler.fit` storing per-group mean/sd.
- 1791870436 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-013?expand=1; evidence: pytest tests/test_scale.py exit 0 (8 passed: mean100/sd10 per season, 120=p97.7, env flavour on neutral ruler, JSON round trip, EB shrinkage); smoke PRODUCT_PASS; 630k rows fit+transform 0.26s; stacked on hack-030; reviewer: -
- 1791870453 | REVIEW | joahan-1 | checkpoint; next: Wait for review of SHA 4673974
