# worklog/WL-1791907357-victor-2-HACK-009-hack.sMInk4.md · HACK-009

## Live summary
- Done: 660cfd1: test_hypotheses 9 passed; smoke-project OK; H1 FF dIVB -3.79 (004 modelo -3.54, within-key raw -3.75); H1 Supported, H2 Rejected, H3 Partially, H4 Rejected(opposite); reports/hypotheses/summary.md
- Decision: bootstrap por pitcher sobre tabla agregada; verdict fijado antes de datos
- Why: advisor plan lock
- Failing: none
- Commands: pytest -q tests/test_hypotheses.py
- Next: Another agent reviews https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/12; run .uak/bin/smoke

## History
- 1791907357 | CLAIMED | victor-2 | claim; next: `hypotheses.within_pitcher_delta(df, metric, pitch_id_family, a, b, min_n=20, n_boot=2000)`.
- 1791907732 | CLAIMED | victor-2 | checkpoint; next: analysis/hypotheses/run.py H1 first
- 1791908139 | CLAIMED | victor-2 | heartbeat; lease until 1791910839
- 1791908149 | REVIEW | victor-2 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/12; evidence: 660cfd1: test_hypotheses 9 passed; smoke-project OK; H1 FF dIVB -3.79 (004 modelo -3.54, within-key raw -3.75); H1 Supported, H2 Rejected, H3 Partially, H4 Rejected(opposite); reports/hypotheses/summary.md; reviewer: -
- 1791908399 | REVIEW | victor-1 | review; approve; SHA 660cfd1c178664f22b8a6105106b93c332b14c2f; reviewer victor-1
