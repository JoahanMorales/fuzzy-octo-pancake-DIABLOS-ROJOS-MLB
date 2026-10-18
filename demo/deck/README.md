# Presentación ejecutiva v2 · HACK-036, HACK-059

10 diapositivas para una entrevista de 10 minutos, con Stuff+ v2 en producción (HACK-057). Rojo #D71920, gris carbón; el PDF usa DejaVu Sans incluida en `fonts/` (licencia en `fonts/LICENSE_DEJAVU`), así que se construye igual en Windows, macOS y Linux. El PPTX editable usa Arial.

**Estado:** evidencia oficial agregada. Las franquicias 5 y 11 no se suman: identificación inferida y sede sin confirmar.

| Lámina | Idea principal | Tiempo | Fuente de cifras |
|---|---|---:|---|
| 1 | El mismo arsenal pierde 13.0 puntos de Stuff+ en el aire de CDMX | 45 s | reports/altitude_delta/delta_by_shape.csv · promedio de la liga = ΔStuff+ de una forma − su diferencia contra la liga. |
| 2 | El aire estimado cambia entre ambientes | 55 s | reports/physics/rho_by_bucket.csv · media por bucket; parques anónimos. |
| 3 | La recta pierde subida: el Magnus cae más rápido que el aire | 55 s | reports/physics/delta_extreme_vs_no.csv; reports/altitude_delta/delta_by_shape.csv · 4S; reports/physics_v2/magnus_elasticity.csv. |
| 4 | Le ganamos al modelo nulo de la rúbrica | 75 s | reports/validation/headline.csv; reports/stuff_v2/skill.csv; reports/stuff_v2/pitcher_level.csv. |
| 5 | La física corrige el sesgo de altitud | 55 s | reports/stuff_v2/altitude_bias.csv · entrenado sin altitud extrema, evaluado en ella. |
| 6 | Las pérdidas dependen de la forma del pitch | 65 s | reports/altitude_delta/delta_by_shape.csv · delta_stuff; misma forma, CDMX menos nivel del mar. |
| 7 | Dos sedes candidatas, dos cuentas de carreras | 55 s | reports/staff_audit/runs_saved.csv · franquicias 5 y 11, por separado. |
| 8 | El producto: dos aires, un lanzamiento | 50 s | Capturas del simulador 3D y del explicador de física (web/, build de HACK-045 y HACK-072). |
| 9 | El entorno cambia el valor de una carrera | 65 s | reports/business_value/runs_per_win.csv; reports/business_value/gm_example.csv · escala de Stuff+ medida con v1. |
| 10 | La demo compara el mismo arsenal | 70 s | Producto web en el repo. Respaldo: este PDF y los CSV agregados de reports/. |

## Archivos y reconstrucción

`deck.pptx`: editable. `deck.pdf`: versión de presentación. `../one-pager/one-pager.pdf`: una página para el GM. `assets/`: capturas del producto (simulador de HACK-045 y explicador de HACK-072); cuando HACK-051 publique sus capturas de Playwright, reemplazarlas con el mismo nombre.

`sources.json` guarda archivo, fila, columna, formato y SHA-256 de cada cifra, y para las dos cifras derivadas (promedio de la liga y recorte del sesgo) sus entradas y la fórmula. Las notas de cada diapositiva llevan el guion oral.

Reconstruir con Python 3.12 y `demo/deck/requirements.txt`: `python demo/deck/build.py`. Validar: `python demo/deck/verify.py`.

## Revisión antes de entrevista

Confirmar con el club cuál de las franquicias 5 y 11 es la sede. La conversión a victorias se midió con la escala de Stuff+ v1 (`reports/business_value/stuff_scale_calibration.csv`).

## Verificación

Verify del backlog: `test -s demo/deck/deck.pdf && test -s demo/one-pager/one-pager.pdf`. Trazabilidad: `python demo/deck/verify.py`.
