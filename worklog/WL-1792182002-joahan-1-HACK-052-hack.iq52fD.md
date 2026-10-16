# worklog/WL-1792182002-joahan-1-HACK-052-hack.iq52fD.md · HACK-052

## Live summary
- Done: a83d9d8: pytest tests/test_stuff_v2.py 7 passed; full run: v2 +0.178/+0.203/+0.230 % over count null (CI>0, count-only = null), first-200 r 0.306->0.323, calib slope 0.69->0.80; R3 fails (league dCDMX -10.3->-12.7); R4 (pre-written) passes: Extreme bias v1 +0.0025 -> v2 +0.0018. Adoption decision for HACK-057 (human).
- Decision: count enters only via Balls/Strikes; Stuff+ marginalized over the family's train count distribution; league weights = sensitivity
- Why: rubric null is mean xRV by count; honest framing = incremental value of stuff over the count null
- Failing: none open
- Commands: python -m analysis.stuff_v2.run (full, ~40 min, background bj34tak2m); pytest -q tests/test_stuff_v2.py
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-052?expand=1; run .uak/bin/smoke

## History
- 1792182002 | CLAIMED | joahan-1 | claim; next: subclass `StuffModel` with a residual target; reuse `analysis/tuning/evaluate.py` patterns.
- 1792183234 | CLAIMED | joahan-1 | checkpoint; next: read reports/stuff_v2/decision.csv; commit reports; uak done
- 1792185278 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-052?expand=1; evidence: a83d9d8: pytest tests/test_stuff_v2.py 7 passed; full run: v2 +0.178/+0.203/+0.230 % over count null (CI>0, count-only = null), first-200 r 0.306->0.323, calib slope 0.69->0.80; R3 fails (league dCDMX -10.3->-12.7); R4 (pre-written) passes: Extreme bias v1 +0.0025 -> v2 +0.0018. Adoption decision for HACK-057 (human).; reviewer: -
