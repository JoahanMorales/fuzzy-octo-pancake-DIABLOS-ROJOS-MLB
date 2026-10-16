# Física v2: coeficientes, brecha de sustentación y vuelo RK4 (HACK-041)

Generado por `python -m analysis.physics_v2.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.

Del ajuste de 9 parámetros de cada lanzamiento salen el arrastre y la fuerza de Magnus; con la densidad de cada juego se convierten en C_D y C_L. El parámetro de giro es S = Rω/v (Nathan et al. 2006) y el número de Reynolds Re = ρvD/μ (Smith y Sciacchitano 2022). La densidad por juego se calibra con el arrastre de las rectas (Kagan y Nathan 2014), así que el C_D de las rectas es casi igual en todos los parques por construcción.

## Coeficientes por bucket (`coefficients_by_bucket.csv`, medianas)

| Familia | Bucket | ρ̂ | C_D | C_L [IC 95 %] | S | Re (miles) |
|---|---|---|---|---|---|---|
| Changeup | Extreme Altitude | 0.841 | 0.294 | 0.120 [0.115, 0.126] | 0.215 | 155 |
| Changeup | Medium Altitude | 0.885 | 0.292 | 0.125 [0.120, 0.131] | 0.218 | 164 |
| Changeup | No Altitude | 1.004 | 0.287 | 0.150 [0.146, 0.155] | 0.206 | 184 |
| Curveball | Extreme Altitude | 0.837 | 0.300 | 0.122 [0.111, 0.129] | 0.282 | 146 |
| Curveball | Medium Altitude | 0.891 | 0.295 | 0.122 [0.115, 0.129] | 0.273 | 157 |
| Curveball | No Altitude | 1.002 | 0.292 | 0.132 [0.121, 0.141] | 0.286 | 173 |
| Cutter | Extreme Altitude | 0.830 | 0.283 | 0.107 [0.096, 0.119] | 0.234 | 163 |
| Cutter | Medium Altitude | 0.887 | 0.279 | 0.104 [0.095, 0.116] | 0.239 | 173 |
| Cutter | No Altitude | 0.991 | 0.271 | 0.114 [0.101, 0.127] | 0.239 | 194 |
| Four-Seam | Extreme Altitude | 0.838 | 0.291 | 0.174 [0.172, 0.177] | 0.220 | 170 |
| Four-Seam | Medium Altitude | 0.887 | 0.292 | 0.176 [0.173, 0.179] | 0.222 | 180 |
| Four-Seam | No Altitude | 1.000 | 0.292 | 0.192 [0.190, 0.194] | 0.221 | 202 |
| Sinker | Extreme Altitude | 0.838 | 0.293 | 0.167 [0.163, 0.171] | 0.218 | 170 |
| Sinker | Medium Altitude | 0.888 | 0.292 | 0.167 [0.164, 0.170] | 0.217 | 179 |
| Sinker | No Altitude | 1.001 | 0.292 | 0.183 [0.179, 0.186] | 0.216 | 201 |
| Slider | Extreme Altitude | 0.838 | 0.295 | 0.077 [0.074, 0.080] | 0.250 | 156 |
| Slider | Medium Altitude | 0.891 | 0.290 | 0.082 [0.077, 0.087] | 0.252 | 166 |
| Slider | No Altitude | 1.002 | 0.279 | 0.083 [0.079, 0.086] | 0.251 | 185 |
| Splitter | Extreme Altitude | 0.842 | 0.312 | 0.085 [0.079, 0.093] | 0.119 | 155 |
| Splitter | Medium Altitude | 0.902 | 0.309 | 0.084 [0.071, 0.092] | 0.126 | 165 |
| Splitter | No Altitude | 0.980 | 0.301 | 0.101 [0.088, 0.109] | 0.118 | 180 |

## ¿Por qué cae la sustentación en altura? (`lift_gap.csv`)

El C_L de la recta baja 9.1 % en altitud extrema. Lo separamos en tres partes:

- **Parámetro de giro:** S casi no cambia (0.221 contra 0.220); con la pendiente medida de C_L contra S (0.019) explica -0.0 %. **La hipótesis de la literatura (menor S en altura) no explica la brecha en estos datos.**
- **Sesgo de densidad:** si la densidad real del Harp Helú es la barométrica (0.787) y no la calibrada con el arrastre (0.819), el C_L calculado sale bajo por -3.9 %. Eso implica que el C_D sube en aire más delgado (menor Reynolds); lo apoya que en los lanzamientos lentos (menor Re) el C_D sí sube en altitud (tabla de arriba).
- **Residuo sin explicar:** -5.4 %: puede ser un efecto real del régimen de Reynolds sobre C_L o calibración de Trackman por parque; se reporta como hipótesis.

| Familia | Brecha de C_L | Por parámetro de giro | Por sesgo de densidad | Residuo |
|---|---|---|---|---|
| Changeup | -19.8 % | +0.1 % | -3.9 % | -16.7 % |
| Curveball | -7.8 % | -0.1 % | -3.9 % | -4.1 % |
| Cutter | -6.2 % | -0.1 % | -3.9 % | -2.4 % |
| Four-Seam | -9.1 % | -0.0 % | -3.9 % | -5.4 % |
| Sinker | -8.6 % | +0.0 % | -3.9 % | -5.0 % |
| Slider | -6.7 % | -0.0 % | -3.9 % | -3.0 % |
| Splitter | -15.1 % | +0.0 % | -3.9 % | -11.7 % |

## Elasticidad del Magnus contra la densidad (`magnus_elasticity.csv`)

Dentro del mismo lanzamiento (pitcher × temporada × identidad) y entre juegos: pendiente de log(aceleración de Magnus) contra log(ρ̂). Con C_L constante la física predice 1.

| Familia | Elasticidad [IC 95 %] | Lanzamientos-juego |
|---|---|---|
| Changeup | 1.76 [1.68, 1.86] | 8,249 |
| Curveball | 1.38 [1.28, 1.49] | 5,808 |
| Cutter | 1.47 [1.26, 1.72] | 1,074 |
| Four-Seam | 1.36 [1.32, 1.40] | 19,427 |
| Sinker | 1.40 [1.34, 1.47] | 9,827 |
| Slider | 1.15 [1.06, 1.23] | 16,415 |
| Splitter | 1.83 [1.06, 2.49] | 408 |

## El integrador RK4 contra lo observado (`flight_check.csv`)

Recta y sinker medianos lanzados con la ρ̂ mediana de cada bucket, contra el cambio observado dentro del mismo pitcher (HACK-004):

| Familia | Modelo | ΔIVB predicho | ΔIVB observado | Δ mph al plato predicho | observado |
|---|---|---|---|---|---|
| Four-Seam | física de libro (elasticidad 1) | -2.79 in | -3.54 in | +1.19 | +1.30 |
| Four-Seam | elasticidad medida | -3.64 in | -3.54 in | +1.20 | +1.30 |
| Sinker | física de libro (elasticidad 1) | -1.84 in | -2.23 in | +1.18 | +1.25 |
| Sinker | elasticidad medida | -2.46 in | -2.23 in | +1.19 | +1.25 |

`physics.json` lleva la traducción por familia (la misma del paper) y los coeficientes del vuelo para el motor del navegador (HACK-042).

## Límites
- La temperatura y la humedad no están en los datos; μ del aire se fija en 1.81e-5 Pa·s.
- S usa el giro total (incluye giro de bala), lo que aplana la pendiente de C_L contra S.
- El sesgo de densidad usa la densidad barométrica del Harp Helú para todo el bucket extremo (aproximación).
