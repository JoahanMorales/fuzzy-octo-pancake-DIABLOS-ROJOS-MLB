# HACK-087
ID: HACK-087
State: REVIEW
Owner: joahan-7
Branch: feat/hack-087
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-087
Worklog: worklog/WL-1792547297-joahan-7-HACK-087-hack.EsU6z7.md
Priority: P0
Paths: stuffplus/export_web.py, web/public/data/real/validation.json, tests/test_export_highlights.py, tests/test_export_web.py
Depends: HACK-050
Verify: `python -m pytest -q --tb=short -x tests/test_export_highlights.py tests/test_export_web.py && npm --prefix web run build && npm --prefix web test -- --run`
Lease-Until: 1792562389
Updated: 1792547989
Task-Base: 1f99f873f59d362982b34a4b6a89bfa33684e917
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-087?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-087?expand=1
Evidence: SHA 7ebaa2f3 · pytest tests/test_export_highlights.py tests/test_export_web.py: 10 passed · npm --prefix web run build OK · npm --prefix web test -- --run: 176 passed · browser (vite preview, data/real): landing league-delta −13.0, presentación −13.0 + riding 4S −17.9
Events: 3
Checkpoints: 0
Sessions: 1
Last-Checkpoint: 0
Task-Tip: 7ebaa2f3c1c5bbab7ee740160982f552305db8d7
