# Auditoría final del modelo (HACK-084)

Generado por `python -m analysis.model_audit.run` sobre los datos reales y el Stuff+ de producción exportado (`web/public/data/models/stuff.json`); ninguna cifra se escribió a mano y no se reentrena nada.

**Regla fijada antes de correr:** el modelo solo cambia por una fuga de datos, pliegues que se traslapan o un traductor mal calibrado (fuera de ±15% y de ±0.5 in) en una familia con al menos 5% de los lanzamientos. Lo demás se declara como limitación.

**Veredicto: el modelo no cambia.**

## Comprobaciones (`checks.csv`, `scale.csv`)

- los rasgos exportados son V2_FEATURES: RelSpeed, SpinRate, spin_axis_arm, InducedVertBreak, hb_arm, RelHeight, rel_side_arm, Extension, arm_angle, is_rhp, pitch_family, rho, velo_diff_fb, ivb_diff_fb, hb_diff_fb, Balls, Strikes (pasa).
- sin ubicación, resultados ni ids en los rasgos: ninguno (pasa).
- pitchers repetidos entre pliegues: 0 (pasa).
- Stuff+ v2 no cambia con el conteo del lanzamiento (máx. |dif|): 0 (pasa).
- el traductor solo cambia movimiento y rho: HorzBreak, InducedVertBreak, hb_arm, hb_diff_fb, ivb_diff_fb, rho (pasa).
- Stuff+ por temporada: 2024 media 100.0, de 10.0; 2025 media 100.0, de 10.0; 2026 media 100.0, de 10.0.

## Traductor físico contra lo observado (`calibration.csv`)

Mismo lanzamiento (pitcher × temporada × identidad) en juegos de altitud extrema trasladado a la densidad de sus juegos sin altitud, contra lo que de verdad hizo en esos juegos. Cociente = cambio predicho / cambio observado.

| Familia | % lanzamientos | Componente | Observado (in) | Predicho (in) | Cociente | ¿Calibrado? |
|---|---:|---|---:|---:|---:|---|
| Four-Seam | 38.1 | HB lado del brazo | +3.17 | +3.42 | 1.08 | sí |
| Four-Seam | 38.1 | IVB | +3.77 | +3.88 | 1.03 | sí |
| Slider | 23.1 | HB lado del brazo | -0.44 | -0.30 | 0.69 | sí |
| Slider | 23.1 | IVB | +1.04 | +1.19 | 1.14 | sí |
| Sinker | 16.8 | HB lado del brazo | +4.73 | +4.84 | 1.02 | sí |
| Sinker | 16.8 | IVB | +2.14 | +2.11 | 0.98 | sí |
| Changeup | 12.5 | HB lado del brazo | +4.26 | +4.37 | 1.03 | sí |
| Changeup | 12.5 | IVB | +1.60 | +1.82 | 1.14 | sí |
| Curveball | 6.8 | HB lado del brazo | -2.76 | -2.96 | 1.07 | sí |
| Curveball | 6.8 | IVB | -2.02 | -1.83 | 0.91 | sí |
| Cutter | 1.9 | HB lado del brazo | +1.44 | +9.29 | 6.45 | no |
| Cutter | 1.9 | IVB | +2.67 | +2.72 | 1.02 | sí |
| Splitter | 0.6 | HB lado del brazo | +1.85 | +1.31 | 0.71 | no |
| Splitter | 0.6 | IVB | -0.26 | -0.15 | 0.57 | sí |

Las familias calibradas en sus dos componentes suman 97.5 % de los lanzamientos.
Fuera de tolerancia: Cutter HB lado del brazo (cociente 6.45, 1.9 % de los lanzamientos); Splitter HB lado del brazo (cociente 0.71, 0.6 % de los lanzamientos). La traducción proporcional se dispara cuando el movimiento medio está cerca de 0; el ΔStuff+ de esas familias se lee con cautela y no cambia el modelo por la regla de arriba.

## ¿De dónde sale el ΔStuff+ de la liga? (`decomposition.csv`)

En una muestra de 20,000 lanzamientos, el ΔStuff+ total en el aire del Harp Helú es -12.94. Con el movimiento trasladado y el rasgo `rho` del modelo fijo a nivel del mar: -5.95 (lo que quita perder Magnus). Con el movimiento fijo y solo el `rho` aprendido: -6.22 (lo que el modelo aprendió de los juegos en altura: el contacto hace más daño y la bola vuela más). El resto es la interacción.

## Límites
- Las diferencias observadas son crudas dentro del lanzamiento: incluyen cambios de ejecución (velocidad, giro) entre juegos, que el traductor no modela.
- La descomposición usa el modelo exportado del navegador, idéntico al de producción (paridad de HACK-066).
- `scale.csv` lee `artifacts/scores/pitch_scores.parquet` (git-ignored): debe ser la corrida de producción v2.
