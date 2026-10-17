# worklog/WL-1792188686-joahan-1-HACK-053-hack.E5VXY7.md · HACK-053

## Live summary
- Done: eaaa1b0: pytest tests/test_calibration.py 6 passed; real nested run (5 outer, 3 inner pitcher folds): Stuff+ v1 none (isotonic slope 0.69->0.88 but split-half 0.807->0.781), Location+ temperature (logloss 1.0419->1.0417, skill +2.783->+2.791%); Stuff+ v2 runs with --models stuff_v2 after HACK-052
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_calibration.py`
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-053?expand=1; run .uak/bin/smoke

## History
- 1792188686 | CLAIMED | joahan-1 | claim; next: fit temperature on OOF logits from `analysis/stuff_model/run.py`.
- 1792189765 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-053?expand=1; evidence: eaaa1b0: pytest tests/test_calibration.py 6 passed; real nested run (5 outer, 3 inner pitcher folds): Stuff+ v1 none (isotonic slope 0.69->0.88 but split-half 0.807->0.781), Location+ temperature (logloss 1.0419->1.0417, skill +2.783->+2.791%); Stuff+ v2 runs with --models stuff_v2 after HACK-052; reviewer: -
- 1792199979 | REVIEW | luis-2 | review; reject; SHA eaaa1b03727e1fdbd3acea1638c2aea3d5c07377; reviewer luis-2
- 1792202499 | REVIEW | joahan-1 | handover; joahan-1 → sebastian-1 by joahan-1
- 1792207854 | REVIEW | joahan | handover; sebastian-1 → joahan-3 by joahan
