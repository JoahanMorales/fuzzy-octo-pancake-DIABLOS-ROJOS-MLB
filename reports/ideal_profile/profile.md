# Perfil físico ideal para Diablos Rojos (HACK-017)

Stuff+ de HACK-015 (identidad `pitch_family`, traslado físico ajustado). Aire del Harp Helú: ρ = 0.819 (`RHO_HARP_HELU`). Escala neutral: 100 = promedio LMB a nivel del mar. Cifras copiadas de los CSV de esta carpeta.

## Qué rasgos importan más en altitud (`rho_sensitivity.csv`, rectas)

Dependencia parcial: el rasgo se fija en una rejilla (cuantiles 5–95 %) con el movimiento definido a nivel del mar, se traslada al aire de cada ρ con la física de HACK-015 y se puntúa. *Swing* = cambio de Stuff+ entre p5 y p95.

Dos vías del aire: **total** (física + rasgo `rho` del modelo) y **solo física** (movimiento trasladado, `rho` del modelo fijo a nivel del mar). Si el veredicto cambia entre ambas, el efecto viene de lo que el modelo aprendió de los juegos en altura y no solo de Magnus ∝ ρ.

| rasgo | swing mar | swing Harp Helú (total) | veredicto total | swing Harp Helú (solo física) | veredicto solo física |
|---|---:|---:|---|---:|---|
| IVB (in) | +20.86 | +7.62 | importa menos en altitud | +3.14 | importa menos en altitud |
| HB lado del brazo (in) | +10.04 | -3.50 | importa menos en altitud | -2.74 | importa menos en altitud |
| extensión (ft) | +2.22 | +4.92 | importa más en altitud | +3.39 | importa más en altitud |
| ángulo de brazo (°) | -6.51 | -4.85 | importa menos en altitud | -6.61 | igual |
| altura de salida (ft) | -1.33 | -2.92 | importa más en altitud | -1.92 | importa más en altitud |
| velocidad (mph) | +8.37 | +9.42 | importa más en altitud | +6.85 | importa menos en altitud |
| salida lateral (ft) | +7.20 | +6.16 | importa menos en altitud | +5.62 | importa menos en altitud |
| eje de giro (°) | -7.05 | -7.70 | igual | -7.90 | importa más en altitud |
| giro (rpm) | -1.73 | +2.07 | importa más en altitud | -2.22 | importa más en altitud |

IVB de la recta (`pdp_2d.csv`): Stuff+ medio al fijar el IVB a nivel del mar, lanzado en cada aire.

| IVB a nivel del mar (in) | ρ = 0.819 | ρ = 0.900 | ρ = 1.000 |
|---:|---:|---:|---:|
| 4.1 | 88.0 | 88.2 | 95.5 |
| 6.3 | 88.6 | 88.4 | 94.8 |
| 8.4 | 88.4 | 88.5 | 94.4 |
| 10.5 | 87.3 | 88.0 | 94.0 |
| 12.6 | 87.0 | 88.9 | 93.8 |
| 14.8 | 88.5 | 89.7 | 97.0 |
| 16.9 | 89.6 | 93.8 | 103.2 |
| 19.0 | 92.6 | 97.5 | 111.0 |
| 21.1 | 95.6 | 104.5 | 116.3 |

- Importan **más** en altitud: extensión (ft), altura de salida (ft), velocidad (mph), giro (rpm).
- Importan **menos** en altitud: IVB (in), HB lado del brazo (in), ángulo de brazo (°), salida lateral (ft).
- Interacción rasgo × ρ más fuerte (H², `h_statistic.csv`): hb_arm (0.112).

## Rasgos fuera del modelo (`delta_by_trait.csv`, rectas, IC 95 % por pitcher)

