# STATE

Phase: execution
Updated: 1792205645
AVAILABLE: HACK-025 HACK-043 HACK-045 HACK-046 HACK-047 HACK-048 HACK-049 HACK-050 HACK-051 HACK-057 HACK-058 HACK-059 
CLAIMED: HACK-040 HACK-044 
BLOCKED: -
REVIEW: HACK-038 HACK-039 HACK-041 HACK-042 HACK-053 HACK-056 
INTEGRATED: (41; last 12) ... HACK-031 HACK-032 HACK-033 HACK-034 HACK-035 HACK-036 HACK-037 HACK-052 HACK-054 HACK-055 HACK-060 HACK-061 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-038 | REVIEW | luis-1 | until 1792218036
HACK-039 | REVIEW | joahan-1 | until 1792215092
HACK-040 | CLAIMED | victor-1 | until 1792207112
HACK-041 | REVIEW | victor-2 | until 1792216960
HACK-042 | REVIEW | victor-1 | until 1792217300
HACK-044 | CLAIMED | luis-2 | until 1792208345
HACK-053 | REVIEW | sebastian-1 | until 1792216899
HACK-056 | REVIEW | joahan-2 | until 1792217950

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1792199183 | deadline lease/HACK-056/1792199173 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1792200722 | deadline lease/HACK-052/1792199823 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1792202900 | HACK-042 | input is velo+sea-level ivb/hb (break-calibrated), not spin/axis | Why: flight.py is break-calibrated; physics.json has no C_L(S)
- 1792203636 | HACK-038 | mocks solo de agregados; delta de liga desde reports/stuff_v2 | Why: la web no puede fijar cifras antes del congelamiento
- 1792204546 | HACK-044 | mock local con demo_data porque parks.json no está en main | Why: HACK-038 sigue en su rama

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
