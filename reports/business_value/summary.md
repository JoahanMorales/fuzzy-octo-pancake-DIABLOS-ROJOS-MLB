# Valor de negocio: Stuff+ → carreras → victorias (HACK-035)

**Datos:** 2051 juegos con marcador reconstruido (suma de `RunsScored` por juego y media entrada; se descartan empates y juegos de < 5 entradas), 60 equipo-temporadas con ≥ 20 juegos (equipos de HACK-003). Carreras por equipo-juego: liga 5.59; No Altitude 4.51, Medium Altitude 6.29, Extreme Altitude 6.80.

## Carreras por victoria (LMB)

Exponente pitagórico **x = 1.90** (IC 95 % bootstrap 1.62–2.15, 60 equipo-temporadas). Con W% = RS^x/(RS^x+RA^x), una carrera menos permitida por juego vale x/(4r) de W%: **carreras por victoria = 4r/x**, con r las carreras por equipo-juego. Control empírico: pendiente de W% contra diferencia de carreras por juego = 0.084 (12.0 carreras por victoria por juego).

| entorno | carreras_por_equipo_juego | carreras_por_victoria | victorias_por_100_carreras |
|---|---|---|---|
| liga | 5.591 | 11.78 | 8.485 |
| No Altitude | 4.513 | 9.512 | 10.51 |
| Medium Altitude | 6.286 | 13.25 | 7.547 |
| Extreme Altitude | 6.798 | 14.33 | 6.979 |
| empírico liga (1/pendiente de W% vs dif. de carreras por juego) | – | 11.95 | 8.366 |

**Lectura:** en el Harp Helú (bucket Extreme) se anota más, así que cada carrera ahorrada vale **menos** victorias que en la liga (14.3 vs 11.8 carreras por victoria).

## Tabla de conversión: +1 punto → carreras → victorias

**Estimación directa, fuera de muestra:** los puntos de Stuff+ y Pitching+ (xRV predicho con validación cruzada por pitcher, escalado con el scaler del modelo: 100 + 10·z) se regresan contra el run value realizado; las carreras ahorradas por punto y por lanzamiento son menos la pendiente. IC 95 % por pitcher (bootstrap).

| escala | objetivo | carreras_por_punto_lanzamiento | lo | hi |
|---|---|---|---|---|
| Stuff+ | rv_x | 0.000724 | 0.000677 | 0.000769 |
| Stuff+ | rv | 0.000726 | 0.00067 | 0.000783 |
| Pitching+ | rv_x | 0.00551 | 0.00547 | 0.00556 |
| Pitching+ | rv | 0.00561 | 0.00555 | 0.00567 |

Control cruzado (Stuff+): σ del scaler del bundle v1 (0.01055) × calibración 0.69 × 0.1 = 7.24e-04, frente a 7.24e-04 directo. El bundle se reconstruyó localmente con `analysis/stuff_model/run.py` (creado 2026-10-13T14:45:18+00:00). Pitching+ usa el xRV combinado con bateador neutral (el que sirve el dashboard) escalado con un `PlusScaler` ajustado con el mismo procedimiento.

### Ejemplo para el GM

**+10 puntos de Stuff+ sostenidos en 2,500 lanzamientos** (orden de magnitud de una temporada de abridor: ~30 aperturas × ~80 lanzamientos; supuesto, no de los datos):

| escala | entorno | carreras | carreras_lo | carreras_hi | victorias | victorias_lo | victorias_hi |
|---|---|---|---|---|---|---|---|
| Stuff+ | liga | 18.1 | 16.9 | 19.2 | 1.54 | 1.44 | 1.63 |
| Stuff+ | Harp Helú (bucket Extreme) | 18.1 | 16.9 | 19.2 | 1.26 | 1.18 | 1.34 |
| Pitching+ | liga | 138 | 137 | 139 | 11.7 | 11.6 | 11.8 |
| Pitching+ | Harp Helú (bucket Extreme) | 138 | 137 | 139 | 9.62 | 9.54 | 9.7 |

