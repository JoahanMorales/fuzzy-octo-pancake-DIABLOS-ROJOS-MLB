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

Por definición de la escala (HACK-013), 1 punto = 0.1 σ del xRV *predicho* por lanzamiento. Esa σ depende del modelo final (HACK-010/012), que todavía no está integrado, así que se muestran **escenarios de calidad del modelo** (fracción de la varianza del `rv_x` por lanzamiento que explica; σ(rv_x) = 0.198). **No son resultados del modelo**: cuando exista el bundle final se sustituye la σ real en `analysis/business_value/run.py`.

| escenario | lanzamientos | entorno | carreras | victorias |
|---|---|---|---|---|
| modelo débil (R²=0.25 % del xRV) | 100 | liga | 0.09899 | 0.0084 |
| modelo débil (R²=0.25 % del xRV) | 100 | Harp Helú (bucket Extreme) | 0.09899 | 0.006908 |
| modelo débil (R²=0.25 % del xRV) | 500 | liga | 0.495 | 0.042 |
| modelo débil (R²=0.25 % del xRV) | 500 | Harp Helú (bucket Extreme) | 0.495 | 0.03454 |
| modelo débil (R²=0.25 % del xRV) | 1000 | liga | 0.9899 | 0.084 |
| modelo débil (R²=0.25 % del xRV) | 1000 | Harp Helú (bucket Extreme) | 0.9899 | 0.06908 |
| modelo débil (R²=0.25 % del xRV) | 2500 | liga | 2.475 | 0.21 |
| modelo débil (R²=0.25 % del xRV) | 2500 | Harp Helú (bucket Extreme) | 2.475 | 0.1727 |
| modelo moderado (R²=1 %) | 100 | liga | 0.198 | 0.0168 |
| modelo moderado (R²=1 %) | 100 | Harp Helú (bucket Extreme) | 0.198 | 0.01382 |
| modelo moderado (R²=1 %) | 500 | liga | 0.9899 | 0.084 |
| modelo moderado (R²=1 %) | 500 | Harp Helú (bucket Extreme) | 0.9899 | 0.06908 |
| modelo moderado (R²=1 %) | 1000 | liga | 1.98 | 0.168 |
| modelo moderado (R²=1 %) | 1000 | Harp Helú (bucket Extreme) | 1.98 | 0.1382 |
| modelo moderado (R²=1 %) | 2500 | liga | 4.95 | 0.42 |
| modelo moderado (R²=1 %) | 2500 | Harp Helú (bucket Extreme) | 4.95 | 0.3454 |
| modelo fuerte (R²=3 %) | 100 | liga | 0.3429 | 0.0291 |
| modelo fuerte (R²=3 %) | 100 | Harp Helú (bucket Extreme) | 0.3429 | 0.02393 |
| modelo fuerte (R²=3 %) | 500 | liga | 1.715 | 0.1455 |
| modelo fuerte (R²=3 %) | 500 | Harp Helú (bucket Extreme) | 1.715 | 0.1197 |
| modelo fuerte (R²=3 %) | 1000 | liga | 3.429 | 0.291 |
| modelo fuerte (R²=3 %) | 1000 | Harp Helú (bucket Extreme) | 3.429 | 0.2393 |
| modelo fuerte (R²=3 %) | 2500 | liga | 8.573 | 0.7274 |
| modelo fuerte (R²=3 %) | 2500 | Harp Helú (bucket Extreme) | 8.573 | 0.5983 |

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
- La tabla Stuff+ → carreras usa escenarios, no el modelo final (aún no integrado). Las cifras absolutas cambiarán; la fórmula y el cociente entre entornos no.
- Marcadores reconstruidos: partidos incompletos en los datos o carreras fuera de los lanzamientos pueden sesgar; los datos solo cubren una muestra de la temporada por equipo.
- Linealización pitagórica válida cerca de un equipo promedio; ±1σ en sensibilidad supone dispersión aproximadamente normal.
- La identidad CDMX vs Puebla sigue sin verificar (HACK-003): «entorno Extreme» agrupa los parques de altura.