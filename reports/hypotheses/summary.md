# Hipótesis H1–H4 con evidencia LMB (HACK-009)

Diseño: comparación intra-lanzamiento (`pitch_key` de `pitch_id`, no `AutoPitchType`), IC 95 % bootstrap por **pitcher**, dosis-respuesta contra la ρ̂ del **parque** (mediana de sus juegos, misma escala que HACK-004). Regla de veredicto fijada de antemano (`stuffplus.hypotheses.verdict`): *Supported* = Δ e pendiente excluyen 0 en la dirección predicha; *Partially* = solo uno; *Rejected* = ninguno. Las filas «info» no entran al veredicto.
Juegos: 2114; sin parque identificado: 3; lanzamientos con `pitch_id`: 623231.

## H1 · Pérdida de movimiento (magnitud) y de caída de velocidad en Extreme vs sin altitud

**Veredicto global: Supported**

Todas las familias pierden quiebre y caída de velocidad, con pendiente consistente contra la ρ̂ del parque (curva dosis-respuesta, `h1_dose_park.png`). Medido en magnitud: la curva *pierde* quiebre aunque su IVB (con signo) suba, porque cae menos. Coincide con HACK-004.

| Métrica | Familia | Contraste | Δ [IC 95 %] | Pendiente por +0.1 ρ̂ [IC] | Pitchers / claves | Veredicto |
|---|---|---|---|---|---|---|
| abs_ivb | Four-Seam | Extreme-No | -3.79 [-3.92, -3.66] | +2.38 [+2.3, +2.45] | 440 / 732 | Supported |
| abs_ivb | Four-Seam | Medium-No | -2.83 [-2.97, -2.7] | – | 360 / 603 | info |
| abs_hb | Four-Seam | Extreme-No | -3.09 [-3.23, -2.95] | +1.84 [+1.74, +1.93] | 440 / 732 | Supported |
| abs_hb | Four-Seam | Medium-No | -2.23 [-2.37, -2.09] | – | 360 / 603 | info |
| total_break | Four-Seam | Extreme-No | -4.94 [-5.08, -4.8] | +3.04 [+2.96, +3.12] | 440 / 732 | Supported |
| total_break | Four-Seam | Medium-No | -3.62 [-3.77, -3.48] | – | 360 / 603 | info |
| SpeedDrop | Four-Seam | Extreme-No | -1.36 [-1.39, -1.32] | +0.828 [+0.81, +0.845] | 440 / 732 | Supported |
| SpeedDrop | Four-Seam | Medium-No | -0.889 [-0.931, -0.848] | – | 360 / 603 | info |
| InducedVertBreak | Four-Seam | Extreme-No | -3.79 [-3.92, -3.65] | +2.38 [+2.3, +2.46] | 440 / 732 | info |
| InducedVertBreak | Four-Seam | Medium-No | -2.86 [-3, -2.72] | – | 360 / 603 | info |
| abs_ivb | Sinker | Extreme-No | -2.13 [-2.34, -1.9] | +1.32 [+1.19, +1.45] | 192 / 321 | Supported |
| abs_ivb | Sinker | Medium-No | -1.51 [-1.7, -1.32] | – | 168 / 251 | info |
| abs_hb | Sinker | Extreme-No | -4.63 [-4.83, -4.42] | +2.74 [+2.61, +2.86] | 192 / 321 | Supported |
| abs_hb | Sinker | Medium-No | -3.24 [-3.46, -3.03] | – | 168 / 251 | info |
| total_break | Sinker | Extreme-No | -5.05 [-5.25, -4.85] | +3.03 [+2.93, +3.14] | 192 / 321 | Supported |
| total_break | Sinker | Medium-No | -3.54 [-3.77, -3.32] | – | 168 / 251 | info |
| SpeedDrop | Sinker | Extreme-No | -1.31 [-1.36, -1.27] | +0.805 [+0.782, +0.828] | 192 / 321 | Supported |
| SpeedDrop | Sinker | Medium-No | -0.878 [-0.931, -0.826] | – | 168 / 251 | info |
| InducedVertBreak | Sinker | Extreme-No | -1.97 [-2.23, -1.66] | +1.26 [+1.08, +1.42] | 192 / 321 | info |
| InducedVertBreak | Sinker | Medium-No | -1.39 [-1.62, -1.14] | – | 168 / 251 | info |
| abs_ivb | Cutter | Extreme-No | -2.82 [-3.43, -2.24] | +1.72 [+1.24, +2.13] | 33 / 40 | Supported |
| abs_ivb | Cutter | Medium-No | -1.98 [-2.58, -1.43] | – | 26 / 33 | info |
| abs_hb | Cutter | Extreme-No | -0.649 [-1.12, -0.208] | +0.54 [+0.157, +0.971] | 33 / 40 | Supported |
| abs_hb | Cutter | Medium-No | -0.58 [-0.976, -0.203] | – | 26 / 33 | info |
| total_break | Cutter | Extreme-No | -3.03 [-3.57, -2.5] | +1.96 [+1.54, +2.32] | 33 / 40 | Supported |
| total_break | Cutter | Medium-No | -2.16 [-2.73, -1.59] | – | 26 / 33 | info |
| SpeedDrop | Cutter | Extreme-No | -0.977 [-1.07, -0.884] | +0.617 [+0.566, +0.66] | 33 / 40 | Supported |
| SpeedDrop | Cutter | Medium-No | -0.612 [-0.702, -0.53] | – | 26 / 33 | info |
| InducedVertBreak | Cutter | Extreme-No | -2.84 [-3.46, -2.28] | +1.73 [+1.27, +2.16] | 33 / 40 | info |
| InducedVertBreak | Cutter | Medium-No | -2.02 [-2.6, -1.48] | – | 26 / 33 | info |
| abs_ivb | Slider | Extreme-No | -1.01 [-1.2, -0.841] | +0.656 [+0.529, +0.795] | 320 / 472 | Supported |
| abs_ivb | Slider | Medium-No | -0.689 [-0.852, -0.541] | – | 269 / 374 | info |
| abs_hb | Slider | Extreme-No | -1.79 [-1.98, -1.6] | +1.08 [+0.941, +1.21] | 320 / 472 | Supported |
| abs_hb | Slider | Medium-No | -1.24 [-1.45, -1.03] | – | 269 / 374 | info |
| total_break | Slider | Extreme-No | -2.27 [-2.48, -2.07] | +1.41 [+1.26, +1.56] | 320 / 472 | Supported |
| total_break | Slider | Medium-No | -1.61 [-1.8, -1.42] | – | 269 / 374 | info |
| SpeedDrop | Slider | Extreme-No | -0.821 [-0.857, -0.784] | +0.511 [+0.49, +0.53] | 320 / 472 | Supported |
| SpeedDrop | Slider | Medium-No | -0.504 [-0.54, -0.468] | – | 269 / 374 | info |
| InducedVertBreak | Slider | Extreme-No | -1.07 [-1.28, -0.871] | +0.743 [+0.599, +0.893] | 320 / 472 | info |
| InducedVertBreak | Slider | Medium-No | -0.877 [-1.05, -0.7] | – | 269 / 374 | info |
| abs_ivb | Curveball | Extreme-No | -2.01 [-2.29, -1.73] | +1.18 [+0.94, +1.41] | 100 / 123 | Supported |
| abs_ivb | Curveball | Medium-No | -1.16 [-1.53, -0.834] | – | 87 / 101 | info |
| abs_hb | Curveball | Extreme-No | -3.37 [-3.71, -3.03] | +2.01 [+1.74, +2.27] | 100 / 123 | Supported |
| abs_hb | Curveball | Medium-No | -2.01 [-2.36, -1.65] | – | 87 / 101 | info |
| total_break | Curveball | Extreme-No | -4.06 [-4.39, -3.73] | +2.43 [+2.15, +2.68] | 100 / 123 | Supported |
| total_break | Curveball | Medium-No | -2.4 [-2.83, -1.97] | – | 87 / 101 | info |
| SpeedDrop | Curveball | Extreme-No | -0.97 [-1.03, -0.91] | +0.601 [+0.555, +0.647] | 100 / 123 | Supported |
| SpeedDrop | Curveball | Medium-No | -0.607 [-0.683, -0.533] | – | 87 / 101 | info |
| InducedVertBreak | Curveball | Extreme-No | +1.73 [+1.2, +2.26] | -1.03 [-1.5, -0.581] | 100 / 123 | info |
| InducedVertBreak | Curveball | Medium-No | +1.46 [+0.944, +2.02] | – | 87 / 101 | info |
| abs_ivb | Changeup | Extreme-No | -1.67 [-1.95, -1.41] | +1.06 [+0.864, +1.27] | 175 / 253 | Supported |
| abs_ivb | Changeup | Medium-No | -1.28 [-1.56, -1] | – | 148 / 202 | info |
| abs_hb | Changeup | Extreme-No | -4.11 [-4.37, -3.81] | +2.43 [+2.24, +2.61] | 175 / 253 | Supported |
| abs_hb | Changeup | Medium-No | -3 [-3.27, -2.75] | – | 148 / 202 | info |
| total_break | Changeup | Extreme-No | -4.47 [-4.71, -4.21] | +2.69 [+2.53, +2.84] | 175 / 253 | Supported |
| total_break | Changeup | Medium-No | -3.28 [-3.55, -3.02] | – | 148 / 202 | info |
| SpeedDrop | Changeup | Extreme-No | -0.993 [-1.05, -0.945] | +0.585 [+0.553, +0.621] | 175 / 253 | Supported |
| SpeedDrop | Changeup | Medium-No | -0.653 [-0.705, -0.604] | – | 148 / 202 | info |
| InducedVertBreak | Changeup | Extreme-No | -1.61 [-1.92, -1.32] | +1.02 [+0.805, +1.27] | 175 / 253 | info |
| InducedVertBreak | Changeup | Medium-No | -1.22 [-1.58, -0.859] | – | 148 / 202 | info |
| abs_ivb | Splitter | Extreme-No | -1.01 [-1.75, -0.248] | +0.638 [+0.423, +1.63] | 9 / 13 | Supported |
| abs_ivb | Splitter | Medium-No | -0.802 [-2.05, -0.363] | – | 5 / 8 | info |
| abs_hb | Splitter | Extreme-No | -3.31 [-3.79, -2.05] | +2.31 [+1.37, +2.72] | 9 / 13 | Supported |
| abs_hb | Splitter | Medium-No | -2.18 [-2.91, -0.942] | – | 5 / 8 | info |
| total_break | Splitter | Extreme-No | -3.45 [-3.8, -2.34] | +2.42 [+1.88, +2.76] | 9 / 13 | Supported |
| total_break | Splitter | Medium-No | -2.44 [-3.68, -1.3] | – | 5 / 8 | info |
| SpeedDrop | Splitter | Extreme-No | -0.858 [-0.973, -0.604] | +0.543 [+0.517, +0.656] | 9 / 13 | Supported |
| SpeedDrop | Splitter | Medium-No | -0.453 [-0.671, -0.37] | – | 5 / 8 | info |
| InducedVertBreak | Splitter | Extreme-No | +0.416 [-1.67, +1.23] | +0.299 [-0.237, +2.33] | 9 / 13 | info |
| InducedVertBreak | Splitter | Medium-No | -0.681 [-2.79, +0.315] | – | 5 / 8 | info |

