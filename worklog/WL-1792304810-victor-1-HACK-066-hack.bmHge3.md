# worklog/WL-1792304810-victor-1-HACK-066-hack.bmHge3.md · HACK-066

## Live summary
- Done: v2 production export + TS evaluator + contract
- Decision: predict().xrv = count-neutral value for v2, like CountNeutral
- Why: consumers keep working unchanged; parity with Python production model
- Failing: none
- Commands: python -m stuffplus.export_trees; PYTHONPATH=. python web/src/features/prospecto/make_golden.py
- Next: Wait for review of SHA 7533e00b; then refresh HACK-069 bands on v2

## History
- 1792304810 | CLAIMED | victor-1 | claim; next: read `CountNeutral` and `StuffV2Model.stuff_value` in stuffplus/models/.
- 1792306028 | REVIEW | victor-1 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/71; evidence: pytest test_export_trees 8 passed; vitest src/model+src/contract 13 passed; web suite 146 passed; build + check_web_dist + check_no_raw_data OK; smoke PRODUCT_PASS; models 13.42 MB; reviewer: -
- 1792306035 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA 7533e00b; then refresh HACK-069 bands on v2
