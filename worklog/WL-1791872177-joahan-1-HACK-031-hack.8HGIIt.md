# worklog/WL-1791872177-joahan-1-HACK-031-hack.8HGIIt.md · HACK-031

## Live summary
- Done: trainer, bundle, serving, v0 run, findings
- Decision: ship as plumbing; move Stuff+ target to rv_x
- Why: rv noise: best iters 25-66, skill +0.02%
- Failing: smoke failed once: api switched to real bundle; fixed with conftest isolation
- Commands: pytest tests/test_serving.py; python analysis/v0/run.py
- Next: Wait for review of SHA badd9b5; then HACK-030 rv_x

## History
- 1791872177 | CLAIMED | joahan-1 | claim; next: `analysis/v0/run.py` → `bundle.save(...)` → `serving.load_bundle()`.
- 1791873018 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-031?expand=1; evidence: pytest tests/test_serving.py exit 0 (8 passed); full suite 60 passed; smoke exit 0 PRODUCT_PASS; real run analysis/v0/run.py -> artifacts/bundle (api.predict_pitch now real, demo_data False). v0 = plumbing only: rv skill +0.02% (CI .003-.031%), best iters 25-66 => rv too noisy; physics signal confirmed (OOF AUC whiff .634 vs .605, GB .615 vs .527); see analysis/v0/README.md. Scope notes: tests/conftest.py autouse isolation (HACK-001 owner = me); dashboard acceptance waits on HACK-007 (app/ not created here). Stacked on 030/013/005.; reviewer: -
- 1791873055 | REVIEW | joahan-1 | checkpoint; next: Wait for review of SHA badd9b5; then HACK-030 rv_x
- 1791873986 | REVIEW | victor-1 | review; approve; SHA badd9b5daac63897a3d36a3cbb3e4ddef1f870a6; reviewer victor-1
