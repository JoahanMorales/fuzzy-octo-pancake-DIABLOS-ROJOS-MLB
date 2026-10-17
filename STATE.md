# STATE

Phase: execution
Updated: 1792203368
AVAILABLE: (14; last 12) ... HACK-043 HACK-044 HACK-045 HACK-046 HACK-047 HACK-048 HACK-049 HACK-050 HACK-051 HACK-057 HACK-058 HACK-059 
CLAIMED: HACK-038 
BLOCKED: -
REVIEW: HACK-039 HACK-041 HACK-042 HACK-053 HACK-056 HACK-060 HACK-061 
INTEGRATED: (39; last 12) ... HACK-029 HACK-030 HACK-031 HACK-032 HACK-033 HACK-034 HACK-035 HACK-036 HACK-037 HACK-052 HACK-054 HACK-055 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-038 | CLAIMED | luis-1 | until 1792206068
HACK-039 | REVIEW | joahan-1 | until 1792215092
HACK-041 | REVIEW | victor-2 | until 1792216960
HACK-042 | REVIEW | victor-1 | until 1792217300
HACK-053 | REVIEW | sebastian-1 | until 1792216899
HACK-056 | REVIEW | joahan-2 | until 1792216983
HACK-060 | REVIEW | joahan-1 | until 1792215356
HACK-061 | REVIEW | joahan-2 | until 1792214985

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1792185423 | HACK-052 | human adopted v2; R4 replaces R3 (2026-10-16) | Why: v2 beats count null, better pitcher-level and calibration; its larger altitude cost is closer to held
- 1792199013 | plan | joahan/joahan | tasks added: HACK-060 HACK-061 | Why: backlog without PR (Plan-Channel: claims)
- 1792199183 | deadline lease/HACK-056/1792199173 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1792200722 | deadline lease/HACK-052/1792199823 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1792202900 | HACK-042 | input is velo+sea-level ivb/hb (break-calibrated), not spin/axis | Why: flight.py is break-calibrated; physics.json has no C_L(S)

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
