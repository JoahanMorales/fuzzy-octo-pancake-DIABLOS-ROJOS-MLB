# Recomendaciones operativas: jugar en el Harp Helú (2,240 m)

*Memo para el cuerpo técnico y la gerencia de Diablos Rojos. Escala Stuff+: 100 = promedio de la LMB a nivel del mar; ΔStuff+ = Stuff+ en el aire del Harp Helú menos Stuff+ a nivel del mar, con intervalos al 95 % por pitcher. Cada cifra sale de un CSV de `reports/` (entre paréntesis) y este texto se regenera con `reports/recommendations/build_memo.py`.*

**En una frase:** el aire del Harp Helú le quita a la liga unos 13.0 puntos de Stuff+ por lanzamiento (promedio de formas); conviene reclutar formas que pierden poco (12-6 CB, sweeper, splitter) y no pagar por *ride* de recta.

## 1. Perfiles que ganan en la CDMX (pierden menos que la liga)

El promedio de la liga cae -13.0 puntos (`altitude_delta/delta_by_shape.csv`). Las tres formas que mejor aguantan:

- **12-6 CB** (-9.5 [-10.1, -8.9]): +3.5 puntos mejor que la liga. Movimiento en altura: IVB +1.4", HB +0.9", whiff +0.0 pp. 271 pitchers, 11,741 lanzamientos.
- **sweeper** (-9.6 [-10.2, -9.1]): +3.4 puntos mejor que la liga. Movimiento en altura: IVB +0.6", HB +2.1", whiff -1.4 pp. 462 pitchers, 25,133 lanzamientos.
- **splitter** (-10.3 [-12.8, -8.4]): +2.7 puntos mejor que la liga. Movimiento en altura: IVB +0.7", HB -1.5", whiff -0.7 pp. 17 pitchers, 3,928 lanzamientos.

**Física:** la fuerza de Magnus y el arrastre son proporcionales a la densidad del aire; con ~16 % menos aire (ρ̂ Extreme ≈ 0.84, `physics/rho_by_bucket.csv`; Harp Helú ≈ 0.82, `park_id/harp_helu.md`) el quiebre inducido baja en esa proporción. Por eso el Stuff+ de una recta depende mucho menos de su IVB en altura (punto 1 de la lista de verificación), y las formas que no viven del *ride* aguantan mejor.

## 2. Perfiles que pierden y riesgo de contacto duro y jonrones

Las tres formas que más pierden:

- **riding 4S** (-17.9 [-18.3, -17.4]): -4.9 puntos contra la liga. Contacto duro +0.7 pp, HR/FB +3.4 pp, valor del contacto +0.074 carreras por bola en juego.
- **power CH** (-15.6 [-16.6, -14.4]): -2.6 puntos contra la liga. Contacto duro +1.4 pp, HR/FB +1.8 pp, valor del contacto +0.052 carreras por bola en juego.
- **11-5 CB** (-14.8 [-15.6, -14.0]): -1.8 puntos contra la liga. Contacto duro +1.9 pp, HR/FB +3.6 pp, valor del contacto +0.055 carreras por bola en juego.

**Riesgo cuantificado (hipótesis H3, `hypotheses/results.csv`):** las bolas al aire viajan +36 pies más [31, 41] y el HR/FB sube +2.3 pp [1.2, 3.4]; una bola al aire vale +0.050 carreras más que un rodado [0.033, 0.067] en altura. **No** hay evidencia de que los pitchers de más rodados se protejan más (pendiente contra GB% con IC que incluye 0): no se debe recomendar fichar rodadores solo por eso.

## 3. Cómo perfilar un prospecto o agente libre (lista de verificación)

Umbrales sacados de los quintiles observados (`ideal_profile/delta_by_trait.csv`) y de la sensibilidad al aire (`ideal_profile/rho_sensitivity.csv`):

