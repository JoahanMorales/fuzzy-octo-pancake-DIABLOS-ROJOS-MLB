# Presentación ejecutiva · HACK-036

10 diapositivas para una entrevista de 10 minutos. Identidad tipográfica Diablos con rojo #D71920, gris carbón y Arial, consistente con los reportes existentes. No sustituye ni cambia el diseño de la aplicación.

**Estado:** evidencia oficial agregada, exploratoria. PPTX editable y PDF disponibles. Holdouts, cuentas de staff y perfilador están citados. Las franquicias 5 y 11 no se suman y la sede sigue sin confirmarse.

| Lámina | Idea principal | Tiempo | Fuente de cifras |
|---|---|---:|---|
| 1 | El mismo arsenal cambia en el aire de CDMX | 45 s | Fuente: reports/altitude_delta/delta_by_shape.csv. Estimaciones exploratorias. |
| 2 | El aire estimado cambia entre ambientes | 55 s | reports/physics/rho_by_bucket.csv · media por bucket; parques anónimos. |
| 3 | La recta pierde movimiento vertical | 55 s | reports/physics/delta_extreme_vs_no.csv · Four-Seam/ivb; reports/altitude_delta/delta_by_shape.csv · 4S. |
| 4 | Pitching+ se sostiene fuera de muestra | 75 s | reports/validation/headline.csv · skill frente al baseline por conteo. |
| 5 | Las pérdidas dependen de la forma del pitch | 65 s | reports/altitude_delta/delta_by_shape.csv · delta_stuff; misma forma, CDMX menos nivel del mar. |
| 6 | La resistencia varía entre arsenales | 65 s | reports/pitcher_sensitivity/top15.csv; reports/pitcher_sensitivity/bottom15.csv · temporada 2025; estimaciones EB. |
| 7 | Dos sedes, dos cuentas de carreras | 55 s | reports/staff_audit/runs_saved.csv · franquicias 5 y 11, por separado. |
| 8 | El prospecto se mide en el aire de casa | 50 s | reports/ideal_profile/best_fastballs.csv · recta de rango 1 por Stuff+ en el Harp Helú. |
| 9 | El entorno cambia el valor de una carrera | 65 s | reports/business_value/runs_per_win.csv; reports/business_value/runs_per_point_direct.csv · Stuff+, rv_x, fuera de muestra. |
| 10 | La demo compara el mismo arsenal | 70 s | Dashboard en el repo. Respaldo: reports/altitude_delta/ y este PDF. |

## Archivos y reconstrucción

`stuffplus2240.pptx`: editable. `stuffplus2240.pdf`: versión de presentación. `../one-pager/resumen_ejecutivo.pdf`: una página para el GM.

`sources.json` conserva archivo, fila, columna, factor de formato y SHA-256 por cifra. El guion oral y los límites están en las notas de cada diapositiva. Todos los datos provienen de CSV agregados versionados. No se leen datos privados.

Reconstruir con Python 3.12 y `python-pptx`, `reportlab`, `pandas`, `pymupdf`: `python demo/deck/build.py`. Para PDF se usan Arial y Arial Bold de macOS. LibreOffice sirve para exportar el PPTX real a PDF y comparar visualmente. `python demo/deck/verify.py` valida fuentes, cifras y artefactos.

## Revisión antes de entrevista

Confirmar con el club cuál de las franquicias 5 y 11 es la sede. No citar `reports/validation/demo` ni `reports/benchmark/demo` como evidencia real.

En la demo integrada mostrar movimiento por ambiente, pérdida del arsenal y cobertura. Si no está integrada, presentar el PDF y abrir los CSV agregados. El respaldo actual no depende de servicios ni incluye una grabación plan B.

## Verificación

Verify del backlog: `test -s demo/deck/README.md`. Verificación de artefactos y trazabilidad: `python demo/deck/verify.py`. La evidencia real de ejecución y QA visual se documenta en `verification.md`.
