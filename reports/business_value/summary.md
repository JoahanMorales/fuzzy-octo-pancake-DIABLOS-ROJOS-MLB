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

## Tabla de conversión: +1 punto de Stuff+ → carreras → victorias

Por definición de la escala (HACK-013), 1 punto = 0.1 σ del xRV predicho por lanzamiento, y σ sale del **bundle v1** (`scalers.stuff.stats`, creado 2026-10-13T22:22:40+00:00): σ = 0.01055 carreras por lanzamiento (por temporada 2024: 0.01063, 2025: 0.01057, 2026: 0.01033). Las carreras *realizadas* por carrera predicha se miden fuera de muestra (validación cruzada por pitcher): pendiente de calibración **0.69** [IC 95 % por pitcher 0.64, 0.73] sobre 627,602 lanzamientos. Entonces +1 punto ≈ 7.24e-04 carreras por lanzamiento (filas «calibración baja/alta» = extremos del IC). Sin escenarios supuestos: la σ y la calibración son del modelo real.

| escenario | lanzamientos | entorno | carreras | victorias |
|---|---|---|---|---|
| calibración central | 100 | liga | 0.07236 | 0.00614 |
| calibración central | 100 | Harp Helú (bucket Extreme) | 0.07236 | 0.00505 |
| calibración central | 500 | liga | 0.3618 | 0.0307 |
| calibración central | 500 | Harp Helú (bucket Extreme) | 0.3618 | 0.02525 |
| calibración central | 1000 | liga | 0.7236 | 0.0614 |
| calibración central | 1000 | Harp Helú (bucket Extreme) | 0.7236 | 0.0505 |
| calibración central | 2500 | liga | 1.809 | 0.1535 |
| calibración central | 2500 | Harp Helú (bucket Extreme) | 1.809 | 0.1263 |
| calibración baja (IC 2.5 %) | 100 | liga | 0.0677 | 0.005744 |
| calibración baja (IC 2.5 %) | 100 | Harp Helú (bucket Extreme) | 0.0677 | 0.004724 |
| calibración baja (IC 2.5 %) | 500 | liga | 0.3385 | 0.02872 |
| calibración baja (IC 2.5 %) | 500 | Harp Helú (bucket Extreme) | 0.3385 | 0.02362 |
| calibración baja (IC 2.5 %) | 1000 | liga | 0.677 | 0.05744 |
| calibración baja (IC 2.5 %) | 1000 | Harp Helú (bucket Extreme) | 0.677 | 0.04724 |
| calibración baja (IC 2.5 %) | 2500 | liga | 1.692 | 0.1436 |
| calibración baja (IC 2.5 %) | 2500 | Harp Helú (bucket Extreme) | 1.692 | 0.1181 |
| calibración alta (IC 97.5 %) | 100 | liga | 0.07688 | 0.006524 |
| calibración alta (IC 97.5 %) | 100 | Harp Helú (bucket Extreme) | 0.07688 | 0.005365 |
| calibración alta (IC 97.5 %) | 500 | liga | 0.3844 | 0.03262 |
| calibración alta (IC 97.5 %) | 500 | Harp Helú (bucket Extreme) | 0.3844 | 0.02683 |
| calibración alta (IC 97.5 %) | 1000 | liga | 0.7688 | 0.06524 |
| calibración alta (IC 97.5 %) | 1000 | Harp Helú (bucket Extreme) | 0.7688 | 0.05365 |
| calibración alta (IC 97.5 %) | 2500 | liga | 1.922 | 0.1631 |
| calibración alta (IC 97.5 %) | 2500 | Harp Helú (bucket Extreme) | 1.922 | 0.1341 |

Referencia: un abridor lanza ~77 lanzamientos por apertura (mediana de los datos).

## Ejemplo: valor de un brazo a prueba de altura

Costo observado de la altura (Δ `rv_x` por lanzamiento, Extreme − sin altitud, intra pitcher-temporada, 379 pitcher-temporadas con ≥ 100 lanzamientos en ambos): **+0.0116 carreras por lanzamiento** (Medium: +0.0088). Dispersión verdadera entre pitchers (descontado el ruido de muestreo, método de momentos): τ̂ = 0.0000 (sd observada 0.0194, ruido de muestreo medio 0.0194); cota superior 95 % (bootstrap) τ ≤ 0.0066. **Con el run value por lanzamiento no se detecta heterogeneidad entre pitchers más allá del ruido**: el ejemplo usa esa cota como la brecha *máxima compatible con los datos*, no como una medición. La sensibilidad por pitcher la medirá HACK-018 con la física (ΔStuff+), no con el resultado ruidoso.

Escenario: 8 aperturas en casa por temporada (juegos de local por equipo-temporada en los datos ÷ rotación de 5) × 77 lanzamientos, a 14.3 carreras por victoria en altura.

| brazo | carreras_extra_por_lanzamiento | carreras_extra | victorias_perdidas |
|---|---|---|---|
| alta pérdida (+τ95) | 0.01821 | 11.22 | 0.7829 |
| promedio | 0.0116 | 7.146 | 0.4987 |
| a prueba de altura (−τ95) | 0.004989 | 3.073 | 0.2145 |

Brecha entre el brazo de alta pérdida y el de a prueba de altura: **8.1 carreras ≈ 0.57 victorias** en esa temporada de aperturas en casa.

## Advertencias

- `rv_x` valora las bolas en juego con la altitud como rasgo (HACK-030): el costo de la altura incluye parte del modelo de contacto, no solo los lanzamientos.
- La σ es la del bundle v1 reconstruido localmente con `analysis/stuff_model/run.py` (los bundles no se comparten por git); si el modelo se reentrena, hay que volver a correr este análisis.
- La calibración se mide sobre el xRV predicho fuera de muestra (modelo de cinco resultados), mientras la escala del bundle usa el modelo destilado (R² 0.92 con él): son aproximaciones del mismo modelo.
- A este nivel de calibración el valor de un punto por lanzamiento es pequeño: el efecto aparece en sumas grandes (mil lanzamientos o más) y en grupos de lanzamientos, no en un lanzamiento suelto.
- Marcadores reconstruidos: partidos incompletos en los datos o carreras fuera de los lanzamientos pueden sesgar; los datos solo cubren una muestra de la temporada por equipo.
- Linealización pitagórica válida cerca de un equipo promedio; ±1σ en sensibilidad supone dispersión aproximadamente normal.
- La identidad CDMX vs Puebla sigue sin verificar (HACK-003): «entorno Extreme» agrupa los parques de altura.