## H2 · Los lanzamientos de diferencial de velocidad (CH/SPL) se degradan más que los rompientes (SL/CB)

**Veredicto global: Rejected**

No hay evidencia de que CH/SPL se degraden más que SL/CB: los IC de la diferencia de diferencias incluyen 0 (whiff, chase y xRV). El mecanismo sí está: el changeup pierde fade y quiebre total, pero los rompientes también pierden. Con tan pocos splitters, esta hipótesis tiene poca potencia para CH/SPL por separado.

| Métrica | Familia | Contraste | Δ [IC 95 %] | Pendiente por +0.1 ρ̂ [IC] | Pitchers / claves | Veredicto |
|---|---|---|---|---|---|---|
| t_whiff | CH+SPL minus SL+CB | DiD Extreme-No | +0.0251 [-0.0211, +0.0731] | – | 42 / 48 | Rejected |
| t_whiff | CH+SPL | Extreme-No (info) | -0.0169 [-0.034, -7.41e-05] | +0.0168 [+0.00709, +0.028] | 48 / 62 | info |
| t_whiff | SL+CB | Extreme-No (info) | -0.0225 [-0.0395, -0.00608] | +0.0066 [-0.00923, +0.0258] | 113 / 133 | info |
| t_chase | CH+SPL minus SL+CB | DiD Extreme-No | -0.0271 [-0.0658, +0.00878] | – | 73 / 83 | Rejected |
| t_chase | CH+SPL | Extreme-No (info) | -0.0165 [-0.0328, -0.00193] | +0.00529 [-0.0043, +0.0175] | 78 / 97 | info |
| t_chase | SL+CB | Extreme-No (info) | +0.0049 [-0.0065, +0.0153] | +0.000322 [-0.00863, +0.00974] | 189 / 232 | info |
| rv_x | CH+SPL minus SL+CB | DiD Extreme-No | -0.00886 [-0.018, +0.000551] | – | 110 / 132 | Rejected |
| rv_x | CH+SPL | Extreme-No (info) | +0.0126 [+0.00806, +0.0171] | -0.00854 [-0.0117, -0.00591] | 141 / 176 | info |
| rv_x | SL+CB | Extreme-No (info) | +0.011 [+0.00775, +0.0142] | -0.00619 [-0.00846, -0.00401] | 307 / 390 | info |
| abs_hb | Changeup | Extreme-No (mecanismo, info) | -4.11 [-4.37, -3.81] | +2.43 [+2.24, +2.61] | 175 / 253 | info |
| total_break | Changeup | Extreme-No (mecanismo, info) | -4.47 [-4.71, -4.21] | +2.69 [+2.53, +2.84] | 175 / 253 | info |

