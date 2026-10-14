# worklog/WL-1791932819-joahan-1-HACK-016-hack.UPHsIq.md · HACK-016

## Live summary
- Done: pytest tests/test_score.py exit 0 (3 passed); full suite passed; smoke exit 0. Real data (python -m stuffplus.score): 623,231 pitches scored OOF by pitcher -> artifacts/scores/pitch_scores.parquet (git-ignored, email deliverable); leaderboards 818 pitcher-seasons, 3,546 pitcher x pitch; by_park: air effect +4.3 (rho 1.06) .. -10.7 (rho 0.81), r=0.996 with rho; README numbers checked vs CSVs. All files in Paths.
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `python -m pytest -q tests/test_score.py`
- Next: Humano: Smoke red or product unverified

## History
- 1791932819 | CLAIMED | joahan-1 | claim; next: batch predict with `serving.load_bundle()`.
- 1791934064 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-016?expand=1; evidence: pytest tests/test_score.py exit 0 (3 passed); full suite passed; smoke exit 0. Real data (python -m stuffplus.score): 623,231 pitches scored OOF by pitcher -> artifacts/scores/pitch_scores.parquet (git-ignored, email deliverable); leaderboards 818 pitcher-seasons, 3,546 pitcher x pitch; by_park: air effect +4.3 (rho 1.06) .. -10.7 (rho 0.81), r=0.996 with rho; README numbers checked vs CSVs. All files in Paths.; reviewer: -
- 1791948009 | REVIEW | victor-1 | review; approve; SHA a1296c796fd0d4475232b65b0775adbb9f2e8be0; reviewer victor-1
- 1791984730 | REVIEW | joahan-1 | heartbeat; lease until 1791999130
- 1791984768 | REVIEW | joahan-1 | merge rechazado; Smoke red or product unverified
