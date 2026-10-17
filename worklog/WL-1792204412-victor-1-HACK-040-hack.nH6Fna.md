# worklog/WL-1792204412-victor-1-HACK-040-hack.nH6Fna.md · HACK-040

## Live summary
- Done: export_trees.py + predict.ts + parity goldens
- Decision: packed tree layout; Pitching+ not exported
- Why: nested=41MB vs 13.4MB; Pitching+ is combine(run_oof), not outcome+contact
- Failing: none
- Commands: python -m stuffplus.export_trees; python -m stuffplus.export_trees --golden
- Next: Wait for review of SHA 3e7b85e; luis-1 schema update

## History
- 1792204412 | CLAIMED | victor-1 | claim; next: `booster.dump_model()` on `deploy/bundle/models/stuff_xrv.txt`.
- 1792205709 | REVIEW | victor-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/51; evidence: pytest tests/test_export_trees.py + vitest src/model exit 0 (TS=LightGBM <1e-6 synthetic+real); 13.41 MB <= 15; smoke PRODUCT_PASS; reviewer: -
- 1792205714 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA 3e7b85e; luis-1 schema update