## H3 · Los rodados protegen: Δ HR/FB, distancia y xRV; moderación por GB% a nivel del mar

**Veredicto global: Partially**

Las bolas al aire sí se vuelven más peligrosas en altura (HR/FB, distancia, xRV) y más que los rodados. Pero no hay evidencia de que los pitchers de más rodados *se protejan* más: la pendiente de Δ xRV contra GB% a nivel del mar incluye 0.

| Métrica | Familia | Contraste | Δ [IC 95 %] | Pendiente por +0.1 ρ̂ [IC] | Pitchers / claves | Veredicto |
|---|---|---|---|---|---|---|
| hr_fb | todos | Extreme-No (pitcher-temporada) | +0.0232 [+0.0123, +0.0337] | -0.0114 [-0.0251, +0.00189] | 129 / 154 | Partially |
| fb_distance | todos | Extreme-No (pitcher-temporada) | +36.1 [+30.9, +41.2] | -22.1 [-29.7, -9.65] | 55 / 61 | Supported |
| rv_fb | todos | Extreme-No (pitcher-temporada) | +0.0663 [+0.0513, +0.0814] | -0.037 [-0.0557, -0.0196] | 129 / 154 | info |
| rv_gb | todos | Extreme-No (pitcher-temporada) | +0.0153 [+0.00746, +0.0229] | -0.0144 [-0.0223, -0.00601] | 189 / 225 | info |
| rv_bip | todos | Extreme-No (pitcher-temporada) | +0.0457 [+0.0372, +0.0545] | -0.0273 [-0.0343, -0.0201] | 367 / 477 | info |
| rv_x fly ball − rv_x rodado | FB − GB | DiD Extreme-No (pitcher-temporada) | +0.0505 [+0.0327, +0.0673] | – | 101 / 121 | Supported |
| Δ rv_x por bola en juego vs GB% (por +10 pp) | todos | pendiente (Extreme-No) | +0.00378 [-0.00752, +0.0157] | – | 134 / 158 | Rejected |
| Δ HR/FB vs GB% (por +10 pp) | todos | pendiente (Extreme-No) | +0.0121 [-6.94e-05, +0.024] | – | 110 / 132 | info |

