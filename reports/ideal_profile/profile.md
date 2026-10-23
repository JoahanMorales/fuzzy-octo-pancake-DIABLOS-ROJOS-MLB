# Perfil físico ideal para Diablos Rojos (HACK-017)

Stuff+ de producción v2 (HACK-057, el mismo de HACK-015; identidad `pitch_family`, traslado físico ajustado). Aire del Harp Helú: ρ = 0.819 (`RHO_HARP_HELU`). Escala neutral: 100 = promedio LMB a nivel del mar. Cifras copiadas de los CSV de esta carpeta.

## Qué rasgos importan más en altitud (`rho_sensitivity.csv`, rectas)

Dependencia parcial: el rasgo se fija en una rejilla (cuantiles 5–95 %) con el movimiento definido a nivel del mar, se traslada al aire de cada ρ con la física de HACK-015 y se puntúa. *Swing* = cambio de Stuff+ entre p5 y p95.

Dos vías del aire: **total** (física + rasgo `rho` del modelo) y **solo física** (movimiento trasladado, `rho` del modelo fijo a nivel del mar). Si el veredicto cambia entre ambas, el efecto viene de lo que el modelo aprendió de los juegos en altura y no solo de Magnus ∝ ρ.

| rasgo | swing mar | swing Harp Helú (total) | veredicto total | swing Harp Helú (solo física) | veredicto solo física |
|---|---:|---:|---|---:|---|
| IVB (in) | +21.10 | +5.83 | importa menos en altitud | +3.86 | importa menos en altitud |
| HB lado del brazo (in) | +7.65 | -3.50 | importa menos en altitud | -4.37 | importa menos en altitud |
| extensión (ft) | +1.48 | +5.42 | importa más en altitud | +1.98 | importa más en altitud |
| altura de salida (ft) | -1.96 | -4.37 | importa más en altitud | -3.10 | importa más en altitud |
| salida lateral (ft) | +6.79 | +4.76 | importa menos en altitud | +5.96 | importa menos en altitud |
| velocidad (mph) | +8.84 | +10.86 | importa más en altitud | +7.68 | importa menos en altitud |
| giro (rpm) | +0.35 | +1.89 | importa más en altitud | -0.04 | importa menos en altitud |
| eje de giro (°) | -4.60 | -5.37 | importa más en altitud | -4.82 | igual |
| ángulo de brazo (°) | -5.80 | -5.22 | importa menos en altitud | -4.99 | importa menos en altitud |

IVB de la recta (`pdp_2d.csv`): Stuff+ medio al fijar el IVB a nivel del mar, lanzado en cada aire.

| IVB a nivel del mar (in) | ρ = 0.819 | ρ = 0.900 | ρ = 1.000 |
|---:|---:|---:|---:|
| 4.1 | 85.4 | 87.1 | 93.3 |
| 6.3 | 85.9 | 86.5 | 92.4 |
| 8.4 | 85.0 | 85.9 | 92.3 |
| 10.5 | 83.6 | 85.2 | 92.3 |
| 12.6 | 82.8 | 85.9 | 92.5 |
| 14.8 | 84.6 | 87.5 | 95.5 |
| 16.9 | 85.8 | 90.7 | 101.0 |
| 19.0 | 87.9 | 94.0 | 108.9 |
| 21.1 | 91.3 | 101.1 | 114.4 |

- Importan **más** en altitud: extensión (ft), altura de salida (ft), velocidad (mph), giro (rpm), eje de giro (°).
- Importan **menos** en altitud: IVB (in), HB lado del brazo (in), salida lateral (ft), ángulo de brazo (°).
- Interacción rasgo × ρ más fuerte (H², `h_statistic.csv`): InducedVertBreak (0.100).

## Rasgos fuera del modelo (`delta_by_trait.csv`, rectas, IC 95 % por pitcher)

