# worklog/WL-1791920599-sebastian-1-HACK-014-hack.Q6gbOp.md · HACK-014

## Live summary
- Done: pytest tests/test_validation.py exit 0 (19 passed); full suite passed; smoke exit 0. Production real-data holdouts (official_full, acceptance_complete true): Pitching+ season +3.74% [3.54,3.94], park +3.28% [3.15,3.39]; pitcher kfold +3.88% (HACK-012); LOPO 20/20 parks >0 (fast). Altitude bias in Extreme with model never trained there: baseline +0.0109, Stuff+ no density +0.0046, Stuff+ +0.0025, Pitching+ +0.0020 runs/pitch. summary.md generated from CSVs. Continues sebastian-1's runner.
- Decision: Leave acceptance incomplete; retain explicit fast/transductive source flags and honest near-baseline Stuff+ result
- Why: Global target/feature preparation prevents inductive claims; final settings pending
- Failing: No current test/runtime failures;153unmapped park rows documented outsideLOPO only; final C1/C2 acceptance pending
- Commands: python -m pytest -q tests/test_validation.py; OMP_NUM_THREADS=2 python -m analysis.validation.run --fast --out reports/validation/official_fast; REAL_REPORT_QA_PASS; secret-scan --tracked
- Next: Integrated in main: 7dc8f4dc72b7e862e24f9bcf668095595c735345

## History
- 1791920599 | CLAIMED | sebastian-1 | claim; next: `stuffplus/validation/run_all.py` iterating `splits.*` × models.
- 1791921039 | CLAIMED | sebastian-1 | checkpoint; next: Finish smoke, commit/push, open draft partial PR; independently review before merge; fold preparation and official-data follow-up pending
- 1791939342 | CLAIMED | sebastian-1 | heartbeat; lease until 1791942042
- 1791939674 | CLAIMED | sebastian-1 | heartbeat; lease until 1791942374
- 1791939824 | CLAIMED | sebastian-1 | checkpoint; next: Review draft feat/hack-014 at 9ee6af7; implement documented fold-preparation contract, then run official-data validation before marking HACK-014 complete
- 1791939998 | CLAIMED | sebastian-1 | checkpoint; next: Wait official fast run, inspect aggregate metrics/provenance, update PR20 and reports; independent draft review pending
- 1791940381 | CLAIMED | sebastian-1 | heartbeat; lease until 1791943081
- 1791941106 | CLAIMED | sebastian-1 | heartbeat; lease until 1791943806
- 1791941400 | CLAIMED | sebastian-1 | checkpoint; next: Independent review of23120e5 official aggregates; implement fold-preparation contract and final run before task completion
- 1791941516 | CLAIMED | sebastian-1 | checkpoint; next: Implement documented fold-preparation contract in stuffplus/validation; verify held-out perturbation invariance and final official run; PR20 remains draft until acceptance complete
- 1791942187 | CLAIMED | sebastian-1 | handoff; next: Implement documented fold-preparation contract in stuffplus/validation; verify held-out perturbation invariance and final official run; PR20 remains draft until acceptance complete
- 1791942192 | AVAILABLE | sebastian-1 | release; claim released by sebastian-1; reason: -; summary kept
- 1791947931 | CLAIMED | joahan-1 | claim; next: Implement documented fold-preparation contract in stuffplus/validation; verify held-out perturbation invariance and final official run; PR20 remains draft until acceptance complete
- 1791950030 | REVIEW | joahan-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-014?expand=1; evidence: pytest tests/test_validation.py exit 0 (19 passed); full suite passed; smoke exit 0. Production real-data holdouts (official_full, acceptance_complete true): Pitching+ season +3.74% [3.54,3.94], park +3.28% [3.15,3.39]; pitcher kfold +3.88% (HACK-012); LOPO 20/20 parks >0 (fast). Altitude bias in Extreme with model never trained there: baseline +0.0109, Stuff+ no density +0.0046, Stuff+ +0.0025, Pitching+ +0.0020 runs/pitch. summary.md generated from CSVs. Continues sebastian-1's runner.; reviewer: -
- 1791950505 | REVIEW | victor-1 | review; approve; SHA 5c3e8ecf943d0183238fdce93d519f38871b8416; reviewer victor-1
- 1791986268 | REVIEW | joahan-1 | heartbeat; lease until 1792000668
- 1791986882 | INTEGRATED | joahan-1 | merge; smoke and Verify PASS; commit 7dc8f4dc72b7e862e24f9bcf668095595c735345; reviewer victor-1
