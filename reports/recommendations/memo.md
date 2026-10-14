# Recomendaciones operativas: jugar en el Harp Helú (2,240 m)

*Memo para el cuerpo técnico y la gerencia de Diablos Rojos. Escala Stuff+: 100 = promedio de la LMB a nivel del mar; ΔStuff+ = Stuff+ en el aire del Harp Helú menos Stuff+ a nivel del mar, con intervalos al 95 % por pitcher. Cada cifra sale de un CSV de `reports/` (entre paréntesis) y este texto se regenera con `reports/recommendations/build_memo.py`.*

**En una frase:** el aire del Harp Helú le quita a la liga unos 10.3 puntos de Stuff+ por lanzamiento (promedio de formas); conviene reclutar formas que pierden poco (sweeper, 12-6 CB, slider) y no pagar por *ride* de recta.

## 1. Perfiles que ganan en la CDMX (pierden menos que la liga)

El promedio de la liga cae -10.3 puntos (`altitude_delta/delta_by_shape.csv`). Las tres formas que mejor aguantan:

- **sweeper** (-4.6 [-5.4, -3.9]): +5.6 puntos mejor que la liga. Movimiento en altura: IVB +0.6", HB +2.1", whiff -1.5 pp. 462 pitchers, 25,133 lanzamientos.
- **12-6 CB** (-6.1 [-6.9, -5.4]): +4.1 puntos mejor que la liga. Movimiento en altura: IVB +1.4", HB +0.9", whiff -0.0 pp. 271 pitchers, 11,741 lanzamientos.
- **slider** (-7.2 [-7.7, -6.8]): +3.0 puntos mejor que la liga. Movimiento en altura: IVB -0.4", HB +1.1", whiff -1.7 pp. 605 pitchers, 28,184 lanzamientos.

**Física:** la fuerza de Magnus y el arrastre son proporcionales a la densidad del aire; con ~16 % menos aire (ρ̂ Extreme ≈ 0.84, `physics/rho_by_bucket.csv`; Harp Helú ≈ 0.82, `park_id/harp_helu.md`) el quiebre inducido baja en esa proporción. Por eso el Stuff+ de una recta depende mucho menos de su IVB en altura (punto 1 de la lista de verificación), y las formas que no viven del *ride* aguantan mejor.

## 2. Perfiles que pierden y riesgo de contacto duro y jonrones

Las tres formas que más pierden:

- **riding 4S** (-16.0 [-16.3, -15.6]): -5.7 puntos contra la liga. Contacto duro +0.7 pp, HR/FB +3.4 pp, valor del contacto +0.065 carreras por bola en juego.
- **power CH** (-12.7 [-13.6, -11.7]): -2.4 puntos contra la liga. Contacto duro +1.4 pp, HR/FB +1.8 pp, valor del contacto +0.042 carreras por bola en juego.
- **changeup** (-11.4 [-12.1, -10.7]): -1.1 puntos contra la liga. Contacto duro +1.5 pp, HR/FB +3.1 pp, valor del contacto +0.045 carreras por bola en juego.

**Riesgo cuantificado (hipótesis H3, `hypotheses/results.csv`):** las bolas al aire viajan +36 pies más [31, 41] y el HR/FB sube +2.3 pp [1.2, 3.4]; una bola al aire vale +0.050 carreras más que un rodado [0.033, 0.067] en altura. **No** hay evidencia de que los pitchers de más rodados se protejan más (pendiente contra GB% con IC que incluye 0): no se debe recomendar fichar rodadores solo por eso.

## 3. Cómo perfilar un prospecto o agente libre (lista de verificación)

Umbrales sacados de los quintiles observados (`ideal_profile/delta_by_trait.csv`) y de la sensibilidad al aire (`ideal_profile/rho_sensitivity.csv`):

