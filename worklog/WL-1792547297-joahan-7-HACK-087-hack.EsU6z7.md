# worklog/WL-1792547297-joahan-7-HACK-087-hack.EsU6z7.md · HACK-087

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q --tb=short -x tests/test_export_highlights.py tests/test_export_web.py && npm --prefix web run build && npm --prefix web test -- --run`
- Next: change `_validation` in stuffplus/export_web.py (~line 222), re-export real/ to a scratch dir and copy only validation.json.

## History
- 1792547297 | CLAIMED | joahan-7 | claim; next: change `_validation` in stuffplus/export_web.py (~line 222), re-export real/ to a scratch dir and copy only validation.json.
