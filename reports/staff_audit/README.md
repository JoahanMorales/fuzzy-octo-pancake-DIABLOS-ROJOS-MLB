# Auditoría del staff candidato de los Diablos (HACK-032)

Generado por `python -m analysis.staff_audit.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.

**Identificación inferida.** Los ids son anónimos. El staff "Diablos" son los pitchers de las dos franquicias con el aire más ligero (11, 5; `reports/park_id/franchise_rho.csv`). Los datos no separan con confianza CDMX de Puebla (`reports/park_id/harp_helu.md`), así que cada tabla se da **por franquicia** y nunca se juntan. Confirmar con el staff del club.

**Dos sabores de Stuff+.** `stuff_plus` = neutral (nivel del mar, 100 = liga); `stuff_plus_harp_helu` = el mismo lanzamiento en aire del Harp Helú (ρ = 0.819); ΔCDMX = la diferencia. Las recomendaciones usan el modelo (todos los lanzamientos del pitcher); los splits casa/visita observados son pocos y van solo como control.

## Franquicia 11

35 pitchers con ≥ 200 lanzamientos (13 abridores, 22 relevistas). Stuff+ neutral medio 100.3; en aire del Harp Helú 86.8 (ΔCDMX -13.4).

Control de la física: Stuff+ neutral en casa − visita = +1.29 (≈ 0 si la traducción es correcta); Stuff+ en el aire real casa − visita = -7.8 (el efecto del aire).
Contra HACK-018 (`reports/pitcher_sensitivity/pitchers.csv`): la correlación entre el ΔCDMX del modelo y el delta observado del mismo pitcher es 0.57 (33 pitchers con delta observado).

**Mezcla en casa.** 22 de 35 pitchers tienen un lanzamiento claramente peor en aire del Harp Helú (≥ 5 puntos de Stuff+ por debajo de su mejor lanzamiento con uso ≥ 5 %). Mover 10 puntos de uso en casa (o todo el uso si es menor) al lanzamiento en el que apoyarse ahorra 2.0 carreras por temporada en total. El mayor caso: pitcher_00685 (relevista), de *4S · 93.3 mph* (86.1 en aire CDMX) a *gyro slider · 84.6 mph* (103.1): 0.24 carreras. Detalle: `staff_pitch_plan.csv`, `mix_runs.csv`.

**Rotación (2026, 5 abridores con ≥ 5 aperturas).** Orden en casa: pitcher_00636, pitcher_00464, pitcher_00938, pitcher_00401, pitcher_00932. Orden de visita: pitcher_00636, pitcher_00464, pitcher_00938, pitcher_00401, pitcher_00932.
El orden **no cambia** entre casa y visita: la resistencia a la altura no alcanza a reordenar a estos abridores.
Lo que sí cambia es **a quién le tocan las aperturas en casa**: pasar aperturas en casa de pitcher_00401 (el menos resistente) a pitcher_00464 (el más resistente; brecha 10.6 puntos de Stuff+, 79 lanzamientos por apertura) vale 0.61 carreras por apertura. Con a lo más una por serie en casa y el tope que permite la temporada (3 cambios: aperturas en casa del primero y de visita del segundo; series de 3 juegos supuestas) son 1.82 carreras por temporada.
Detalle: `rotation.csv`, `rotation_runs.csv`.

**Bullpen.** 22 relevistas. Más valiosos en casa: pitcher_00685, pitcher_00742, pitcher_00055. Ventaja por lado del bateador **por encima de la normal de la liga** para su mano: 1 vs zurdos, 2 vs derechos, 19 sin ventaja clara (diferencia ≥ 1.5 puntos de Pitching+ y ≥ 100 lanzamientos por lado). Detalle: `bullpen.csv`.

**Total proyectado:** 3.8 carreras por temporada ≈ 0.26 victorias (a 14.3 carreras por victoria en altitud extrema, HACK-035).

## Franquicia 5

45 pitchers con ≥ 200 lanzamientos (13 abridores, 32 relevistas). Stuff+ neutral medio 101.2; en aire del Harp Helú 87.9 (ΔCDMX -13.3).

Control de la física: Stuff+ neutral en casa − visita = +1.17 (≈ 0 si la traducción es correcta); Stuff+ en el aire real casa − visita = -7.9 (el efecto del aire).
Contra HACK-018 (`reports/pitcher_sensitivity/pitchers.csv`): la correlación entre el ΔCDMX del modelo y el delta observado del mismo pitcher es 0.68 (42 pitchers con delta observado).

**Mezcla en casa.** 25 de 45 pitchers tienen un lanzamiento claramente peor en aire del Harp Helú (≥ 5 puntos de Stuff+ por debajo de su mejor lanzamiento con uso ≥ 5 %). Mover 10 puntos de uso en casa (o todo el uso si es menor) al lanzamiento en el que apoyarse ahorra 4.3 carreras por temporada en total. El mayor caso: pitcher_00736 (relevista), de *cutter · 87.3 mph* (79.6 en aire CDMX) a *gyro slider · 79.2 mph* (101.4): 0.61 carreras. Detalle: `staff_pitch_plan.csv`, `mix_runs.csv`.

**Rotación (2026, 5 abridores con ≥ 5 aperturas).** Orden en casa: pitcher_00019, pitcher_00964, pitcher_00103, pitcher_00705, pitcher_00664. Orden de visita: pitcher_00019, pitcher_00964, pitcher_00705, pitcher_00103, pitcher_00664.
Los órdenes difieren poco (Spearman 0.90).
Lo que sí cambia es **a quién le tocan las aperturas en casa**: pasar aperturas en casa de pitcher_00964 (el menos resistente) a pitcher_00019 (el más resistente; brecha 7.8 puntos de Stuff+, 68 lanzamientos por apertura) vale 0.38 carreras por apertura. Con a lo más una por serie en casa y el tope que permite la temporada (3 cambios: aperturas en casa del primero y de visita del segundo; series de 3 juegos supuestas) son 1.15 carreras por temporada.
Detalle: `rotation.csv`, `rotation_runs.csv`.

**Bullpen.** 32 relevistas. Más valiosos en casa: pitcher_00987, pitcher_00913, pitcher_00660. Ventaja por lado del bateador **por encima de la normal de la liga** para su mano: 4 vs zurdos, 2 vs derechos, 26 sin ventaja clara (diferencia ≥ 1.5 puntos de Pitching+ y ≥ 100 lanzamientos por lado). Detalle: `bullpen.csv`.

**Total proyectado:** 5.5 carreras por temporada ≈ 0.38 victorias (a 14.3 carreras por victoria en altitud extrema, HACK-035).

## Supuestos y límites

- Carreras por punto y lanzamiento: Stuff+ 0.000724, Pitching+ 0.00551 (`reports/business_value/runs_per_point_direct.csv`, OOF directo). Victorias: `runs_per_win.csv`.
- La mezcla supone que cada lanzamiento conserva su calidad al usarlo un poco más o menos y que los bateadores no se adaptan: es una estimación optimista de primer orden.
- Valor en casa de un pitcher = valor neutral (Pitching+) + resistencia a la altura (ΔCDMX del pitcher − ΔCDMX de la liga, a la tasa de Stuff+). La asignación de aperturas solo cambia por esa resistencia: la calidad neutral es la misma en cualquier estadio.
- "Por temporada" = con los juegos en casa que hay en los datos de cada temporada (cobertura parcial; ver abajo). Con un calendario completo las carreras serían proporcionalmente mayores.
- Abridor = el pitcher con más lanzamientos en la primera entrada de su equipo en ese juego. Casa = su equipo inferido es el local del juego (HACK-003).
- Muestras pequeñas en casa (juegos en casa por temporada: franquicia 5: 43/43/29; franquicia 11: 3/14/16, `home_games.csv`): por eso las recomendaciones usan el modelo y no los resultados en casa. Umbrales: `params.csv`.
