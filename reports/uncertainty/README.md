# Incertidumbre bajo cambio de entorno (HACK-055)

Generado por `python -m analysis.uncertainty.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.

## ¿Qué tan distinta es la altitud extrema para el modelo? (`shift.csv`)

Un clasificador que intenta distinguir lanzamientos de altitud extrema por su física (sin la densidad del aire) logra AUC 0.770 (0.5 = indistinguibles). El tamaño efectivo de muestra de los pesos de importancia es 45 % de los 444,065 lanzamientos de origen: hay solapamiento suficiente para ponderar (Shimodaira 2000).

## Validación ponderada contra el holdout real (`weighted_cv.csv`)

Solo con juegos sin altitud y de altitud media: la habilidad sobre el modelo nulo en validación por pitcher, la misma ponderada para parecerse a la altitud extrema, y la habilidad real al predecir la altitud extrema.

| Modelo | Validación de origen | Estimación ponderada | Holdout real en altitud extrema |
|---|---|---|---|
| Stuff+ | -0.05 % | -0.11 % | +0.00 % |
| Location+ | +2.92 % | +2.59 % | +2.35 % |

## Intervalos conformales para un pitcher (`conformal_pitchers.csv`)

Con la primera mitad de los juegos de una temporada se predice el valor de carreras por cada 100 lanzamientos en la segunda mitad. Intervalos al 90 % (Angelopoulos y Bates 2021), calibrados con la mitad de los pitchers y evaluados en la otra mitad. La versión ponderada (Tibshirani et al. 2019) sube el peso de los pitchers que lanzan sobre todo en altura.

| Predictor | ± carreras / 100 lanz. | Cobertura (todos) | Cobertura (sobre todo en altura) | Ponderado: ± | Ponderado: cobertura |
|---|---|---|---|---|---|
| pitching | 2.37 | 90.9 % | 89.3 % (n = 84) | 2.40 | 89.3 % |
| stuff | 2.56 | 91.4 % | 88.1 % (n = 84) | 2.76 | 92.9 % |

## Intervalo para el ΔStuff+ en altura de cada pitcher (`conformal_delta.csv`)

El ΔStuff+ del modelo y el observado (mismos lanzamientos en altitud extrema contra sin altitud, HACK-018) correlacionan 0.58. Para predecir el observado de un pitcher nuevo, el intervalo al 90 % mide ±7.6 puntos (cobertura en pitchers de prueba 93.2 %). El delta observado de un solo pitcher es ruidoso: el modelo da la expectativa y este intervalo dice cuánto puede desviarse un caso individual.

## Límites
- Los pesos de importancia usan la física del lanzamiento; la identidad del parque es inferida (HACK-003).
- La versión ponderada a nivel pitcher usa un solo indicador (lanza sobre todo en altura).
