# worklog/WL-1792547297-joahan-7-HACK-087-hack.EsU6z7.md · HACK-087

## Live summary
- Done: pytest tests/test_export_web.py: 10 passed; npm --prefix web run build OK; npm --prefix web test -- --run: 20 files, 176 tests passed
- Decision: update 5 literal asserts that pin the old familia source/value (tests/test_export_web.py:24-25, story.test.ts:21, landing.test.tsx:39,70) to the production value -13.0; regenerate mock/validation.json (test_write_mock requires it)
- Why: these asserts encode the bug HACK-087 fixes; superseded by tests/test_export_highlights.py
- Failing: No validation run yet
- Commands: `python -m pytest -q --tb=short -x tests/test_export_highlights.py tests/test_export_web.py && npm --prefix web run build && npm --prefix web test -- --run`
- Next: Another agent reviews https://github.com/JoahanMorales/Ethical-hoops/compare/main...feat/hack-087?expand=1; run .uak/bin/smoke

## History
- 1792547297 | CLAIMED | joahan-7 | claim; next: change `_validation` in stuffplus/export_web.py (~line 222), re-export real/ to a scratch dir and copy only validation.json.
- 1792547561 | CLAIMED | joahan-7 | pending decision HACK-087-1792547561; option: update 5 literal asserts that pin the old familia source/value (tests/test_export_web.py:24-25, story.test.ts:21, landing.test.tsx:39,70) to the production value -13.0; regenerate mock/validation.json (test_write_mock requires it); Why: these asserts encode the bug HACK-087 fixes; superseded by tests/test_export_highlights.py
- 1792547989 | REVIEW | joahan-7 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-087?expand=1; evidence: SHA 7ebaa2f3 · pytest tests/test_export_highlights.py tests/test_export_web.py: 10 passed · npm --prefix web run build OK · npm --prefix web test -- --run: 176 passed · browser (vite preview, data/real): landing league-delta −13.0, presentación −13.0 + riding 4S −17.9; reviewer: -
- 1792720903 | REVIEW | scheduler | deadline decision HACK-087-1792547561; option: update 5 literal asserts that pin the old familia source/value (tests/test_export_web.py:24-25, story.test.ts:21, landing.test.tsx:39,70) to the production value -13.0; regenerate mock/validation.json (test_write_mock requires it); Why: these asserts encode the bug HACK-087 fixes; superseded by tests/test_export_highlights.py
- 1792722197 | REVIEW | joahan-7 | done; PR https://github.com/JoahanMorales/Ethical-hoops/compare/main...feat/hack-087?expand=1; evidence: pytest tests/test_export_web.py: 10 passed; npm --prefix web run build OK; npm --prefix web test -- --run: 20 files, 176 tests passed; reviewer: -