| rasgo | quintil | ΔStuff+ | IC 95 % |
|---|---|---:|---|
| vaa_neto_altura | [-8.53, -0.43] | -12.40 | [-12.93, -11.86] |
| vaa_neto_altura | [-0.43, -0.09] | -13.33 | [-13.84, -12.76] |
| vaa_neto_altura | [-0.09, 0.18] | -13.42 | [-13.97, -12.96] |
| vaa_neto_altura | [0.18, 0.48] | -13.94 | [-14.34, -13.46] |
| vaa_neto_altura | [0.48, 2.85] | -14.08 | [-14.59, -13.57] |
| eficiencia_giro | [0.01, 0.43] | -8.35 | [-8.64, -8.03] |
| eficiencia_giro | [0.43, 0.53] | -10.14 | [-10.40, -9.88] |
| eficiencia_giro | [0.53, 0.62] | -12.87 | [-13.18, -12.57] |
| eficiencia_giro | [0.62, 0.72] | -16.07 | [-16.40, -15.72] |
| eficiencia_giro | [0.72, 1.00] | -19.73 | [-20.16, -19.40] |
| velocidad | [46.13, 88.81] | -13.42 | [-13.90, -13.03] |
| velocidad | [88.81, 90.64] | -13.23 | [-13.66, -12.72] |
| velocidad | [90.64, 92.11] | -13.77 | [-14.33, -13.31] |
| velocidad | [92.11, 93.69] | -13.48 | [-13.94, -12.86] |
| velocidad | [93.69, 101.42] | -13.27 | [-13.86, -12.77] |
| extension | [-2.26, 5.58] | -15.28 | [-15.95, -14.67] |
| extension | [5.58, 5.88] | -14.31 | [-14.79, -13.78] |
| extension | [5.88, 6.13] | -13.50 | [-13.89, -13.03] |
| extension | [6.13, 6.43] | -13.10 | [-13.56, -12.64] |
| extension | [6.43, 14.43] | -10.98 | [-11.55, -10.35] |

VAA se usa neto de la altura en el plato (residuo por familia). La eficiencia de giro solo ordena lanzamientos: la brecha de ~15 % entre altitudes (HACK-004) sigue sin explicarse, así que no se presentan sus deltas como hecho.

## Mejor recta observada en el aire del Harp Helú (`best_fastballs.csv`)

Perfiles de recta dentro del casco de datos (kNN): 1007. Correlación de rangos altitud vs mar: 0.664; coinciden 1 de las 10 mejores. Solo con la vía física, la correlación es 0.585.

La mejor: Four-Seam, 91.4 mph, IVB 14.4" y HB 4.4" a nivel del mar, extensión 6.48 ft, salida 5.84 ft → Stuff+ 106.7 en el Harp Helú (105.3 a nivel del mar, Δ +1.4).

## Mejor secundario dado esa recta (`best_secondaries.csv`) y mejor arsenal de 3 (`best_arsenals.csv`)

Secundarios observados re-anclados a esa recta y dentro del casco conjunto (rasgos + diferencias): 219. Arsenales de 3 pitches observados: 186; correlación de rangos altitud vs mar 0.631.

## Receta (`receta.png`)

Hexágonos con el Stuff+ medio de perfiles de recta observados (≥ 3 por hexágono) en el aire del Harp Helú y su Δ contra el nivel del mar.

## Lista de verificación para reclutar (de estos CSV)

1. **No pagar por *ride* de recta.** El swing de Stuff+ entre IVB bajo y alto es +21.1 a nivel del mar y +5.8 en el Harp Helú (+3.9 solo con la física): la regla se sostiene.
2. **Extensión alta.** Quintil superior ΔStuff+ -11.0 contra -15.3 del inferior (brecha +4.3; IC sin traslape: robusta).
3. **VAA plano, neto de la altura de salida.** Quintil más plano -12.4 contra -14.1 del más inclinado (brecha +1.7; IC sin traslape: robusta).
4. **Velocidad.** ΔStuff+ por quintil: -13.4, -13.2, -13.8, -13.5, -13.3; no monótona: sin umbral de velocidad.

## Limitaciones

- Perfiles = centroides pitcher-temporada-familia; el Stuff+ de un perfil promedio no es el promedio de sus Stuff+.
- `add_stuff_features` (HACK-010) elige la recta principal por `AutoPitchType`, no por `pitch_family`.
- La interacción SHAP con ρ (`shap_rho_interaction.csv`) mide solo la vía directa del rasgo `rho`; la vía física (menos Magnus) está en la dependencia parcial.
- Escalas transductivas: identidad, densidad y valores de carrera se ajustan con todos los datos antes de puntuar.
- Los quintiles extremos de velocidad y extensión incluyen lecturas atípicas de Trackman (ver límites en `delta_by_trait.csv`).
- Requiere HACK-015 en `main` (`stuffplus.altitude`, `analysis/altitude_delta`).
