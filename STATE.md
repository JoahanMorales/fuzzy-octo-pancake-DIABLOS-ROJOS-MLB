# STATE

Phase: execution
Updated: 1791899332
AVAILABLE: (25; last 12) ... HACK-032 HACK-033 HACK-034 HACK-035 HACK-022 HACK-023 HACK-036 HACK-024 HACK-025 HACK-026 HACK-027 HACK-028 
CLAIMED: HACK-003 
BLOCKED: -
REVIEW: HACK-004 HACK-005 HACK-006 HACK-007 HACK-013 HACK-029 HACK-031 
INTEGRATED: HACK-001 HACK-002 HACK-030 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-003 | CLAIMED | victor-1 | until 1791877608
HACK-004 | REVIEW | victor-2 | until 1791887724
HACK-005 | REVIEW | joahan-1 | until 1791885806
HACK-006 | REVIEW | victor-4 | until 1791888455
HACK-007 | REVIEW | victor-5 | until 1791913457
HACK-013 | REVIEW | joahan-1 | until 1791913721
HACK-029 | REVIEW | victor-3 | until 1791887759
HACK-031 | REVIEW | joahan-1 | until 1791887455

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791898637 | deadline lease/HACK-013/1791884853 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-029/1791887759 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-030/1791887764 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-031/1791887455 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791899057 | HACK-007 | implement brief direction only; lock left to human | Why: needs luis pick

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
