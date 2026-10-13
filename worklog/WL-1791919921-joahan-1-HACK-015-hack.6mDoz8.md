# worklog/WL-1791919921-joahan-1-HACK-015-hack.6mDoz8.md · HACK-015

## Live summary
- Done: reject fixed; tests/test_altitude.py 6 passed; full suite passed; smoke exit 0; regenerated real-data reports; README numbers copied from CSVs
- Decision: retrain Stuff+ with pitch_family; physics translation from ShapeModel
- Why: AutoPitchType relabels with altitude
- Failing: none
- Commands: pytest tests/test_altitude.py; python analysis/altitude_delta/run.py
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-015?expand=1; run .uak/bin/smoke

## History
- 1791919921 | CLAIMED | joahan-1 | claim; next: `altitude.counterfactual_scores(df, bundle, rho_a, rho_b)`.
- 1791920712 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-015?expand=1; evidence: pytest tests/test_altitude.py exit 0 (6 passed); full suite passed; smoke exit 0. Real data: league ΔStuff+ -10.3 at rho 0.819; sweeper -4.6 [-5.4,-3.9] best, riding 4S -16.0 [-16.3,-15.6] worst; triangulation same sign 7/7 families (within-pitcher Extreme vs No, model and results). Uses pitch_family (invariant), per-family proportional physics. Branch from main, single merge base; all files in Paths.; reviewer: -
- 1791920738 | REVIEW | joahan-1 | checkpoint; next: Wait for review of SHA 922fc44
- 1791921944 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-015?expand=1; evidence: pytest tests/test_altitude.py 6 passed; smoke exit 0; README claims checked against CSVs (contact +0.032..+0.065, triangulation ranges, transductive caveat, unassigned excluded). Real data: league -10.3, sweeper -4.6 best, riding 4S -16.0 worst, 7/7 same-sign triangulation.; reviewer: -
- 1791925209 | REVIEW | victor-1 | review; approve; SHA a6c09e1f0ebbb4bfca10a7fad50cc0098f8a80eb; reviewer victor-1
- 1791925375 | REVIEW | victor-1 | review; reject; SHA a6c09e1f0ebbb4bfca10a7fad50cc0098f8a80eb; reviewer victor-1
- 1791925863 | REVIEW | joahan-1 | heartbeat; lease until 1791940263
- 1791927348 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-015?expand=1; evidence: reject fixed; tests/test_altitude.py 6 passed; full suite passed; smoke exit 0; regenerated real-data reports; README numbers copied from CSVs; reviewer: -
- 1791930005 | REVIEW | victor-1 | review; approve; SHA 5780f531fdd0b2cefec77c0eae94f4dd5c4c3c35; reviewer victor-1
- 1791931715 | REVIEW | joahan-1 | heartbeat; lease until 1791946115