| rasgo | quintil | ΔStuff+ | IC 95 % |
|---|---|---:|---|
| vaa_neto_altura | [-8.53, -0.43] | -9.15 | [-9.78, -8.54] |
| vaa_neto_altura | [-0.43, -0.09] | -10.49 | [-11.05, -9.94] |
| vaa_neto_altura | [-0.09, 0.18] | -11.08 | [-11.58, -10.64] |
| vaa_neto_altura | [0.18, 0.48] | -12.05 | [-12.43, -11.61] |
| vaa_neto_altura | [0.48, 2.85] | -13.08 | [-13.55, -12.59] |
| eficiencia_giro | [0.01, 0.43] | -5.38 | [-5.62, -5.06] |
| eficiencia_giro | [0.43, 0.53] | -7.82 | [-8.12, -7.52] |
| eficiencia_giro | [0.53, 0.62] | -10.74 | [-11.07, -10.38] |
| eficiencia_giro | [0.62, 0.72] | -13.90 | [-14.23, -13.55] |
| eficiencia_giro | [0.72, 1.00] | -18.02 | [-18.36, -17.67] |
| velocidad | [46.13, 88.81] | -10.23 | [-10.69, -9.82] |
| velocidad | [88.81, 90.64] | -10.43 | [-10.92, -9.91] |
| velocidad | [90.64, 92.11] | -11.27 | [-11.86, -10.79] |
| velocidad | [92.11, 93.69] | -12.32 | [-12.78, -11.77] |
| velocidad | [93.69, 101.42] | -11.59 | [-12.19, -11.06] |
| extension | [-2.26, 5.58] | -12.83 | [-13.50, -12.21] |
| extension | [5.58, 5.88] | -11.32 | [-11.77, -10.86] |
| extension | [5.88, 6.13] | -11.04 | [-11.46, -10.56] |
| extension | [6.13, 6.43] | -10.93 | [-11.42, -10.43] |
| extension | [6.43, 14.43] | -9.73 | [-10.32, -9.13] |

VAA se usa neto de la altura en el plato (residuo por familia). La eficiencia de giro solo ordena lanzamientos: la brecha de ~15 % entre altitudes (HACK-004) sigue sin explicarse, así que no se presentan sus deltas como hecho.

## Mejor recta observada en el aire del Harp Helú (`best_fastballs.csv`)

Perfiles de recta dentro del casco de datos (kNN): 1007. Correlación de rangos altitud vs mar: 0.569; coinciden 2 de las 10 mejores. Solo con la vía física, la correlación es 0.500.

La mejor: Four-Seam, 90.7 mph, IVB 16.3" y HB 6.6" a nivel del mar, extensión 6.25 ft, salida 6.14 ft → Stuff+ 108.2 en el Harp Helú (115.5 a nivel del mar, Δ -7.3).

## Mejor secundario dado esa recta (`best_secondaries.csv`) y mejor arsenal de 3 (`best_arsenals.csv`)

Secundarios observados re-anclados a esa recta y dentro del casco conjunto (rasgos + diferencias): 232. Arsenales de 3 pitches observados: 186; correlación de rangos altitud vs mar 0.610.

## Receta (`receta.png`)

Hexágonos con el Stuff+ medio de perfiles de recta observados (≥ 3 por hexágono) en el aire del Harp Helú y su Δ contra el nivel del mar.

## Limitaciones

- Perfiles = centroides pitcher-temporada-familia; el Stuff+ de un perfil promedio no es el promedio de sus Stuff+.
- `add_stuff_features` (HACK-010) elige la recta principal por `AutoPitchType`, no por `pitch_family`.
- La interacción SHAP con ρ (`shap_rho_interaction.csv`) mide solo la vía directa del rasgo `rho`; la vía física (menos Magnus) está en la dependencia parcial.
- Escalas transductivas: identidad, densidad y valores de carrera se ajustan con todos los datos antes de puntuar.
- Los quintiles extremos de velocidad y extensión incluyen lecturas atípicas de Trackman (ver límites en `delta_by_trait.csv`).
- Requiere HACK-015 en `main` (`stuffplus.altitude`, `analysis/altitude_delta`).