Cada carrera ahorrada vale menos victorias en el Harp Helú que en la liga (más anotación), pero el valor en carreras es el mismo. **+10 puntos en todos los lanzamientos es un salto muy grande**: es 1 σ del xRV *por lanzamiento* (incluye conteo, ubicación y contexto), mucho más que la diferencia típica entre pitchers, sobre todo para Pitching+. Una escala más realista es 1 desviación estándar entre pitcher-temporadas (≥ 300 lanzamientos; observada, incluye ruido de muestreo):

| escala | entorno | sd_puntos_entre_pitcher_temporadas | pitcher_temporadas | carreras_por_1sd | victorias_por_1sd |
|---|---|---|---|---|---|
| Stuff+ | liga | 5.45 | 818 | 9.86 | 0.837 |
| Stuff+ | Harp Helú (bucket Extreme) | 5.45 | 818 | 9.86 | 0.688 |
| Pitching+ | liga | 1.55 | 818 | 21.4 | 1.82 |
| Pitching+ | Harp Helú (bucket Extreme) | 1.55 | 818 | 21.4 | 1.5 |

Tabla completa (lanzamientos × entorno × estimación) en `conversion_table.csv`; aquí 1,000 y 2,500 lanzamientos en la liga y en el Harp Helú:

| escenario | lanzamientos | entorno | carreras | victorias |
|---|---|---|---|---|
| Stuff+ · rv_x (central) | 1000 | liga | 0.724 | 0.0614 |
| Stuff+ · rv_x (central) | 1000 | Harp Helú (bucket Extreme) | 0.724 | 0.0505 |
| Stuff+ · rv_x (central) | 2500 | liga | 1.81 | 0.154 |
| Stuff+ · rv_x (central) | 2500 | Harp Helú (bucket Extreme) | 1.81 | 0.126 |
| Stuff+ · rv_x (IC 2.5 %) | 1000 | liga | 0.677 | 0.0575 |
| Stuff+ · rv_x (IC 2.5 %) | 1000 | Harp Helú (bucket Extreme) | 0.677 | 0.0473 |
| Stuff+ · rv_x (IC 2.5 %) | 2500 | liga | 1.69 | 0.144 |
| Stuff+ · rv_x (IC 2.5 %) | 2500 | Harp Helú (bucket Extreme) | 1.69 | 0.118 |
| Stuff+ · rv_x (IC 97.5 %) | 1000 | liga | 0.769 | 0.0653 |
| Stuff+ · rv_x (IC 97.5 %) | 1000 | Harp Helú (bucket Extreme) | 0.769 | 0.0537 |
| Stuff+ · rv_x (IC 97.5 %) | 2500 | liga | 1.92 | 0.163 |
| Stuff+ · rv_x (IC 97.5 %) | 2500 | Harp Helú (bucket Extreme) | 1.92 | 0.134 |
| Stuff+ · rv observado | 1000 | liga | 0.726 | 0.0616 |
| Stuff+ · rv observado | 1000 | Harp Helú (bucket Extreme) | 0.726 | 0.0507 |
| Stuff+ · rv observado | 2500 | liga | 1.82 | 0.154 |
| Stuff+ · rv observado | 2500 | Harp Helú (bucket Extreme) | 1.82 | 0.127 |
| Pitching+ · rv_x (central) | 1000 | liga | 5.51 | 0.468 |
| Pitching+ · rv_x (central) | 1000 | Harp Helú (bucket Extreme) | 5.51 | 0.385 |
| Pitching+ · rv_x (central) | 2500 | liga | 13.8 | 1.17 |
| Pitching+ · rv_x (central) | 2500 | Harp Helú (bucket Extreme) | 13.8 | 0.962 |
| Pitching+ · rv_x (IC 2.5 %) | 1000 | liga | 5.47 | 0.464 |
| Pitching+ · rv_x (IC 2.5 %) | 1000 | Harp Helú (bucket Extreme) | 5.47 | 0.381 |
| Pitching+ · rv_x (IC 2.5 %) | 2500 | liga | 13.7 | 1.16 |
| Pitching+ · rv_x (IC 2.5 %) | 2500 | Harp Helú (bucket Extreme) | 13.7 | 0.954 |
| Pitching+ · rv_x (IC 97.5 %) | 1000 | liga | 5.56 | 0.472 |
| Pitching+ · rv_x (IC 97.5 %) | 1000 | Harp Helú (bucket Extreme) | 5.56 | 0.388 |
| Pitching+ · rv_x (IC 97.5 %) | 2500 | liga | 13.9 | 1.18 |
| Pitching+ · rv_x (IC 97.5 %) | 2500 | Harp Helú (bucket Extreme) | 13.9 | 0.97 |
| Pitching+ · rv observado | 1000 | liga | 5.61 | 0.476 |
| Pitching+ · rv observado | 1000 | Harp Helú (bucket Extreme) | 5.61 | 0.391 |
| Pitching+ · rv observado | 2500 | liga | 14 | 1.19 |
| Pitching+ · rv observado | 2500 | Harp Helú (bucket Extreme) | 14 | 0.979 |

