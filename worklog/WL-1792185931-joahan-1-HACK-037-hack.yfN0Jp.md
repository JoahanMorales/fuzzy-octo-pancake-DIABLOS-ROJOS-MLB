# worklog/WL-1792185931-joahan-1-HACK-037-hack.yfN0Jp.md · HACK-037

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `npm --prefix web ci && npm --prefix web run build && npm --prefix web test -- --run`
- Next: `npm create vite@5 web -- --template react-ts`, then add the deps above in one install.

## History
- 1792185931 | CLAIMED | joahan-1 | claim; next: `npm create vite@5 web -- --template react-ts`, then add the deps above in one install.
