# Auditoría del staff candidato de los Diablos (HACK-032)

Generado por `python -m analysis.staff_audit.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.

**Identificación inferida.** Los ids son anónimos. El staff "Diablos" son los pitchers de las dos franquicias con el aire más ligero (11, 5; `reports/park_id/franchise_rho.csv`). HACK-003 no separa CDMX de Puebla (P = 0.83), así que cada tabla se da **por franquicia** y nunca se juntan. Confirmar con el staff del club.

**Dos sabores de Stuff+.** `stuff_plus` = neutral (nivel del mar, 100 = liga); `stuff_plus_harp_helu` = el mismo lanzamiento en aire del Harp Helú (ρ 0.819); ΔCDMX = la diferencia. Las recomendaciones usan el modelo (todos los lanzamientos del pitcher); los splits casa/visita observados son pocos y van solo como control.

## Franquicia 11

35 pitchers con ≥ 200 lanzamientos (13 abridores, 22 relevistas). Stuff+ neutral medio 100.4; en aire del Harp Helú 89.7 (ΔCDMX -10.7).

Control de la física: Stuff+ neutral en casa − visita = +0.22 (≈ 0 si la traducción es correcta); Stuff+ en el aire real casa − visita = -6.4 (el efecto del aire).

**Mezcla en casa.** 19 de 35 pitchers tienen un lanzamiento claramente peor en aire del Harp Helú (≥ 5 puntos de Stuff+ por debajo de su mejor lanzamiento con uso ≥ 5 %). Mover 10 puntos de uso (o todo el uso si es menor) al lanzamiento en el que apoyarse ahorra 1.2 carreras por temporada en total. El mayor caso: pitcher_00932 (abridor), de *riding 4S* (76.5 en aire CDMX) a *gyro slider* (86.9): 0.19 carreras. Detalle: `staff_pitch_plan.csv`, `mix_runs.csv`.

**Rotación (2026, 5 abridores con ≥ 5 aperturas).** Orden en casa: pitcher_00636, pitcher_00464, pitcher_00938, pitcher_00401, pitcher_00932. Orden de visita: pitcher_00636, pitcher_00464, pitcher_00938, pitcher_00401, pitcher_00932.
Correlación de Spearman entre los dos órdenes: 1.00. Dar una apertura por serie en casa al abridor más resistente a la altura en lugar del menos resistente (brecha 11.7 puntos de Stuff+, 79 lanzamientos por apertura, 5 series en casa de 16 juegos, supuesto de 3 juegos por serie) ahorra 3.57 carreras por temporada.
Detalle: `rotation.csv`, `rotation_runs.csv`.

**Bullpen.** 22 relevistas. Más valiosos en casa: pitcher_00742, pitcher_00685, pitcher_00055. Emparejamientos por lado: 1 vs zurdos, 7 vs derechos, 14 sin ventaja clara (Pitching+ por lado, diferencia ≥ 1.5 puntos y ≥ 100 lanzamientos por lado). Detalle: `bullpen.csv`.

**Total proyectado:** 4.8 carreras por temporada ≈ 0.33 victorias (a 14.3 carreras por victoria en altitud extrema, HACK-035).

## Franquicia 5

45 pitchers con ≥ 200 lanzamientos (13 abridores, 32 relevistas). Stuff+ neutral medio 101.0; en aire del Harp Helú 90.6 (ΔCDMX -10.5).

Control de la física: Stuff+ neutral en casa − visita = +0.92 (≈ 0 si la traducción es correcta); Stuff+ en el aire real casa − visita = -6.1 (el efecto del aire).

**Mezcla en casa.** 17 de 45 pitchers tienen un lanzamiento claramente peor en aire del Harp Helú (≥ 5 puntos de Stuff+ por debajo de su mejor lanzamiento con uso ≥ 5 %). Mover 10 puntos de uso (o todo el uso si es menor) al lanzamiento en el que apoyarse ahorra 3.0 carreras por temporada en total. El mayor caso: pitcher_00736 (relevista), de *cutter* (81.4 en aire CDMX) a *gyro slider* (105.7): 0.68 carreras. Detalle: `staff_pitch_plan.csv`, `mix_runs.csv`.

**Rotación (2026, 5 abridores con ≥ 5 aperturas).** Orden en casa: pitcher_00019, pitcher_00964, pitcher_00103, pitcher_00705, pitcher_00664. Orden de visita: pitcher_00019, pitcher_00964, pitcher_00705, pitcher_00103, pitcher_00664.
Correlación de Spearman entre los dos órdenes: 0.90. Dar una apertura por serie en casa al abridor más resistente a la altura en lugar del menos resistente (brecha 9.1 puntos de Stuff+, 68 lanzamientos por apertura, 10 series en casa de 29 juegos, supuesto de 3 juegos por serie) ahorra 4.35 carreras por temporada.
Detalle: `rotation.csv`, `rotation_runs.csv`.

**Bullpen.** 32 relevistas. Más valiosos en casa: pitcher_00913, pitcher_00660, pitcher_00813. Emparejamientos por lado: 5 vs zurdos, 8 vs derechos, 19 sin ventaja clara (Pitching+ por lado, diferencia ≥ 1.5 puntos y ≥ 100 lanzamientos por lado). Detalle: `bullpen.csv`.

**Total proyectado:** 7.4 carreras por temporada ≈ 0.51 victorias (a 14.3 carreras por victoria en altitud extrema, HACK-035).

## Supuestos y límites

- Carreras por punto y lanzamiento: Stuff+ 0.000724, Pitching+ 0.00552 (`reports/business_value/runs_per_point_direct.csv`, OOF directo). Victorias: `runs_per_win.csv`.
- La mezcla supone que cada lanzamiento conserva su calidad al usarlo un poco más o menos y que los bateadores no se adaptan: es una estimación optimista de primer orden.
- Valor en casa de un pitcher = valor neutral (Pitching+) + resistencia a la altura (ΔCDMX del pitcher − ΔCDMX de la liga, a la tasa de Stuff+). La rotación solo cambia por esa resistencia: la calidad neutral es la misma en cualquier estadio.
- "Por temporada" = con los juegos en casa que hay en los datos de cada temporada (cobertura parcial; ver abajo). Con un calendario completo las carreras serían proporcionalmente mayores.
- Abridor = el pitcher con más lanzamientos en la primera entrada de su equipo en ese juego. Casa = su equipo inferido es el local del juego (HACK-003).
- Muestras pequeñas en casa (juegos en casa por temporada: franquicia 5: 43/43/29; franquicia 11: 3/14/16, `home_games.csv`): por eso las recomendaciones usan el modelo y no los resultados en casa.
