# Física del vuelo a 2,240 m (HACK-004)

**Idea.** La pelota siente una fuerza de arrastre y una de Magnus, ambas proporcionales a la densidad del aire ρ:
`a_drag = ½ρA·Cd·v²/m`, `a_magnus = ½ρA·Cl·v²/m`. Con ρ menor, Harp Helú recibe menos frenado (la recta llega más rápido) y menos curvatura inducida (menos IVB).

**Cómo se mide** (`stuffplus/physics/aero.py`, ajuste de 9 parámetros x0…az0 de Trackman):
- drag = −a·v̂ (gravedad retirada), Magnus = componente ⊥ v; `Cd-proxy = drag/v²`, `Cl-proxy = Magnus/v²`.
- Eficiencia de giro (Nathan): `Cl = 1/(2.32+0.4/S)` → S → giro transversal implicado / `SpinRate`.
- ρ̂ por juego = mediana de Cd-proxy de rectas ÷ la de juegos sin altitud (=1.0). Juegos con < 30 rectas se encogen al promedio de su bucket.

**Resultados** (`analysis/physics/run.py`, 627 k lanzamientos limpios):

| Bucket | ρ̂ medio | sd juego |
|---|---|---|
| No Altitude | 1.001 | 0.044 |
| Medium | 0.892 | 0.042 |
| Extreme | 0.841 | 0.033 |

Δ Extreme − No (modelo de efectos fijos por pitcher×temporada×pitch_id; el efecto de ρ es **proporcional al movimiento propio** del lanzamiento, Magnus y arrastre ∝ ρ; IC bootstrap 95 % por pitcher-temporada): recta **ΔIVB −3.94" [−4.00, −3.84]**, ΔHB −1.28", **llega +1.30 mph más rápida** (referencia exploratoria −3.7" y −1.36 mph). La curva *pierde caída* (ΔIVB +1.75" [+1.57, +1.93], signo contrario a la recta) y un ride mayor cambia más que uno menor. Otras familias en `delta_extreme_vs_no.csv`.

**Advertencias honestas.**
- La eficiencia de giro usa ρ̂ de cada juego (antes se usaba nivel del mar para todos: 0.62 en No Altitude vs 0.40 en Extreme, artefacto del aire). Ahora 0.61 vs 0.52; el residuo (~15 %) viene del punto de abajo.
- Validación Cl/Cd **parcial**: Cd-proxy cae 16 % en Extreme pero Cl-proxy cae 24 % (`validation_cl_cd.csv`). Si ambos fueran ∝ ρ la razón sería constante; baja ~9 %. No descarta un artefacto de calibración de Trackman por parque, ni un efecto real de Reynolds/giro. Los Δ de movimiento se estiman empíricamente, no del modelo Cl teórico.
- Los IC solo propagan incertidumbre del coeficiente de ρ, no la de Δρ ni de la identidad de lanzamiento.
- `RHO_HARP_HELU` = 0.819 (ρ̂ agrupado de HACK-003, IC95 % 0.814–0.824; identidad CDMX vs Puebla sin verificar); el barométrico en la misma escala da ≈0.79. HACK-003 debe sustituirlo por el estimador agrupado.
