# worklog/WL-1791941086-sebastian-2-HACK-018-hack.QYsFI4.md · HACK-018

## Live summary
- Done: API, CLI, metodología y 9 pruebas de agregación/EB/input: Verify exit 0
- Decision: Índice relativo 100 + delta EB - delta liga; split observado estandarizado por arsenal común
- Why: Evitar confusión entre composición, resistencia relativa y efecto causal
- Failing: python ausente en shell; usar PATH del entorno existente hack-026
- Commands: PATH=.../hack-026/.venv/bin:$PATH bash .uak/bin/q python -m pytest -q tests/test_sensitivity.py
- Next: Terminar corrida oficial --fast, revisar agregados, smoke, commit y PR

## History
- 1791941086 | CLAIMED | sebastian-2 | claim; next: usage-weighted aggregation of per-pitch ΔStuff+ by pitcher-season.
- 1791941339 | CLAIMED | sebastian-2 | checkpoint; next: Terminar corrida oficial --fast, revisar agregados, smoke, commit y PR
