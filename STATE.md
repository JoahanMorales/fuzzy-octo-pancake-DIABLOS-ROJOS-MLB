# STATE

Phase: execution
Updated: 1792374920
AVAILABLE: HACK-062 HACK-063 HACK-070 HACK-078 HACK-079 HACK-080 HACK-081 HACK-082 
CLAIMED: HACK-025 HACK-077 
BLOCKED: -
REVIEW: HACK-051 HACK-076 
INTEGRATED: (70; last 12) ... HACK-061 HACK-064 HACK-065 HACK-066 HACK-067 HACK-068 HACK-069 HACK-071 HACK-072 HACK-073 HACK-074 HACK-075 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
HACK-025 | CLAIMED | joahan-6 | until 1792313733
HACK-051 | REVIEW | luis-1 | until 1792389305
HACK-076 | REVIEW | joahan-2 | until 1792386366
HACK-077 | CLAIMED | luis-2 | until 1792377435

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1792309707 | HACK-074 | commit only uncertainty files; real/ refresh belongs to HACK-075 | Why: avoid clobbering HACK-075
- 1792311033 | HACK-025 | Do not mark done: video, other-laptop rehearsal, public URL and sending are human-owned | Why: Acceptance requires planb.mp4 (human), clean-clone rehearsa
- 1792369570 | deadline lease/HACK-025/1792313733 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1792370718 | plan | joahan/joahan | tasks added: HACK-076 HACK-077 HACK-078 HACK-079 HACK-080 HACK-081 HACK-082 | Why: backlog without PR (Plan-Channel: claims)
- 1792374243 | HACK-051 | --host 127.0.0.1 en playwright.config; Verify efectivo npm --prefix web run e2e | Why: vite escuchaba en ::1; npx --prefix web no cambia cwd

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
