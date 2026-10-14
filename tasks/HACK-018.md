# HACK-018
ID: HACK-018
State: INTEGRATED
Owner: sebastian-2
Branch: feat/hack-018
Worktree: /Users/sebastian/Desktop/Hackathones/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-018
Worklog: worklog/WL-1791941086-sebastian-2-HACK-018-hack.QYsFI4.md
Priority: P0
Paths: analysis/pitcher_sensitivity/, reports/pitcher_sensitivity/, stuffplus/sensitivity.py, tests/test_sensitivity.py
Depends: HACK-015
Verify: `python -m pytest -q tests/test_sensitivity.py`
Lease-Until: 0
Updated: 1791942327
Task-Base: dcb3f2809a47993e919f4c7e426890a561f21376
Next: Integrated in main: 8347f3dbbe549eff74f400d16ebe44ce12751ddd; claim next P0
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/21
Evidence: Verify exit 0 (12 tests); smoke exit 0 PRODUCT_PASS; official --fast 623231 pitches/1455 pitcher-seasons/1277 eligible, top15/bottom15 anonymous aggregates; independent review and advisor GO
Events: 10
Checkpoints: 5
Sessions: 2
Last-Checkpoint: 1791941947
Task-Tip: 322aa9f2b9d092467f490428c225bf64ef2da091
Integration-Proof: ancestry
Merge-Commit: 8347f3dbbe549eff74f400d16ebe44ce12751ddd
Reviewer: joahan-1
