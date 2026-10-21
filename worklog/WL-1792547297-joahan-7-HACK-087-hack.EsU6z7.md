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
- 1792547561 | CLAIMED | joahan-7 | pending decision HACK-087-1792547561; option: update 5 literal asserts that pin the old familia source/value (tests/test_export_web.py:24-25, story.test.ts:21, landing.test.tsx:39,70) to the production value -13.0; regenerate mock/validation.json (test_write_mock requires it); Why: these asserts encode the bug HACK-087 fixes; superseded by tests/test_export_highlights.py
