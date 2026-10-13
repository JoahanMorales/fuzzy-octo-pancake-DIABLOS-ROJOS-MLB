# worklog/WL-1791869602-joahan-1-HACK-030-hack.0uierc.md · HACK-030

## Live summary
- Done: pytest tests/test_targets.py exit 0 (11 passed); smoke exit 0; real data: rv_x sd 0.198 vs rv 0.267 (-26% noise), in-play corr(LW, xLW)=0.67; batted-ball value Extreme +0.087 vs sea +0.034 runs/BIP; LMB vs MLB table (MLB unverified) from previous reject fix
- Decision: RE by outs x count with observed future runs (no base state in data)
- Why: RE24 impossible without runners
- Failing: 3-out rows in raw data: clipped
- Commands: pytest tests/test_targets.py; python -m stuffplus.targets
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-030?expand=1; run .uak/bin/smoke

## History
- 1791869602 | CLAIMED | joahan-1 | claim; next: compute runs-to-end-of-half-inning with a reverse cumulative sum of `RunsScored` per (game, inning, half).
- 1791869991 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-030?expand=1; evidence: pytest tests/test_targets.py exit 0 (8 passed); smoke PRODUCT_PASS; real data (python -m stuffplus.targets, 8.5s): RE monotone (0-0/0 outs 0.913), LW 1B .551 2B .859 HR 1.465 BB .417 K -.396 Out -.383, corr(rv, rv_delta)=0.70; stacked on hack-002; reviewer: -
- 1791870012 | REVIEW | joahan-1 | checkpoint; next: Wait for review of SHA ae42b37
- 1791870982 | REVIEW | victor-2 | review; reject; SHA ae42b37227e4b4e0d77306c298321fc29ccdc49b; reviewer victor-2
- 1791871697 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-030?expand=1; evidence: pytest tests/test_targets.py exit 0 (9 passed); reject fixed: lmb_vs_mlb.csv (MLB flagged unverified); smoke unchanged; reviewer: -
- 1791873364 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-030?expand=1; evidence: pytest tests/test_targets.py exit 0 (11 passed); smoke exit 0; real data: rv_x sd 0.198 vs rv 0.267 (-26% noise), in-play corr(LW, xLW)=0.67; batted-ball value Extreme +0.087 vs sea +0.034 runs/BIP; LMB vs MLB table (MLB unverified) from previous reject fix; reviewer: -
- 1791874035 | REVIEW | victor-1 | review; approve; SHA 210cd02b08804ad8bdc5572b76b5b5ef1c05ea72; reviewer victor-1
- 1791898995 | REVIEW | joahan-1 | heartbeat; lease until 1791913395
