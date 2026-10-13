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

Δ Extreme − No para la recta (efectos fijos por pitcher×temporada×pitch_id, IC bootstrap 95 % por pitcher-temporada): **ΔIVB −3.51" [−3.57, −3.43]**, ΔHB −1.23", **la recta llega +1.30 mph más rápida** (speed drop −1.30; referencia exploratoria −3.7" y −1.36 mph). Otras familias en `delta_extreme_vs_no.csv`.

**Advertencias honestas.**
- Validación Cl/Cd **parcial**: Cd-proxy cae 16 % en Extreme pero Cl-proxy cae 24 % (`validation_cl_cd.csv`). Si ambos fueran ∝ ρ la razón sería constante; baja ~9 %. No descarta un artefacto de calibración de Trackman por parque, ni un efecto real de Reynolds/giro. Los Δ de movimiento se estiman empíricamente, no del modelo Cl teórico.
- Los IC solo propagan incertidumbre del coeficiente de ρ, no la de Δρ ni de la identidad de lanzamiento.
- `RHO_HARP_HELU` sigue en el valor barométrico (≈0.75, ISA 2,240 m, 20 °C) hasta que HACK-003 entregue el empírico; el ρ̂ de arriba es relativo a juegos de tierras bajas, no a ISA.
