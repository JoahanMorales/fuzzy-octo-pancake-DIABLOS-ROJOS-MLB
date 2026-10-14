# worklog/WL-1791941086-sebastian-2-HACK-018-hack.QYsFI4.md · HACK-018

## Live summary
- Done: 12 pruebas PASS; oficial 623231 pitches/1455 pitcher-seasons/1277 elegibles; QA agregados PASS; revisión independiente y advisor GO
- Decision: Publicar rankings exploratorios con baseline/uso/fits fijos en CI; no certeza de rango
- Why: Limitación estadística explícita del advisor
- Failing: Smoke completo pendiente; q usa log único, no ejecutar q simultáneos
- Commands: python analysis/pitcher_sensitivity/run.py --fast; python -m pytest -q tests/test_sensitivity.py; agregado QA
- Next: Completar smoke, commit/push y PR; solicitar revisión del SHA

## History
- 1791941086 | CLAIMED | sebastian-2 | claim; next: usage-weighted aggregation of per-pitch ΔStuff+ by pitcher-season.
- 1791941339 | CLAIMED | sebastian-2 | checkpoint; next: Terminar corrida oficial --fast, revisar agregados, smoke, commit y PR
- 1791941512 | CLAIMED | sebastian-2 | heartbeat; lease until 1791944212
- 1791941551 | CLAIMED | sebastian-2 | checkpoint; next: Completar smoke, commit/push y PR; solicitar revisión del SHA
