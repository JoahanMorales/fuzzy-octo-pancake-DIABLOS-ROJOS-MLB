# Stuff+ v2: el conteo valora los resultados, el Stuff+ no depende del conteo (HACK-052)

Generado por `python -m analysis.stuff_v2.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.

**Qué cambia.** v1 predice el valor del lanzamiento sin ver el conteo, así que por lanzamiento no puede superar al modelo nulo de la rúbrica (xRV medio por conteo). v2 deja que el conteo (`Balls`, `Strikes`, nada más) valore los resultados: un strike vale más en 3-0 que en 0-2. La predicción por lanzamiento usa el conteo real y anida al nulo: mide el **valor incremental del stuff sobre el nulo por conteo**. El **Stuff+ v2** integra el conteo: promedia el valor del lanzamiento sobre la distribución de conteos de *su familia* en entrenamiento, así que la mezcla de conteos de un pitcher no mueve su Stuff+. Incluye interacciones stuff × conteo.

## Por lanzamiento: habilidad sobre el modelo nulo (`skill.csv`)

| Partición | Stuff+ v1 | Stuff+ v2 | Solo conteo (ablación) |
|---|---|---|---|
| pitcher_kfold | -0.025 % [-0.048, -0.002] | +0.178 % [+0.153, +0.205] | +0.000 % [+0.000, +0.000] |
| season_holdout | -0.001 % [-0.055, +0.040] | +0.203 % [+0.141, +0.267] | +0.000 % [+0.000, +0.000] |
| park_holdout | +0.004 % [-0.036, +0.040] | +0.230 % [+0.181, +0.283] | +0.000 % [-0.000, +0.000] |

**Atribución al stuff** (`incremental.csv`): v2 contra la misma arquitectura con solo el conteo.
- pitcher_kfold: +0.178 % [+0.153, +0.205]
- season_holdout: +0.203 % [+0.141, +0.267]
- park_holdout: +0.230 % [+0.181, +0.283]

## Nivel pitcher (`pitcher_level.csv`, 5 pliegues por pitcher)

| Modelo | 50 → resto (r) | 200 → resto (r) | Mitad contra mitad | Año a año |
|---|---|---|---|---|
| Stuff+ v1 | 0.265 | 0.306 | 0.807 | 0.738 |
| Stuff+ v2 (familia) | 0.269 | 0.323 | 0.803 | 0.725 |
| Stuff+ v2 (liga) | 0.265 | 0.319 | 0.802 | 0.727 |

Pendiente de calibración por lanzamiento (1 = ideal): Stuff+ v1 0.69; Stuff+ v2 0.80.

## Altitud (`altitude.csv`, aire del Harp Helú contra nivel del mar)

| Modelo | ΔStuff+ liga | Resiste más | Pierde más |
|---|---|---|---|
| Stuff+ v1 | -10.3 | sweeper (-4.6) | riding 4S (-16.0) |
| Stuff+ v2 (familia) | -12.7 | 12-6 CB (-9.2) | riding 4S (-17.4) |
| Stuff+ v2 (liga) | -12.5 | 12-6 CB (-8.4) | riding 4S (-17.8) |

## Decisión (regla fijada antes de correr; `decision.csv`)

| Regla | Prueba | Valor | ¿Pasa? |
|---|---|---|---|
| R1 | habilidad por lanzamiento sobre el nulo, pitcher_kfold: IC > 0 | +0.178 % [+0.153, +0.205] | sí |
| R1 | habilidad por lanzamiento sobre el nulo, season_holdout: IC > 0 | +0.203 % [+0.141, +0.267] | sí |
| R1 | habilidad por lanzamiento sobre el nulo, park_holdout: IC > 0 | +0.230 % [+0.181, +0.283] | sí |
| R2 | primeros 50 → resto: v2 ≥ v1 − 0.005 | 0.265 → 0.269 | sí |
| R2 | primeros 200 → resto: v2 ≥ v1 − 0.005 | 0.306 → 0.323 | sí |
| R2 | confiabilidad mitad contra mitad: v2 ≥ v1 − 0.005 | 0.807 → 0.803 | sí |
| R3 | ΔStuff+ de la liga en CDMX a ±1.5 de v1 | -10.3 → -12.7 | no |
| R3 | misma forma que más resiste y que más pierde | sweeper/riding 4S → 12-6 CB/riding 4S | no |

**Veredicto: no adoptar; v2 queda como ablación documentada.**

## Límites
- Mismas preparaciones transductivas que HACK-014 (identidad, densidad por juego, valores de carrera).
- Los pesos por familia salen del entrenamiento; la versión con un solo vector de la liga es la sensibilidad.
