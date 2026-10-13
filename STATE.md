# STATE

Phase: execution
Updated: 1791873317
AVAILABLE: (27; last 12) ... HACK-032 HACK-033 HACK-034 HACK-035 HACK-022 HACK-023 HACK-036 HACK-024 HACK-025 HACK-026 HACK-027 HACK-028 
CLAIMED: HACK-003 HACK-029 
BLOCKED: -
REVIEW: HACK-004 HACK-005 HACK-013 HACK-030 HACK-031 
INTEGRATED: HACK-001 HACK-002 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-003 | CLAIMED | victor-1 | until 1791873191
HACK-004 | REVIEW | victor-2 | until 1791887717
HACK-005 | REVIEW | joahan-1 | until 1791885806
HACK-013 | REVIEW | joahan-1 | until 1791884853
HACK-029 | CLAIMED | victor-3 | until 1791875134
HACK-030 | REVIEW | joahan-1 | until 1791886097
HACK-031 | REVIEW | joahan-1 | until 1791887455

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791869565 | HACK-002 | drop rows w/o pitcher id (2,956) | Why: cannot attribute or group them
- 1791870012 | HACK-030 | RE by outs x count with observed future runs (no base state in data) | Why: RE24 impossible without runners
- 1791870453 | HACK-013 | EB k from within/between variance | Why: small samples (relievers) must not look elite
- 1791871406 | HACK-005 | skill = % RMSE/logloss reduction, pitcher-cluster bootstrap | Why: pitches of one pitcher are not independent
- 1791873055 | HACK-031 | ship as plumbing; move Stuff+ target to rv_x | Why: rv noise: best iters 25-66, skill +0.02%

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
