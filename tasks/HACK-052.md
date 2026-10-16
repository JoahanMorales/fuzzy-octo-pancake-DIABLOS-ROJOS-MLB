# HACK-052
ID: HACK-052
State: REVIEW
Owner: joahan-1
Branch: feat/hack-052
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-052
Worklog: worklog/WL-1792182002-joahan-1-HACK-052-hack.iq52fD.md
Priority: P0
Paths: stuffplus/models/stuff_v2.py, analysis/stuff_v2/, reports/stuff_v2/, tests/test_stuff_v2.py
Depends: None
Verify: `python -m pytest -q tests/test_stuff_v2.py`
Lease-Until: 1792199823
Updated: 1792185423
Task-Base: 2a2792a3b0a9998e462d0b0539e0eb3ea23d561c
Next: HACK-057 wires StuffV2Model into production and adds data/roster.csv to .gitignore
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-052?expand=1
Evidence: a83d9d8: pytest tests/test_stuff_v2.py 7 passed; full run: v2 +0.178/+0.203/+0.230 % over count null (CI>0, count-only = null), first-200 r 0.306->0.323, calib slope 0.69->0.80; R3 fails (league dCDMX -10.3->-12.7); R4 (pre-written) passes: Extreme bias v1 +0.0025 -> v2 +0.0018. Adoption decision for HACK-057 (human).
Events: 4
Checkpoints: 2
Sessions: 1
Last-Checkpoint: 1792185423
Task-Tip: a83d9d867073a1926b20e63cb13d5a13456a30a8
