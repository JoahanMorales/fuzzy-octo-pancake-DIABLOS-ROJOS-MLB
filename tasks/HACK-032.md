# HACK-032
ID: HACK-032
State: REVIEW
Owner: joahan-1
Branch: feat/hack-032
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-032
Worklog: worklog/WL-1791986988-joahan-1-HACK-032-hack.016gka.md
Priority: P0
Paths: stuffplus/staff.py, analysis/staff_audit/, reports/staff_audit/, app/pages/8_Staff_Diablos.py, tests/test_staff.py
Depends: HACK-003, HACK-016
Verify: `python -m pytest -q tests/test_staff.py`
Lease-Until: 1792003018
Updated: 1791988618
Task-Base: 7dc8f4dc72b7e862e24f9bcf668095595c735345
Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-032?expand=1; run .uak/bin/smoke
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-032?expand=1
Evidence: b2336a0: pytest tests/test_staff.py 11 passed; smoke PASS; real run reports/staff_audit (franq 5: 4.4 carreras/temp, franq 11: 3.2; neutral casa-visita +0.92/+0.22; corr modelo vs HACK-018 observado 0.65/0.52); page 8 renders both franchises
Events: 3
Checkpoints: 0
Sessions: 2
Last-Checkpoint: 0
Task-Tip: b2336a087cb01cc6eb0fcbe959f6b8d0c0cbf5f1
