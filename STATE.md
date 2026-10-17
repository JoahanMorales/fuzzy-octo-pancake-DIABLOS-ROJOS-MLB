# STATE

Phase: execution
Updated: 1792277305
AVAILABLE: HACK-051 HACK-058 HACK-059 HACK-062 HACK-063 HACK-025 
CLAIMED: HACK-045 HACK-049 HACK-057 
BLOCKED: HACK-046 
REVIEW: HACK-064 HACK-065 
INTEGRATED: (53; last 12) ... HACK-043 HACK-044 HACK-047 HACK-048 HACK-050 HACK-052 HACK-053 HACK-054 HACK-055 HACK-056 HACK-060 HACK-061 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-045 | CLAIMED | luis-3 | until 1792275155
HACK-046 | BLOCKED | sebastian-2 | until 1792266556
HACK-049 | CLAIMED | sebastian-1 | until 1792267092
HACK-057 | CLAIMED | joahan-2 | until 1792276043
HACK-064 | REVIEW | joahan-3 | until 1792288862
HACK-065 | REVIEW | joahan-1 | until 1792291705

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1792269240 | HACK-048 | loader uses real/ only if manifest parses; design_lab.json embedded until export_web adds it | Why: SPA fallback returns index.html 200; no contract file 
- 1792271792 | HACK-045 | Pitching+ equals Stuff+ until models/pitching.json exists; Harp rho comes from physics.json rho.harp_helu | Why: the export has stuff and location only, a
- 1792272455 | HACK-045 | Pitching+ equals Stuff+ until models/pitching.json is exported; models are fetched, not bundled | Why: the pitching composite is not in the web export and
- 1792273955 | HACK-064 | follow-up of HACK-047 by joahan-3: data.ts: real/ only when manifest.json parses as JSON (static hosts answer index.html with 200) | Why: same Paths, no s
- 1792273983 | HACK-065 | follow-up of HACK-050 by joahan-1: export real/design_lab.json from reports/design_lab (request #400) | Why: same Paths, no scope change

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
