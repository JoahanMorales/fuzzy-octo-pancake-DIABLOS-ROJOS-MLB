# STATE

Phase: execution
Updated: 1791871352
AVAILABLE: (29; last 12) ... HACK-032 HACK-033 HACK-034 HACK-035 HACK-022 HACK-023 HACK-036 HACK-024 HACK-025 HACK-026 HACK-027 HACK-028 
CLAIMED: HACK-003 HACK-004 HACK-005 
BLOCKED: -
REVIEW: HACK-001 HACK-002 HACK-013 HACK-030 
INTEGRATED: -
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-001 | REVIEW | joahan-1 | until 1791883529
HACK-002 | REVIEW | joahan-1 | until 1791883965
HACK-003 | CLAIMED | victor-1 | until 1791873191
HACK-004 | CLAIMED | victor-2 | until 1791874052
HACK-005 | CLAIMED | joahan-1 | until 1791873716
HACK-013 | REVIEW | joahan-1 | until 1791884853
HACK-030 | REVIEW | joahan-1 | until 1791884412

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791869129 | HACK-001 | smoke-project via init-smoke resolves the shared venv python | Why: python3 is the Store stub on Windows
- 1791869565 | HACK-002 | drop rows w/o pitcher id (2,956) | Why: cannot attribute or group them
- 1791870012 | HACK-030 | RE by outs x count with observed future runs (no base state in data) | Why: RE24 impossible without runners
- 1791870453 | HACK-013 | EB k from within/between variance | Why: small samples (relievers) must not look elite

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
