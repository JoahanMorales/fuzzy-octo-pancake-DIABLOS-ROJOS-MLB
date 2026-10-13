# HACK-031
ID: HACK-031
State: REVIEW
Owner: joahan-1
Branch: feat/hack-031
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-031
Worklog: worklog/WL-1791872177-joahan-1-HACK-031-hack.8HGIIt.md
Priority: P0
Paths: stuffplus/models/__init__.py, stuffplus/models/common.py, stuffplus/bundle.py, stuffplus/serving.py, analysis/v0/, tests/test_serving.py
Depends: HACK-001, HACK-002
Verify: `python -m pytest -q tests/test_serving.py`
Lease-Until: 1791887455
Updated: 1791873055
Task-Base: f0f2298437311fb5f3e3fcc293f8585e339633b3
Next: Wait for review of SHA badd9b5; then HACK-030 rv_x
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-031?expand=1
Evidence: pytest tests/test_serving.py exit 0 (8 passed); full suite 60 passed; smoke exit 0 PRODUCT_PASS; real run analysis/v0/run.py -> artifacts/bundle (api.predict_pitch now real, demo_data False). v0 = plumbing only: rv skill +0.02% (CI .003-.031%), best iters 25-66 => rv too noisy; physics signal confirmed (OOF AUC whiff .634 vs .605, GB .615 vs .527); see analysis/v0/README.md. Scope notes: tests/conftest.py autouse isolation (HACK-001 owner = me); dashboard acceptance waits on HACK-007 (app/ not created here). Stacked on 030/013/005.
Events: 3
Checkpoints: 1
Sessions: 1
Last-Checkpoint: 1791873055
Task-Tip: badd9b5daac63897a3d36a3cbb3e4ddef1f870a6
