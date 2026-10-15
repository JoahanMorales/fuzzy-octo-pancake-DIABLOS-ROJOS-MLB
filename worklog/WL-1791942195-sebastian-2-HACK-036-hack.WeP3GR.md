# worklog/WL-1791942195-sebastian-2-HACK-036-hack.WeP3GR.md · HACK-036

## Live summary
- Done: PR 31 SHA 5447c83: deck cites holdouts, separate franchise accounts, reference fastball and Stuff+ scale
- Decision: Staff numbers only from runs_saved.csv; franchises 5 and 11 never combined
- Why: HACK-032 contract and the park identity is still inferred
- Failing: LibreOffice export of the PPTX was not re-run
- Commands: test -s demo/deck/README.md; python demo/deck/verify.py
- Next: Wait for review of SHA 5447c83

## History
- 1791942195 | CLAIMED | sebastian-2 | claim; next: storyboard the 10 slides in `demo/deck/README.md` with the source CSV of each number.
- 1791942780 | CLAIMED | sebastian-2 | checkpoint; next: Finish smoke, commit/push and open draft PR with dependencies; checkpoint/handoff under critical pace
- 1791942997 | CLAIMED | sebastian-2 | checkpoint; next: Resume branch feat/hack-036 and PR #22; fill slides 7/8/10 from verified HACK-032/021/dashboard outputs, refresh slide 4 with HACK-014 and slide 9 with final scale; rebuild, verify/render, review before ready
- 1791943003 | CLAIMED | sebastian-2 | handoff; next: Resume branch feat/hack-036 and PR #22; fill slides 7/8/10 from verified HACK-032/021/dashboard outputs, refresh slide 4 with HACK-014 and slide 9 with final scale; rebuild, verify/render, review before ready
- 1791943008 | AVAILABLE | sebastian-2 | release; claim released by sebastian-2; reason: -; summary kept
- 1792027236 | CLAIMED | luis-1 | claim; next: Resume branch feat/hack-036 and PR #22; fill slides 7/8/10 from verified HACK-032/021/dashboard outputs, refresh slide 4 with HACK-014 and slide 9 with final scale; rebuild, verify/render, review before ready
- 1792027258 | CLAIMED | luis-1 | heartbeat; lease until 1792029958
- 1792027503 | CLAIMED | luis-1 | heartbeat; lease until 1792030203
- 1792027670 | REVIEW | luis-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/31; evidence: test -s demo/deck/README.md exit 0; python demo/deck/verify.py PASS 30 CSV values; SHA 5447c83; reviewer: -
- 1792027676 | REVIEW | luis-1 | checkpoint; next: Wait for review of SHA 5447c83
