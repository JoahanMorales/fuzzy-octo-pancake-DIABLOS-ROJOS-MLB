# worklog/WL-1792182002-joahan-1-HACK-052-hack.iq52fD.md · HACK-052

## Live summary
- Done: StuffV2Model (count values outcomes, per-count recentring nests the null, family-weighted marginal Stuff+), 7 tests, runner with pre-registered rule R1-R3; fast run: v2 +0.15% over null CI>0 on 3 splits, count-only = null
- Decision: count enters only via Balls/Strikes; Stuff+ marginalized over the family's train count distribution; league weights = sensitivity
- Why: rubric null is mean xRV by count; honest framing = incremental value of stuff over the count null
- Failing: none open
- Commands: python -m analysis.stuff_v2.run (full, ~40 min, background bj34tak2m); pytest -q tests/test_stuff_v2.py
- Next: read reports/stuff_v2/decision.csv; commit reports; uak done

## History
- 1792182002 | CLAIMED | joahan-1 | claim; next: subclass `StuffModel` with a residual target; reuse `analysis/tuning/evaluate.py` patterns.
- 1792183234 | CLAIMED | joahan-1 | checkpoint; next: read reports/stuff_v2/decision.csv; commit reports; uak done
