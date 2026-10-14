# STATE

Phase: execution
Updated: 1791941106
AVAILABLE: HACK-020 HACK-021 HACK-032 HACK-033 HACK-034 HACK-022 HACK-023 HACK-036 HACK-024 HACK-025 HACK-027 HACK-028 
CLAIMED: HACK-014 HACK-018 
BLOCKED: -
REVIEW: HACK-007 HACK-016 HACK-017 
INTEGRATED: (19; last 12) ... HACK-009 HACK-010 HACK-011 HACK-012 HACK-013 HACK-015 HACK-019 HACK-026 HACK-029 HACK-030 HACK-031 HACK-035 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-007 | REVIEW | victor-5 | until 1791913457
HACK-014 | CLAIMED | sebastian-1 | until 1791943806
HACK-016 | REVIEW | joahan-1 | until 1791948464
HACK-017 | REVIEW | victor-1 | until 1791945455
HACK-018 | CLAIMED | sebastian-2 | until 1791943786

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791925103 | deadline lease/HACK-014/1791923739 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791925103 | deadline queue-lock/hack.O87yH8-sebastian-1-HACK-026/1791922783 | HUMAN | Lock lease expired; revalidate before merging
- 1791939288 | deadline lease/HACK-026/1791934738 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791939824 | HACK-014 | Draft implementation only; task acceptance remains incomplete | Why: Official input absent; shared preparation still transductive
- 1791939998 | HACK-014 | Use newly supplied official parquet for a fast exploratory diagnostic run before updating draft evidence | Why: User confirmed main data/raw; parquet63500

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
