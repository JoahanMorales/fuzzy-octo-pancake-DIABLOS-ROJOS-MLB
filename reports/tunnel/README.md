# Tunneling por tiempo (HACK-061)

El punto de decisión del bateador se fija en el **tiempo**: 150 ms antes de que la pelota llegue al frente del plato (17/12 ft), resuelto con el ajuste de aceleración constante de 9 parámetros de cada lanzamiento. En aire delgado la pelota llega antes, así que esos 150 ms corresponden a otra distancia. La separación se mide contra la recta principal del mismo pitcher (promedio del juego con al menos 3 rectas, si no de la temporada), en ese punto y en el plato, y el cociente de tunneling es separación en el plato / separación en la decisión. Son rasgos físicos: nunca usan resultados.

Para que no sean ubicación disfrazada, se comparan trayectorias promedio por tipo de pitch y juego (no lanzamientos sueltos; promedio del juego con al menos 3 lanzamientos, si no de la temporada) contra la recta principal construida igual. Ver la auditoría de ubicación abajo.

Datos: 623,231 lanzamientos de 924 pitchers.

## Regla de adopción (fijada antes de correr)

Se adopta solo si se cumplen las tres: (1) el límite inferior del IC 95 % de la habilidad por lanzamiento con tunneling es mayor o igual a la habilidad del modelo base; (2) la r de pitcher-temporada de "primeros N lanzamientos al resto" (N = 50, 100, 200) no baja más de 0.005 contra la base; (3) la confiabilidad split-half no baja más de 0.005 contra la base.

## Antes y después (pliegues por pitcher, objetivo rv_x)

| Modelo | RMSE | Habilidad vs null | IC 95 % |
|---|---|---|---|
| Null: media de rv_x por cuenta | 0.19757 |  |  |
| Stuff+ base (rasgos invariantes) | 0.19762 | -0.025 % | -0.051 % a 0.003 % |
| Stuff+ con tunneling por tiempo | 0.19761 | -0.021 % | -0.048 % a 0.007 % |

| N primeros lanzamientos | Pitcher-temporadas | r base | r con tunneling | Diferencia |
|---|---|---|---|---|
| 50 | 711 | 0.265 | 0.248 | -0.017 |
| 100 | 623 | 0.291 | 0.278 | -0.014 |
| 200 | 461 | 0.306 | 0.272 | -0.035 |

Split-half (631 pitcher-temporadas): base 0.807, con tunneling 0.779 (diferencia -0.028).

## Veredicto

| Criterio | Con tunneling | Referencia | Cumple |
|---|---|---|---|
| 1. habilidad: IC inferior del tunnel >= habilidad del base | -0.0005 | -0.0003 | no |
| 2. r primeros 50 -> resto >= base - 0.005 | 0.2477 | 0.2648 | no |
| 2. r primeros 100 -> resto >= base - 0.005 | 0.2775 | 0.2915 | no |
| 2. r primeros 200 -> resto >= base - 0.005 | 0.2717 | 0.3065 | no |
| 3. split-half >= base - 0.005 | 0.7794 | 0.8072 | no |

**No adoptar: al menos un criterio falla.** La adopción real pasa por HACK-057 (congelamiento 2026-10-20 12:00).

## Chequeo de altitud (mismo pitch, Extreme menos No Altitude)

Diferencia dentro del mismo pitcher x temporada x pitch_key, sin las rectas principales, con IC 95 % por bootstrap de pitchers. Los renglones `arsenal.py` son el tunneling por distancia ya existente, para comparar.

| Métrica | Pitches comparados (pitcher x temporada x tipo) | Extreme menos No | IC 95 % | Cambio relativo | Distinto de 0 |
|---|---|---|---|---|---|
| separación en la decisión (pulg) | 713 | +0.172 | -0.010 a +0.354 | +3.1 % | no |
| separación en el plato (pulg) | 713 | -0.327 | -0.623 a -0.026 | -3.3 % | sí |
| cociente de tunneling (tiempo) | 713 | -0.182 | -0.255 a -0.112 | -8.8 % | sí |
| distancia al plato del punto de decisión (ft) | 713 | +0.212 | +0.197 a +0.226 | +1.1 % | sí |
| tiempo de vuelo al plato (s) | 713 | -0.0034 | -0.0038 a -0.0031 | -0.8 % | sí |
| arsenal.py: separación a 23.8 ft (ft) | 713 | +0.0109 | +0.0028 a +0.0201 | +1.5 % | sí |
| arsenal.py: separación en el plato (ft) | 713 | -0.0222 | -0.0388 a -0.0050 | -1.6 % | sí |
| arsenal.py: cociente por distancia | 713 | -0.152 | -0.191 a -0.115 | -6.4 % | sí |

Cociente de tunneling por familia de pitch:

| Familia | Pitches comparados | Extreme menos No | IC 95 % |
|---|---|---|---|
| Changeup | 147 | -0.062 | -0.150 a +0.026 |
| Curveball | 66 | -0.561 | -0.877 a -0.244 |
| Cutter | 6 | +0.083 | -0.078 a +0.272 |
| Four-Seam | 129 | +0.036 | -0.074 a +0.169 |
| Sinker | 59 | -0.072 | -0.151 a +0.004 |
| Slider | 296 | -0.275 | -0.423 a -0.158 |
| Splitter | 10 | -0.300 | -0.824 a -0.097 |

## Auditoría de ubicación

Los rasgos de Stuff+ no pueden codificar hacia dónde se apuntó. Correlación de cada rasgo con la altura y el lado (en marco del brazo) en el plato, en lanzamientos que no son la recta principal:

| Rasgo | r con altura | r con lado | máx. de r absoluta dentro de familia |
|---|---|---|---|
| tunnel_dec_dx_in | -0.10 | -0.28 | 0.31 |
| tunnel_dec_dz_in | +0.35 | +0.11 | 0.34 |
| tunnel_dec_sep_in | -0.16 | -0.04 | 0.19 |
| tunnel_plate_dx_in | -0.15 | -0.35 | 0.35 |
| tunnel_plate_dz_in | +0.39 | +0.13 | 0.35 |
| tunnel_plate_sep_in | -0.28 | -0.15 | 0.28 |
| tunnel_ratio_t | -0.09 | -0.09 | 0.11 |

La correlación global más alta es 0.39 (tunnel_plate_dz_in con PlateLocHeight); dentro de cada familia de pitch la correlación más alta baja a 0.35.

## Reproducir

```
python analysis/tunnel/run.py
```