1. **No pagar por *ride* de recta.** El rango de Stuff+ entre IVB bajo y alto es +20.9 puntos a nivel del mar y solo +7.6 en el Harp Helú; la recta de más *ride* es la que más pierde (riding 4S -16.0).
2. **Extensión alta.** Quintil superior (≥ 6.43 ft): ΔStuff+ -9.7; quintil inferior (≤ 5.58 ft): -12.8 (la extensión pesa más en altura: rango +2.2 → +4.9).
3. **Ángulo de aproximación (VAA) bajo, neto de la altura del lanzamiento.** Quintil inferior: -9.1; superior: -13.1.
4. **Velocidad: suma más en altura** (rango +8.4 → +9.4 puntos).
5. **Secundarios:** preferir sweeper, 12-6 CB, slider; desconfiar de power CH, changeup.
6. **Perfil de referencia de recta** en el aire del Harp Helú (`ideal_profile/best_fastballs.csv`): 90.7 mph, IVB 16.3" y HB 6.6" a nivel del mar, extensión 6.25 ft, salida 6.14 ft → Stuff+ 108.2 en el Harp Helú (115.5 a nivel del mar).

*Límite:* la eficiencia de giro no se usa como criterio: la brecha de ~15 % entre altitudes sigue sin explicarse (`physics/README.md`).

## 4. Tácticas en casa frente a gira

Efecto del aire por zona del plato, en carreras por lanzamiento (+ = peor para el pitcher; `location_model/altitude_by_zone.csv`, basado en el modelo y con ρ a nivel de juego):

- **El centro cuesta más:** recta zona 4 +0.027 y zona 5 +0.025; slider zona 4 +0.025. Evitar el medio de la zona en casa.
- **Abajo pierde más que arriba:** recta zonas 7–8 (+0.018, +0.021) frente a zonas 1–3 (+0.012 a +0.014).
- **El borde fuera de la zona casi no cambia** (recta -0.0007, slider +0.0035): en casa conviene buscar el *chase* en lugar de pelear la zona.
- **La esquina baja del lado del guante (zona 9) aguanta mejor** (recta +0.006, slider +0.010).

*Pendiente:* secuencias y conteos de Diablos en casa contra gira dependen de la auditoría del staff (HACK-032), todavía no integrada; este memo no las inventa.

## 5. Valor en carreras y victorias

- **Carreras por victoria:** liga 11.8; Harp Helú (bucket Extreme) 14.3 (`business_value/runs_per_win.csv`). En altura se anota más, así que cada carrera ahorrada vale menos victorias.
- **Un punto de Stuff+ vale 7.24e-04 carreras por lanzamiento** [6.78e-04, 7.69e-04] (estimación directa fuera de muestra, `business_value/runs_per_point_direct.csv`).
- **Ejemplo:** +10 puntos de Stuff+ en 2,500 lanzamientos son 18.1 carreras ≈ **1.26 victorias** en el Harp Helú (`business_value/gm_example.csv`). Una desviación estándar entre pitcher-temporadas (5.4 puntos) equivale a 9.9 carreras ≈ 0.69 victorias (`business_value/pitcher_spread_example.csv`).
- **Costo medio de la altura:** +0.0116 carreras por lanzamiento (Extreme frente a sin altitud, `business_value/altitude_cost.csv`): ~0.9 carreras por apertura de 77 lanzamientos.
- **Orden de magnitud de la decisión de reclutamiento:** la diferencia de pérdida entre riding 4S y sweeper es 11.4 puntos; por cada 1,000 lanzamientos son ~8.2 carreras (~0.57 victorias en el Harp Helú). Es una diferencia de pérdida entre formas, no el efecto causal de cambiar un lanzamiento por otro.

## Cómo leer estas cifras

- Estimaciones con datos de la LMB 2024–2026; los intervalos solo propagan el muestreo de pitchers, no la incertidumbre de ρ̂ ni de la identidad de lanzamiento.
- La identidad de CDMX frente a Puebla entre los parques de altura no está verificada (HACK-003): «Harp Helú» usa ρ̂ = 0.82 de las dos franquicias de menor densidad.
- Estas son estimaciones de modelo y de datos observacionales; no son un experimento. El rango por pitcher individual es ruidoso: usar para decisiones de perfil, no de un solo lanzador.
