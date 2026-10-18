# Laboratorio de diseño de lanzamientos (HACK-033)

Para cada pitcher-temporada con ≥ 300 lanzamientos (784; 235,200 lanzamientos muestreados, ≤ 300 por temporada) se aplica un ajuste *coherente* al movimiento a nivel del mar y se puntúa con el modelo de HACK-015 (identidad `pitch_family`, traslado físico) en el aire del Harp Helú (`RHO_HARP_HELU`) y a nivel del mar. La **ganancia de arsenal** es el cambio medio de Stuff+ de todos los lanzamientos del pitcher (el ajuste a una familia puede mover las diferencias contra la recta de las demás). La **diferencia** = ganancia en el Harp Helú − ganancia a nivel del mar: cuánto más (o menos) vale el ajuste en CDMX.

## Qué ajuste gana más en CDMX (`tweak_summary.csv`)

| label | arsenal_gain_hh | hh_lo | hh_hi | arsenal_gain_sea | arsenal_diff | admissible_share | share_above_noise |
|---|---|---|---|---|---|---|---|
| +1 mph de velocidad | 0.573 | 0.547 | 0.601 | 0.534 | 0.0385 | 0.975 | 0.727 |
| eje de giro −5° | 0.347 | 0.319 | 0.373 | 0.29 | 0.0573 | 0.977 | 0.55 |
| +5 % de eficiencia de giro (más movimiento) | 0.237 | 0.222 | 0.254 | 0.658 | -0.421 | 0.978 | 0.531 |
| slot de brazo 5° más bajo | 0.153 | 0.121 | 0.188 | 0.0744 | 0.0789 | 0.97 | 0.473 |
| eje de giro +5° | -0.284 | -0.311 | -0.259 | -0.211 | -0.0732 | 0.974 | 0.229 |

**Mayor ganancia en el Harp Helú:** +1 mph de velocidad (+0.573 puntos de Stuff+ de arsenal [+0.547, +0.601]). **Vale más en CDMX que a nivel del mar:** slot de brazo 5° más bajo (diferencia +0.079 [+0.050, +0.108]). Piso de ruido: una ganancia < 0.1 puntos no entra al plan (convención; ≈ 7.2e-05 carreras por lanzamiento con `business_value/runs_per_point_direct.csv`).

## Lanzamiento nuevo (`new_pitch_summary.csv`)

Se agrega un splitter, un sinker o un sweeper con el perfil mediano de pitchers *comparables* (misma mano, velocidad de recta ±2.5 mph y ángulo de brazo ±12°; ≥ 8 comparables), con la salida del propio pitcher y un uso **supuesto** del 10% tomado proporcionalmente de los demás. Δ de arsenal = uso × (Stuff+ del lanzamiento nuevo − Stuff+ medio del arsenal); puede ser negativo.

| new_pitch | candidates | admissible_share | arsenal_gain_hh | hh_lo | hh_hi | arsenal_gain_sea | arsenal_diff | share_positive |
|---|---|---|---|---|---|---|---|---|
| splitter | 772 | 0 | – | – | – | – | – | – |
| sinker | 501 | 0.854 | -0.235 | -0.294 | -0.181 | -0.654 | 0.419 | 0.315 |
| sweeper | 646 | 0.717 | 0.262 | 0.19 | 0.329 | -0.356 | 0.618 | 0.639 |

## Cómo se acota a lo observado

- **Casco de datos:** un ajuste es admisible solo si el perfil resultante (centroide pitcher-temporada-familia) cae en la parte densa de los perfiles observados de esa familia (kNN, `profile.knn_in_hull`); fuera de ahí los árboles son planos y mostrarían ceros falsos. `admissible_share` dice en qué fracción de pitcher-temporadas aplica cada ajuste.
- **Eje de giro:** rotar el eje ±5° rota el vector (IVB, HB lado del brazo) el mismo ángulo con la magnitud intacta; el sentido (+) se estimó de los datos.
- **Eficiencia de giro +5 %:** supuesto físico (movimiento × 1.05, `SpinRate` fijo); la eficiencia no es un rasgo del modelo y la brecha de ~15 % entre altitudes (HACK-004) sigue sin explicarse.
- **Slot más bajo (−5°):** `RelHeight` sigue la geometría de `arm_angle` con la salida lateral fija; el movimiento cambia según la pendiente observada entre pitchers con distinto slot, por familia, controlando velocidad y giro (asociación, no causa).
- **Diferencias contra la recta:** un ajuste a la recta mueve las diferencias (velocidad, IVB, HB) de los secundarios del mismo pitcher-temporada.

## Plan de desarrollo (`development_plan_top3.csv`)

Top 3 ajustes por pitcher-temporada, solo admisibles y ≥ 0.1 puntos; ids anonimizados y sin filas por lanzamiento.

## Límites

- La ganancia es una diferencia del modelo (Stuff+ puro, sin ubicación ni conteo), no un efecto causal medido: cambiar un lanzamiento en la vida real mueve más de lo que el modelo ve.
- Escalas transductivas (identidad, densidad, valores de carrera) y modelo entrenado con todos los datos: las ganancias son en muestra del modelo; los IC solo propagan el muestreo de pitchers.
- La identidad de CDMX frente a Puebla sigue sin verificar (HACK-003); el aire del Harp Helú es ρ̂ = `RHO_HARP_HELU`.
