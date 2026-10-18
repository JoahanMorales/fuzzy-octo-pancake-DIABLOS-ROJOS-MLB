# Validación · resumen (HACK-014)

Generado por `python -m stuffplus.validation.summary` desde los CSV citados; ninguna cifra se escribió a mano.
Objetivo `rv_x` (run value esperado LMB). Línea base de la rúbrica: xRV medio por conteo, ajustada solo con entrenamiento. Habilidad = reducción del RMSE vs esa línea base; IC 95 % remuestreando pitchers completos.

## Habilidad fuera de muestra vs el modelo nulo de la rúbrica

| Partición | Ajustes | Stuff+ | Location+ | Pitching+ |
|---|---|---|---|---|
| pitcher_kfold | production | -0.03 % [-0.06 %, -0.01 %] | +2.78 % [+2.70 %, +2.87 %] | +3.88 % [+3.78 %, +4.00 %] |
| season_holdout | production | +0.01 % [-0.04 %, +0.06 %] | +2.82 % [+2.66 %, +2.99 %] | +3.74 % [+3.54 %, +3.93 %] |
| park_holdout | production | +0.02 % [-0.02 %, +0.05 %] | +2.35 % [+2.24 %, +2.45 %] | +3.28 % [+3.15 %, +3.39 %] |
| leave_one_park_out (20 parks) | fast | +0.00 % (mín -0.13 %, máx +0.24 %; 8/20 > 0) | +2.28 % (mín +1.67 %, máx +2.95 %; 20/20 > 0) | +3.10 % (mín +2.12 %, máx +4.21 %; 20/20 > 0) |

Stuff+ puro no usa conteo ni ubicación (definición del reto), así que por lanzamiento no supera al modelo por conteo; su valor está en la estabilidad y la predicción a nivel pitcher (abajo). Pitching+ y Location+ sí lo superan en todas las particiones.

## ¿Sirve la física? Sesgo en altitud extrema sin haberla visto

Park holdout: se entrena SOLO con juegos sin altitud y de altitud media y se predicen los 181,032 lanzamientos de altitud extrema. Sesgo = carreras observadas − predichas por lanzamiento (positivo = el modelo subestima el daño). Fuente: `reports/validation/official_full/altitude_bias.csv`.

| Modelo | Sesgo (carreras/lanzamiento) | ± ee | vs línea base |
|---|---|---|---|
| baseline | +0.0109 | 0.0005 | — |
| Stuff+ physics neutral | +0.0059 | 0.0005 | -46 % |
| Stuff+ no density | +0.0046 | 0.0005 | -58 % |
| Stuff+ | +0.0025 | 0.0005 | -77 % |
| Location+ | +0.0035 | 0.0005 | -68 % |
| Pitching+ | +0.0020 | 0.0005 | -82 % |

Con la densidad del aire como variable, Stuff+ deja el 56 % del sesgo de la misma arquitectura sin ella (+0.0025 vs +0.0046), extrapolando a un aire que nunca vio en entrenamiento.

## Estabilidad y predicción a nivel pitcher

| Prueba | Stuff+ | Pitching+ | Resultados observados | Fuente |
|---|---|---|---|---|
| Primeros 50 lanzamientos → resto de la temporada (r) | 0.230 | 0.238 | 0.051 | `reports/{stuff,pitching}_model/predictiveness.csv` |
| Primeros 200 lanzamientos → resto de la temporada (r) | 0.270 | 0.333 | 0.110 | `reports/{stuff,pitching}_model/predictiveness.csv` |
| Estabilidad 2024→2025 (r, pitcher-temporada) | 0.707 | 0.589 | — | `official_fast/stability.csv` |
| Estabilidad 2025→2026 (r, pitcher-temporada) | 0.711 | 0.568 | — | `official_fast/stability.csv` |

## Stuff+ v1 → v2 (HACK-057, en producción)

Desde HACK-057 el Stuff+ de producción es v2: valor del lanzamiento neutral al conteo (HACK-052) con calibración por temperatura (HACK-053); Location+ también usa temperatura y Pitching+ queda sin calibrar. Las filas de la tabla de arriba siguen siendo la corrida oficial de v1; estas comparan v1 y v2 en las mismas particiones. La regla R3 (ΔStuff+ de liga a ±1.5 de v1) no se cumple y el humano adoptó R4 (sesgo en altitud no vista).

| Prueba | v1 | v2 | Fuente |
|---|---|---|---|
| Habilidad vs nulo, pitcher_kfold | -0.03 % [-0.05 %, -0.00 %] | +0.18 % [+0.15 %, +0.21 %] | `stuff_v2/skill.csv` |
| Habilidad vs nulo, season_holdout | -0.00 % [-0.06 %, +0.04 %] | +0.20 % [+0.14 %, +0.27 %] | `stuff_v2/skill.csv` |
| Habilidad vs nulo, park_holdout | +0.00 % [-0.04 %, +0.04 %] | +0.23 % [+0.18 %, +0.28 %] | `stuff_v2/skill.csv` |
| Primeros 50 → resto (r) | 0.265 | 0.269 | `stuff_v2/pitcher_level.csv` |
| Primeros 200 → resto (r) | 0.306 | 0.323 | `stuff_v2/pitcher_level.csv` |
| Mitad contra mitad (r) | 0.807 | 0.803 | `stuff_v2/pitcher_level.csv` |
| Sesgo en altitud extrema no vista (carreras/lanz.) | +0.0025 | +0.0018 | `stuff_v2/altitude_bias.csv` |
| ΔStuff+ de liga en el aire del Harp Helú | -10.3 | -12.7 | `stuff_v2/altitude.csv` |
| ΔStuff+ de liga en producción (v2 + temperatura) |  | -13.0 | `altitude_delta/delta_by_shape.csv` (Δ − relativo a la liga) |
| Calibración elegida (regla de HACK-053) | none | temperature | `calibration/decision.csv` |

## Límites

- Preparación transductiva: la identidad de lanzamiento, la densidad por juego, las referencias de arsenal y los valores de carrera LMB (RE, pesos lineales, valor esperado del batazo) se estiman una vez con todos los datos. Ningún paso usa el resultado de un lanzamiento como variable de ese lanzamiento, y todos los modelos se ajustan solo con entrenamiento; aun así las cifras son condicionales a esas entradas.
- Leave-one-park-out y estabilidad año a año vienen de la corrida rápida (pocos árboles): son conservadoras.
- Los parques son franquicias inferidas (HACK-003), no etiquetas verificadas de estadio.
