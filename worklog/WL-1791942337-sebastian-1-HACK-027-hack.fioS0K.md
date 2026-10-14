# worklog/WL-1791942337-sebastian-1-HACK-027-hack.fioS0K.md · HACK-027

## Live summary
- Done: Implemented actual CausalForestDML with pitcher-grouped nuisance CV; past-only covariates;2026holdout;propensity/support gates;aggregate-only reports;isolated optional env installed
- Decision: Report observational/transductive contrasts and conditional composition CIs, not causal-policy evidence
- Why: Unmeasured selection confounding and proxy target/identity/density preparation; EconML sklearn<1.7 requires isolatedenv
- Failing: Verify/demo running; no confirmed runtime failure yet
- Commands: uv pip install -r requirements.txt econml==0.16.0; python -m pytest -q tests/test_causal.py; python -m analysis.causal.run --demo --fast
- Next: Finish tests/demo, run official sampled whole games, inspect privacy/support/results, smoke/commit/push/PR then independent review

## History
- 1791942337 | CLAIMED | sebastian-1 | claim; next: treatment/outcome frame from Pitching+ OOF predictions.
- 1791942485 | CLAIMED | sebastian-1 | pending decision HACK-027-1791942485; option: Use isolated optional EconML extra; grouped nuisance CV; pre-pitch covariates; report only exploratory aggregate contrasts with overlap gates; Why: HACK-033 conflicts with UI owner; EconML incompatible with shared sklearn1.9; causal ignorability is not established; strong checkpoint unavailable at pace critical cap0
- 1791942887 | CLAIMED | sebastian-1 | checkpoint; next: Finish tests/demo, run official sampled whole games, inspect privacy/support/results, smoke/commit/push/PR then independent review
