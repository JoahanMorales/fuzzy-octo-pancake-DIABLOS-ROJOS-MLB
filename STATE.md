# STATE

Phase: execution
Updated: 1791930590
AVAILABLE: (14; last 12) ... HACK-020 HACK-021 HACK-032 HACK-033 HACK-034 HACK-022 HACK-023 HACK-036 HACK-024 HACK-025 HACK-027 HACK-028 
CLAIMED: HACK-014 HACK-017 
BLOCKED: -
REVIEW: HACK-007 HACK-012 HACK-015 HACK-026 
INTEGRATED: (16; last 12) ... HACK-005 HACK-006 HACK-008 HACK-009 HACK-010 HACK-011 HACK-013 HACK-019 HACK-029 HACK-030 HACK-031 HACK-035 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-007 | REVIEW | victor-5 | until 1791913457
HACK-012 | REVIEW | joahan-1 | until 1791942685
HACK-014 | CLAIMED | sebastian-1 | until 1791923739
HACK-015 | REVIEW | joahan-1 | until 1791941748
HACK-017 | CLAIMED | victor-1 | until 1791933046
HACK-026 | REVIEW | sebastian-1 | until 1791934738

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791920338 | HACK-026 | Demo evidence only; no ensemble promotion or production changes | Why: Official dataset absent and shared preparation is transductive
- 1791920738 | HACK-015 | retrain Stuff+ with pitch_family; physics translation from ShapeModel | Why: AutoPitchType relabels with altitude
- 1791921039 | HACK-014 | Ship partial diagnostic runner only; task acceptance stays incomplete | Why: Pitching+ absent, shared preparation transductive, official parquet absent
- 1791925103 | deadline lease/HACK-014/1791923739 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791925103 | deadline queue-lock/hack.O87yH8-sebastian-1-HACK-026/1791922783 | HUMAN | Lock lease expired; revalidate before merging

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
