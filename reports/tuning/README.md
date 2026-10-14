# Ajuste de modelos (HACK-028)

Generado por `python -m analysis.tuning.summary` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.

## Qué encontramos
Los modelos de producción entrenan un número FIJO de rondas (300 multiclase a learning rate 0.08) sin early stopping. En pitchers que el modelo no vio eso sobreajusta. La búsqueda (solo 2024–25, 3 pliegues por pitcher, rondas elegidas con un conjunto interno de pitchers y evaluadas en el pliegue externo; la temporada 2026 nunca se usa) mejora la pérdida de los 14 boosters:

| Booster | Producción (rondas) | Pérdida producción | Ajustado (rondas) | Pérdida ajustada |
|---|---|---|---|---|
| stuff_outcome | 300 | 1.5056 | 133 | 1.4946 |
| stuff_contact | 200 | 0.1346 | 52 | 0.1340 |
| location_outcome | 300 | 1.0531 | 210 | 1.0405 |
| location_contact | 200 | 0.1283 | 175 | 0.1282 |
| pitching_outcome | 300 | 1.0050 | 449 | 0.9975 |
| pitching_contact | 200 | 0.1274 | 190 | 0.1271 |
| target_t_swing | 200 | 0.4469 | 501 | 0.4442 |
| target_t_whiff | 200 | 0.4555 | 188 | 0.4554 |
| target_t_chase | 200 | 0.4399 | 413 | 0.4386 |
| target_t_called_strike | 200 | 0.1872 | 136 | 0.1868 |
| target_t_weak_contact | 200 | 0.6380 | 100 | 0.6339 |
| target_t_groundball | 200 | 0.6511 | 102 | 0.6474 |
| target_t_hard_contact | 200 | 0.3584 | 66 | 0.3521 |
| target_t_out_in_pa | 200 | 0.6346 | 58 | 0.6329 |

Fuente: `chosen.json`, `search_*.csv`, `search_summary.csv` (pérdida = log-loss o MSE en el pliegue externo, media de 3 pliegues).

## Antes / después (regla de adopción fijada antes de correrlo)

Se adopta un modelo ajustado solo si: mejora su log-loss; no bajan (más de 0.005) la predicción primeros 50 / 200 lanzamientos → resto de la temporada ni la confiabilidad split-half; y, para Stuff+, se sostiene la historia de altitud (ΔStuff+ de la liga a ±1 punto, mismas formas mejor y peor).

| Modelo | Log-loss | Habilidad vs nulo (k-fold) | Pendiente de calibración | 50 → resto (r) | 200 → resto (r) | Split-half (r) | Temporada | Estadio | Sesgo en altitud extrema |
|---|---|---|---|---|---|---|---|---|---|
| Stuff+ | 1.5013 | -0.03 % | 0.69 | 0.265 | 0.306 | 0.807 | -0.00 % | +0.00 % | +0.0025 |
| Stuff+ ajustado | 1.4961 | +0.02 % | 1.09 | 0.236 | 0.286 | 0.752 | +0.02 % | +0.05 % | +0.0036 |
| Location+ | 1.0419 | +2.78 % | 0.92 | 0.119 | 0.182 | 0.565 | +2.81 % | +2.35 % | +0.0036 |
| Location+ ajustado | 1.0352 | +2.86 % | 0.95 | 0.127 | 0.186 | 0.584 | +2.91 % | +2.49 % | +0.0035 |
| Pitching+ | — | +3.91 % | 1.00 | 0.250 | 0.360 | 0.659 | +3.73 % | +3.27 % | +0.0015 |
| Pitching+ ajustado | — | +3.94 % | 1.00 | 0.254 | 0.358 | 0.628 | +3.75 % | +3.37 % | +0.0008 |

Fuentes: `before_after_kfold.csv` (Stuff+, Location+: 5 pliegues por pitcher, todas las temporadas), `before_after_pitching_kfold.csv` (Pitching+ con combinación anidada), `holdouts/` (suite de HACK-014: temporada 2024–25 → 2026, estadio sin altitud extrema → extrema; sesgo = observado − predicho en altitud extrema).

Historia de altitud (`before_after_altitude.csv`): ΔStuff+ de la liga -10.3 (producción) vs -13.8 (ajustado); forma que más resiste sweeper vs slider; la que más pierde riding 4S (-16.0) vs riding 4S (-22.3).

## Decisión

- **Stuff+: no adoptar** (no cumple: primeros 50 → resto no baja; primeros 200 → resto no baja; confiabilidad split-half no baja; historia de altitud se sostiene).
- **Location+: adoptar**.
- **Pitching+: no adoptar** (no cumple: confiabilidad split-half no baja).

**Lectura.** El Stuff+ más regularizado predice mejor cada lanzamiento (log-loss, pendiente de calibración 0.69 → 1.09) pero distingue peor entre pitchers (split-half 0.81 → 0.75), que es para lo que sirve Stuff+. La varianza extra del modelo de producción no es solo ruido: lleva información estable de cada pitcher. Por eso Stuff+ se queda como está, y su sobre-dispersión por lanzamiento ya se corrige al convertir puntos a carreras (HACK-035 estima carreras por punto directamente, fuera de muestra).

## Límites
- Rejilla pequeña (regularización y número de rondas; learning rate 0.05); el criterio de búsqueda es la pérdida por lanzamiento, que no es lo mismo que la discriminación entre pitchers.
- Mismas preparaciones transductivas que HACK-014 (identidad, densidad por juego, valores de carrera).