1. **No pagar por *ride* de recta.** El rango de Stuff+ entre IVB bajo y alto es +21.1 puntos a nivel del mar y solo +5.8 en el Harp Helú; la recta de más *ride* es la que más pierde (riding 4S -17.9).
2. **Extensión alta.** Quintil superior (≥ 6.43 ft): ΔStuff+ -11.0; quintil inferior (≤ 5.58 ft): -15.3 (la extensión pesa más en altura: rango +1.5 → +5.4).
3. **Ángulo de aproximación (VAA) bajo, neto de la altura del lanzamiento.** Quintil inferior: -12.4; superior: -14.1.
4. **Velocidad: sin umbral.** El efecto no es robusto: el rango de Stuff+ por velocidad pasa de +8.8 (mar) a +10.9 en el Harp Helú con el efecto total, pero a +7.7 con solo la física (`rho_sensitivity.csv`), y los quintiles de ΔStuff+ no son monótonos (-13.4, -13.2, -13.8, -13.5, -13.3; `delta_by_trait.csv`).
5. **Secundarios:** preferir 12-6 CB, sweeper, splitter; desconfiar de power CH, 11-5 CB.
6. **Perfil de referencia de recta** en el aire del Harp Helú (`ideal_profile/best_fastballs.csv`): 91.4 mph, IVB 14.4" y HB 4.4" a nivel del mar, extensión 6.48 ft, salida 5.84 ft → Stuff+ 106.7 en el Harp Helú (105.3 a nivel del mar).

*Límite:* la eficiencia de giro no se usa como criterio: la brecha de ~15 % entre altitudes sigue sin explicarse (`physics/README.md`).

## 4. Tácticas en casa frente a gira (hipótesis basadas en el modelo)

Efecto del aire por zona del plato, en carreras por lanzamiento (+ = peor para el pitcher; `location_model/altitude_by_zone.csv`). Es el modelo de ubicación (Location+) con ρ a nivel de juego: son **hipótesis para probar**, no un experimento. Zonas 1–9 = filas de arriba a abajo y columnas del lado del brazo al del guante (`stuffplus/models/location.py`, `zone_label`).

- **El centro cuesta más:** recta zona 4 +0.027 y zona 5 +0.025; slider zona 4 +0.025 y zona 3 +0.025. Evitar el medio de la zona en casa.
- **Recta: abajo pierde más que arriba** (zonas 7–8: +0.018, +0.021; zonas 1–3: +0.012 a +0.014). No se generaliza al slider (zonas 7–8: +0.018, +0.017; zonas 1–3: +0.014 a +0.025).
- **Borde fuera de la zona:** el *cambio* por la altura es casi nulo (recta -0.0007, slider +0.0035), pero su valor absoluto sigue siendo el peor de todas las regiones (recta +0.040 en el Harp Helú): la altura no lo empeora, y eso no basta para recomendar buscarlo.
- **Zona 9 (abajo, lado del guante) aguanta mejor el cambio** (recta +0.006, slider +0.010).

*Pendiente (aceptación incompleta):* secuencias y conteos de Diablos en casa contra gira dependen de la auditoría del staff (HACK-032), todavía no integrada; este memo no las inventa.

## 5. Valor en carreras y victorias

- **Carreras por victoria:** liga 11.8; Harp Helú (bucket Extreme) 14.3 (`business_value/runs_per_win.csv`). En altura se anota más, así que cada carrera ahorrada vale menos victorias.
- **Un punto de Stuff+ vale 8.67e-04 carreras por lanzamiento** [8.18e-04, 9.19e-04] (estimación directa fuera de muestra, `business_value/runs_per_point_direct.csv`).
- **Ejemplo:** +10 puntos de Stuff+ en 2,500 lanzamientos son 21.7 carreras ≈ **1.51 victorias** en el Harp Helú (`business_value/gm_example.csv`). Una desviación estándar *observada* entre pitcher-temporadas, que incluye ruido de muestreo (5.1 puntos) equivale a 11.0 carreras ≈ 0.77 victorias (`business_value/pitcher_spread_example.csv`).
- **Costo medio de la altura:** +0.0116 carreras por lanzamiento (Extreme frente a sin altitud, `business_value/altitude_cost.csv`): ~0.9 carreras por apertura de 77 lanzamientos.
- **Orden de magnitud de la decisión de reclutamiento:** la diferencia de pérdida entre riding 4S y sweeper es 8.3 puntos; por cada 1,000 lanzamientos son ~7.2 carreras (~0.50 victorias en el Harp Helú). Es una diferencia de pérdida entre formas, no el efecto causal de cambiar un lanzamiento por otro.

## Cómo leer estas cifras

- Estimaciones con datos de la LMB 2024–2026; los intervalos solo propagan el muestreo de pitchers, no la incertidumbre de ρ̂ ni de la identidad de lanzamiento.
- La identidad de CDMX frente a Puebla entre los parques de altura no está verificada (HACK-003): «Harp Helú» usa ρ̂ = 0.82 de las dos franquicias de menor densidad.
- Estas son estimaciones de modelo y de datos observacionales; no son un experimento. El rango por pitcher individual es ruidoso: usar para decisiones de perfil, no de un solo lanzador.
