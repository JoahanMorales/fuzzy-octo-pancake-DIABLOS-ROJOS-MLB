# STATE

Phase: execution
Updated: 1791903064
AVAILABLE: (24; last 12) ... HACK-032 HACK-033 HACK-034 HACK-035 HACK-022 HACK-023 HACK-036 HACK-024 HACK-025 HACK-026 HACK-027 HACK-028 
CLAIMED: -
BLOCKED: -
REVIEW: HACK-004 HACK-006 HACK-007 HACK-010 HACK-029 
INTEGRATED: HACK-001 HACK-002 HACK-003 HACK-005 HACK-013 HACK-030 HACK-031 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-004 | REVIEW | victor-2 | until 1791917391
HACK-006 | REVIEW | victor-4 | until 1791888455
HACK-007 | REVIEW | victor-5 | until 1791913457
HACK-010 | REVIEW | joahan-1 | until 1791917398
HACK-029 | REVIEW | victor-3 | until 1791917464

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791898637 | deadline lease/HACK-031/1791887455 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791899057 | HACK-007 | implement brief direction only; lock left to human | Why: needs luis pick
- 1791900367 | HACK-003 | ship via uak done after HACK-030 landed on main | Why: last pending criterion was unblocked
- 1791902448 | HACK-004 | k proportional for ivb/hb/speed_drop, additive plate_velo | Why: joahan-1 reject 16abfbb
- 1791902998 | HACK-010 | component xRV (5 outcomes x LMB values + contact) instead of direct rv regression | Why: direct regression on rv ~ noise; components stabilize 0.80

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
