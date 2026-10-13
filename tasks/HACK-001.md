# HACK-001
ID: HACK-001
State: REVIEW
Owner: joahan-1
Branch: feat/hack-001
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-001
Worklog: worklog/WL-1791868422-joahan-1-HACK-001-hack.MjD1JF.md
Priority: P0
Paths: requirements.txt, pyproject.toml, stuffplus/__init__.py, stuffplus/io.py, stuffplus/config.py, tests/__init__.py, tests/conftest.py, tests/fixtures/, tests/test_io.py, README.md, Makefile
Depends: None
Verify: `python -m pytest -q tests/test_io.py`
Lease-Until: 1791885870
Updated: 1791871470
Task-Base: 0e16deb8f07b4012d2ca009393a2f3f62c0d68f0
Next: Humano: Diff outside Paths: .uak/bin/.smoke-project.provenance (new test files: add the dir to Additive-Paths in PROJECT.md)
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-001?expand=1
Evidence: python -m pytest -q tests/test_io.py exit 0 (11 passed, incl. real-file schema check); bash .uak/bin/smoke exit 0 PRODUCT_PASS; fixture call mix matches LMB (Ball 36%/InPlay 20%/Foul 17%), Extreme/No drag 0.78-0.88; scope note: added .uak/bin/smoke-project via uak init-smoke (product smoke = setup)
Events: 6
Checkpoints: 1
Sessions: 2
Last-Checkpoint: 1791869129
Task-Tip: 298c823fa004c19e318da26f73b3c016e9e029e0
