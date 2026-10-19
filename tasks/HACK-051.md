# HACK-051
ID: HACK-051
State: REVIEW
Owner: luis-1
Branch: feat/hack-051
Worktree: /Users/FerV/Documents/HackDiablos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-051
Worklog: worklog/WL-1792373649-luis-1-HACK-051-hack.2NfXh6.md
Priority: P1
Paths: web/e2e/
Depends: HACK-045, HACK-043
Verify: `npm --prefix web run build && npx --prefix web playwright test`
Lease-Until: 1792392430
Updated: 1792378030
Task-Base: 9ccaf7a4bdeb8f877bf6e90839394b3953512ef4
Next: Humano: Edits a file outside Paths: web/playwright.config.ts (Paths of HACK-037). Revert that file on the branch (git checkout origin/main -- web/playwright.config.ts), or the human merges the PR
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/78
Evidence: beac61a2: npm --prefix web run build && npm --prefix web run e2e exit 0 (4/4 desktop+mobile, sin errores de consola, sin desborde movil, capturas deck en web/e2e/screenshots); smoke exit 0; vitest 170/170. Verify literal no corre desde la raiz (npx --prefix no cambia cwd): ver uak decision HACK-051
Events: 8
Checkpoints: 2
Sessions: 2
Last-Checkpoint: 1792374923
Task-Tip: beac61a2cf38f2cd6d22727c10afb116ea9d1fbe
