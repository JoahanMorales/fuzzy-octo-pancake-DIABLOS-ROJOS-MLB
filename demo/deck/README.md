# Presentación ejecutiva · HACK-036

10 diapositivas para una entrevista de 10 minutos. Identidad tipográfica Diablos con rojo #D71920, gris carbón y Arial, consistente con los reportes existentes. No sustituye ni cambia el diseño de la aplicación.

**Estado:** evidencia oficial agregada, exploratoria. PPTX editable y PDF disponibles. Staff, evaluador de prospectos, dashboard integrado y validación inductiva final pendientes. La presentación lo dice explícitamente.

| Lámina | Idea principal | Tiempo | Fuente de cifras |
|---|---|---:|---|
| 1 | El mismo arsenal cambia en el aire de CDMX | 45 s | Fuente: reports/altitude_delta/delta_by_shape.csv. Estimaciones exploratorias. |
| 2 | El aire estimado cambia entre ambientes | 55 s | reports/physics/rho_by_bucket.csv · media por bucket; parques anónimos. |
| 3 | La recta pierde movimiento vertical | 55 s | reports/physics/delta_extreme_vs_no.csv · Four-Seam/ivb; reports/altitude_delta/delta_by_shape.csv · 4S. |
| 4 | Pitching+ mejora el error. Stuff+ queda cerca | 75 s | reports/stuff_model/metrics.csv; reports/pitching_model/metrics.csv · rv_x, baseline por conteo. |
| 5 | Las pérdidas dependen de la forma del pitch | 65 s | reports/altitude_delta/delta_by_shape.csv · delta_stuff; misma forma, CDMX menos nivel del mar. |
| 6 | La resistencia varía entre arsenales | 65 s | reports/pitcher_sensitivity/top15.csv; reports/pitcher_sensitivity/bottom15.csv · temporada 2025; estimaciones EB. |
| 7 | El staff requiere confirmar la sede | 55 s | reports/park_id/franchise_rho.csv; reports/park_id/harp_helu.md · identidad provisional. |
| 8 | El prospecto comienza con un perfil físico | 50 s | Contrato: docs/CONTRACT.md; stuffplus/schema.py. Flujo propuesto, sin evaluación real de prospectos. |
| 9 | El entorno cambia el valor de una carrera | 65 s | reports/business_value/runs_per_win.csv · aproximación pitagórica; no proyección de ahorro del staff. |
| 10 | La demo compara y explica el arsenal | 70 s | Respaldo: reports/altitude_delta/ y reports/pitcher_sensitivity/. Integración de dashboard pendiente. |

## Archivos y reconstrucción

`stuffplus2240.pptx`: editable. `stuffplus2240.pdf`: versión de presentación. `../one-pager/resumen_ejecutivo.pdf`: una página para el GM.

`sources.json` conserva archivo, fila, columna, factor de formato y SHA-256 por cifra. El guion oral y los límites están en las notas de cada diapositiva. Todos los datos provienen de CSV agregados versionados. No se leen datos privados.

Reconstruir con Python 3.12 y `python-pptx`, `reportlab`, `pandas`, `pymupdf`: `python demo/deck/build.py`. Para PDF se usan Arial y Arial Bold de macOS. LibreOffice sirve para exportar el PPTX real a PDF y comparar visualmente. `python demo/deck/verify.py` valida fuentes, cifras y artefactos.

## Revisión antes de entrevista

Confirmar el staff y el estadio con el equipo, integrar salidas de HACK-032/021 y refrescar HACK-014 con holdouts inductivos reales. Sustituir los estados pendientes solo con resultados verificables. No citar `reports/benchmark/demo` como evidencia real.

En la demo integrada mostrar movimiento por ambiente, pérdida del arsenal y cobertura. Si no está integrada, presentar el PDF y abrir los CSV agregados. El respaldo actual no depende de servicios ni incluye una grabación plan B.

## Verificación

Verify del backlog: `test -s demo/deck/README.md`. Verificación de artefactos y trazabilidad: `python demo/deck/verify.py`. La evidencia real de ejecución y QA visual se documenta en `verification.md`.
