# worklog/WL-1792182002-joahan-1-HACK-052-hack.iq52fD.md · HACK-052

## Live summary
- Done: full run + R4; in REVIEW
- Decision: human adopted v2; R4 replaces R3 (2026-10-16)
- Why: v2 beats count null, better pitcher-level and calibration; its larger altitude cost is closer to held-out reality
- Failing: none
- Commands: python -m analysis.stuff_v2.run; python -m analysis.stuff_v2.altitude_bias
- Next: Integrated in main: 455e796b50a15fc590d0487647db8692739b9379 (recorded by joahan-1)

## History
- 1792182002 | CLAIMED | joahan-1 | claim; next: subclass `StuffModel` with a residual target; reuse `analysis/tuning/evaluate.py` patterns.
- 1792183234 | CLAIMED | joahan-1 | checkpoint; next: read reports/stuff_v2/decision.csv; commit reports; uak done
- 1792185278 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-052?expand=1; evidence: a83d9d8: pytest tests/test_stuff_v2.py 7 passed; full run: v2 +0.178/+0.203/+0.230 % over count null (CI>0, count-only = null), first-200 r 0.306->0.323, calib slope 0.69->0.80; R3 fails (league dCDMX -10.3->-12.7); R4 (pre-written) passes: Extreme bias v1 +0.0025 -> v2 +0.0018. Adoption decision for HACK-057 (human).; reviewer: -
- 1792185423 | REVIEW | joahan-1 | checkpoint; next: HACK-057 wires StuffV2Model into production and adds data/roster.csv to .gitignore
- 1792199909 | REVIEW | luis-2 | review; approve; SHA a83d9d867073a1926b20e63cb13d5a13456a30a8; reviewer luis-2
- 1792201990 | INTEGRATED | joahan-1 | integrate; recorded by joahan-1; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-052?expand=1; merged 455e796b50a15fc590d0487647db8692739b9379; proof ancestry
