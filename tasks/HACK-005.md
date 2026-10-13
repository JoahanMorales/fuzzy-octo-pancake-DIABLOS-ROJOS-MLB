# HACK-005
ID: HACK-005
State: REVIEW
Owner: joahan-1
Branch: feat/hack-005
Worktree: /c/Users/chump/OneDrive/Escritorio/Progra/proyectos/diablo/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-005
Worklog: worklog/WL-1791871016-joahan-1-HACK-005-hack.hSdC2P.md
Priority: P0
Paths: stuffplus/baseline.py, stuffplus/evaluate.py, reports/baseline/, tests/test_evaluate.py
Depends: None
Verify: `python -m pytest -q tests/test_evaluate.py`
Lease-Until: 1791914032
Updated: 1791899632
Task-Base: 08e6a655642cd7a11385d0e17e814fea34cc111f
Next: Wait for review of SHA ba49eba
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-005?expand=1
Evidence: pytest tests/test_evaluate.py exit 0 (9 passed); smoke PRODUCT_PASS; real data python -m stuffplus.baseline 58s -> reports/baseline/baseline_metrics.csv: rv RMSE 0.2673 (count), park holdout bias +0.012 runs/pitch in Extreme; t_whiff AUC 0.53 count / 0.60 count x family; stacked on hack-013
Events: 5
Checkpoints: 1
Sessions: 2
Last-Checkpoint: 1791871406
Task-Tip: ba49eba9dfc939cbf57d334b4f6e0e668944d968