## H4 · El giro solo explica peor la efectividad en altura que movimiento + eficiencia de giro

**Veredicto global: Rejected**

Contraria a lo predicho: el movimiento aporta *menos* sobre SpinRate en altura (la ganancia de AUC baja) y SpinRate explica *más* del IVB entre pitchers en Extreme. Ver advertencias sobre SpinRate y spin_eff antes de interpretar.

| Métrica | Familia | Contraste | Δ [IC 95 %] | Pendiente por +0.1 ρ̂ [IC] | Pitchers / claves | Veredicto |
|---|---|---|---|---|---|---|
| DiD ΔAUC(movimiento+spin_eff − SpinRate) Extreme-No | todas (whiff|swing) | OOF por pitcher | -0.00973 [-0.0144, -0.0055] | – | 924 / 292995 | Rejected (opposite) |
| R² (IVB ~ SpinRate+RelSpeed) Extreme-No | Four-Seam | R² por ambiente | +0.107 [+0.0545, +0.163] | – | 679 / 237604 | Rejected (opposite) |

### H4 · AUC fuera de muestra (whiff | swing, validación cruzada por pitcher)

| env | AUC SpinRate | AUC movimiento+spin_eff | ganancia | swings |
|---|---|---|---|---|
| No Altitude | 0.6039 | 0.6278 | +0.0239 | 137345 |
| Medium Altitude | 0.6100 | 0.6266 | +0.0166 | 71853 |
| Extreme Altitude | 0.6146 | 0.6287 | +0.0141 | 83797 |

## Advertencias

- La eficiencia de giro usa ρ̂ por juego; queda una brecha de ~15 % entre No y Extreme sin explicar (Cl cae más que Cd, HACK-004): H4 no debe leerse como evidencia sobre spin_eff en sí.
- `SpinRate` sube ~+17 rpm dentro del mismo lanzamiento en Extreme (medición o efecto real); por eso no entra en `pitch_id` (HACK-029).
- `rv_x` valora las bolas en juego con altitud como rasgo (HACK-030): parte de su diferencia por altitud está en el modelo; HR/FB y distancia crudos son la evidencia primaria de H3.
- Identidad de CDMX vs Puebla sin verificar (HACK-003); los parques se agrupan por franquicia inferida.
- Los IC propagan solo el muestreo de pitchers, no la incertidumbre de ρ̂ ni de la identidad de lanzamiento.