# STATE

Phase: execution
Updated: 1792308110
AVAILABLE: HACK-051 HACK-059 HACK-062 HACK-063 HACK-070 HACK-025 
CLAIMED: HACK-058 HACK-074 
BLOCKED: -
REVIEW: HACK-045 HACK-046 HACK-072 HACK-075 
INTEGRATED: (63; last 12) ... HACK-056 HACK-057 HACK-060 HACK-061 HACK-064 HACK-065 HACK-066 HACK-067 HACK-068 HACK-069 HACK-071 HACK-073 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-045 | REVIEW | joahan-3 | until 1792316974
HACK-046 | REVIEW | joahan-4 | until 1792321390
HACK-058 | CLAIMED | joahan-2 | until 1792309789
HACK-072 | REVIEW | joahan-1 | until 1792321350
HACK-074 | CLAIMED | victor-1 | until 1792309629
HACK-075 | REVIEW | joahan-5 | until 1792322346

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1792293062 | HACK-069 | compute width by n in export_web from OOF pitch scores | Why: reports/uncertainty has only global widths
- 1792306035 | HACK-066 | predict().xrv = count-neutral value for v2, like CountNeutral | Why: consumers keep working unchanged; parity with Python production model
- 1792306915 | HACK-074 | follow-up of HACK-069 by victor-1: Recalibrate the Stuff+ uncertainty bands on the v2 production scores (HACK-057/066) | Why: same Paths, no scope change
- 1792307251 | HACK-075 | follow-up of HACK-057 by joahan-2: Regenerate web/public/data/real with production Stuff+ v2 (real export still has v1 deltas) | Why: same Paths, no scope
- 1792307997 | deadline decision/HACK-046-1792306683/1792307583 | REVERSIBLE_AND_LOG | Option: Map criterion met as in sebastian-2 draft 88f6fc2: Mexico outline (Natural Earth, pub

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
