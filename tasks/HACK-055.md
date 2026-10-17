# HACK-055
ID: HACK-055
State: REVIEW
Owner: joahan-1
Branch: feat/hack-055
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-055
Worklog: worklog/WL-1792195875-joahan-1-HACK-055-hack.45u8dn.md
Priority: P1
Paths: stuffplus/uncertainty.py, analysis/uncertainty/, reports/uncertainty/, tests/test_uncertainty.py
Depends: None
Verify: `python -m pytest -q tests/test_uncertainty.py`
Lease-Until: 1792211199
Updated: 1792196799
Task-Base: 05ff7a941d9dfba8900623f057a412c34c87bcfd
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-055?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-055?expand=1
Evidence: 3376e35: pytest tests/test_uncertainty.py 5 passed; smoke PASS; real: shift AUC 0.770, ESS 45%; Location+ CV +2.92% / weighted +2.59% / actual Extreme +2.35%; 90% conformal coverage 89-93% (pitcher halves), altitude delta +-7.6 pts coverage 93%
Events: 2
Checkpoints: 0
Sessions: 1
Last-Checkpoint: 0
Task-Tip: 3376e35b970099f3aa1378085a39e3568e19a177