Referencia: un abridor lanza ~77 lanzamientos por apertura (mediana de los datos).

## Ejemplo: valor de un brazo a prueba de altura

Costo observado de la altura (Δ `rv_x` por lanzamiento, Extreme − sin altitud, intra pitcher-temporada, 379 pitcher-temporadas con ≥ 100 lanzamientos en ambos): **+0.0116 carreras por lanzamiento** (Medium: +0.0088). Dispersión verdadera entre pitchers (descontado el ruido de muestreo, método de momentos): τ̂ = 0.0000 (sd observada 0.0194, ruido de muestreo medio 0.0194); cota superior 95 % (bootstrap) τ ≤ 0.0066. **Con el run value por lanzamiento no se detecta heterogeneidad entre pitchers más allá del ruido**: el ejemplo usa esa cota como la brecha *máxima compatible con los datos*, no como una medición. La sensibilidad por pitcher con la física (ΔStuff+) está en HACK-018 (`reports/pitcher_sensitivity/`), no con el resultado ruidoso.

Escenario: 8 aperturas en casa por temporada (juegos de local por equipo-temporada en los datos ÷ rotación de 5) × 77 lanzamientos, a 14.3 carreras por victoria en altura.

| brazo | carreras_extra_por_lanzamiento | carreras_extra | victorias_perdidas |
|---|---|---|---|
| alta pérdida (+τ95) | 0.01821 | 11.22 | 0.7829 |
| promedio | 0.0116 | 7.146 | 0.4987 |
| a prueba de altura (−τ95) | 0.004989 | 3.073 | 0.2145 |

Brecha entre el brazo de alta pérdida y el de a prueba de altura: **8.1 carreras ≈ 0.57 victorias** en esa temporada de aperturas en casa.

## Advertencias

- `rv_x` valora las bolas en juego con la altitud como rasgo (HACK-030): el costo de la altura incluye parte del modelo de contacto, no solo los lanzamientos.
- Los bundles no se comparten por git: la escala se reconstruyó localmente (`analysis/stuff_model/run.py`); si el modelo se reentrena, hay que volver a correr este análisis (la caché OOF está en `artifacts/`, git-ignored).
- Los puntos usan el xRV de los modelos completos fuera de muestra, no el modelo destilado del dashboard (R² 0.92 / 0.94 con ellos): aproximan el mismo número.
- El efecto de un punto es chico por lanzamiento y crece con el volumen: sumas grandes (miles de lanzamientos) y grupos de lanzamientos, no un lanzamiento suelto. El `rv` observado es más ruidoso que `rv_x`: su IC es más ancho.
- Marcadores reconstruidos: partidos incompletos en los datos o carreras fuera de los lanzamientos pueden sesgar; los datos solo cubren una muestra de la temporada por equipo.
- Linealización pitagórica válida cerca de un equipo promedio; ±1σ en sensibilidad supone dispersión aproximadamente normal.
- La identidad CDMX vs Puebla sigue sin verificar (HACK-003): «entorno Extreme» agrupa los parques de altura.