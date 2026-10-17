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
- 1792207527 | REVIEW | joahan-2 | review; approve; SHA 3e7b85eeee4aa64bf973ee7606866fac9cdfa697; reviewer joahan-2
- 1792210842 | REVIEW | joahan-2 | review; approve; SHA 54d5e2b61eb96a8e1e5c1177e6e053ac34f2aa26; reviewer joahan-2
