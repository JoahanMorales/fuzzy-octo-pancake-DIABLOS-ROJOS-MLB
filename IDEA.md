# IDEA · Stuff+ 2240

> Reto: ISAC Sports Analytics Hackathon 2026 · Diablos Rojos — *Stuff Plus Model: calidad de pitcheo ajustada por entorno*.
> Entrega: 2026-10-22. Tags: **[Decided]** · **[Recommended]** · **[To validate]**.

## 0. Nombre y marca (fijo)
- Nombre: **Stuff+ 2240** · repo: `fuzzy-octo-pancake-DIABLOS-ROJOS-MLB` · tagline: *El primer Stuff+ que respira el aire de la CDMX.*
- Identidad visual: rojo Diablos + negro, tipografía condensada deportiva. UI en **español**.

## 1. Una línea
Para el **pitching coach y el director deportivo de Diablos Rojos**, que hoy evalúan lanzadores con modelos MLB entrenados a nivel del mar (aire **~16 % más denso** que en el Harp Helú, medido en nuestros datos), **Stuff+ 2240** les dice **cuánto vale cada pitch en el aire de la CDMX y qué perfiles reclutar**, a diferencia de Stuff+/Pitching+ de FanGraphs que ignoran la altitud.

**Ventaja vs otros equipos:** casi todos entrenarán un LightGBM con `altitude_category` como dummy. Nosotros **medimos la física en los datos**:
1. **Densidad del aire por juego** estimada de la desaceleración por arrastre de cada lanzamiento (trayectoria de 9 parámetros, `ax0/ay0/az0`, `vx0/vy0/vz0`) → índice continuo ρ̂ por juego, no una etiqueta de 3 niveles.
2. **Identificación del Harp Helú** dentro del bucket "Extreme Altitude" vía detección de comunidades de pitchers (el home team lanza la parte alta) + ρ̂ mínima.
3. **Modelo de dos etapas** (física → outcome) que permite el contrafactual honesto: *el mismo release (velo, spin, eje, extensión) lanzado en ρ CDMX vs ρ nivel del mar*.

## 2. Usuarios
| Persona | Momento | Necesidad | Paso del flujo |
|---|---|---|---|
| Pitching coach | Bullpen / preparación de serie | ¿Qué pitch de mi lanzador pierde más en casa? ¿Qué ajusto? | 2, 3 |
| Director deportivo | Draft, agentes libres, intercambios | ¿Este prospecto rinde en 2,240 m? | 4, 5 |
| Analista | Reporte semanal | Stuff+/Location+/Pitching+ por pitch y pitcher | 1 |

## 3. Caso demo
Un pitcher anónimo real con fastball de mucho "ride" (IVB alto) y slider: en el Harp Helú su fastball pierde ~3.7" de IVB y su Stuff+ cae X puntos, mientras que un sinker/splitter de otro pitcher casi no cambia. El jurado ve el mismo pitch evaluado en los dos aires lado a lado.

## 4. Flujo demo (≤ 3 min)
| # | Usuario hace | Ve en pantalla | Módulo | Prio |
|---|---|---|---|---|
| 1 | Abre el dashboard | Leaderboard Stuff+ / Location+ / Pitching+ por pitcher y arsenal (filtro Harp Helú vs nivel del mar) | `app/` + `artifacts/scores` | P0 |
| 2 | Captura un pitch (velo, spin, eje, IVB/HB o release) | **Wow:** Stuff+ CDMX vs Stuff+ nivel del mar lado a lado + flechas de movimiento perdido en el mapa de movimiento | `stuffplus.api.predict_pitch` | P0 |
| 3 | Clic en "¿por qué?" | SHAP: qué features empujan el score; delta por altitud | `stuffplus.explain` | P1 |
| 4 | Carga el arsenal de un prospecto | Stuff+ de arsenal en CDMX, comparables, riesgo HR | `app/pages/prospecto` | P0 |
| 5 | Abre "Recomendaciones" | Perfiles que ganan/pierden en altitud con explicación física | `reports/` | P0 |

- Wow en una frase: *"Este mismo fastball vale 112 en Monterrey y 96 en el Harp Helú — y te decimos por qué."* · segundos al wow: ≤ 40.
- Plan B: video `demo/planb.mp4`; dashboard corre local desde `artifacts/` sin datos crudos.

## 5. Núcleo técnico
- **Targets [Decided]:** xRunValue por pitch = valor de transición de conteo + linear weights de eventos, **calibrado a LMB** con `RunsScored` (no MLB). Multi-target: P(whiff), P(chase), P(called strike), P(weak contact), P(GB), P(hard/barrel), xRV, P(out en PA). Pesos de combinación = regresión del RV observado sobre las probabilidades (defendible, no a mano).
- **Tres sub-modelos [Decided]:** Stuff+ (solo física en release + arsenal + ρ), Location+ (zona × conteo × lado × cluster de pitch), Pitching+ (todo).
- **Física [Decided]:** etapa A = modelo de movimiento `release + spin + ρ → IVB/HB esperados` (ajustado con deltas intra-pitcher); etapa B = modelo de outcome. Contrafactual = mismos inputs en ρ_CDMX vs ρ_mar.
- **Escala [Decided]:** Stuff+ = 100 + 10·z(−xRV) normalizado **por temporada sobre todos los pitches LMB** (100 = promedio liga); versión por tipo de pitch como vista secundaria.
- **Modelos:** LightGBM (principal) + SHAP; benchmark GAM/jerárquico (P2); Causal Forest táctico (P2).
- **Validación honesta:** pitcher holdout (GroupKFold por `pitcher_anon_id`), season holdout (train 2024–25 → test 2026), park holdout (train No+Medium → test Extreme), estabilidad año-a-año del Stuff+ por pitcher, y siempre vs **baseline nulo = xRV medio por conteo**.

## 6. Datos (contrato en `stuffplus/schema.py`)
| Entidad | Campos clave | Fuente |
|---|---|---|
| Pitch | 635,002 pitches · 84 cols · 2024 (243k) / 2025 (256k) / 2026 (136k) · 1,134 pitchers · 2,127 juegos | ISAC/Diablos (**no se publica**) |
| Ambiente | `altitude_category`: No (294k) / Medium (155k) / Extreme (183k) / NaN (3k). Sin ID de estadio. | idem |
| Orden | Las filas están en orden de juego/PA (conteo no decreciente 99.99 %) → `prev_pitch_type` y secuencia **sí** son construibles. No hay corredores en base → base-out reducido a outs × conteo. | verificado 2026-10-12 |

## 7. Riesgos / spikes
| Riesgo | Spike | Fallback |
|---|---|---|
| No poder aislar Harp Helú | HACK-003 (Louvain sobre co-apariciones + ρ̂) | Reportar "bucket Extreme Altitude (incluye Harp Helú)" + ρ̂ = 2,240 m teórica |
| Ruido en ρ̂ por clima | HACK-004 | Usar mediana por juego con fastballs, shrinkage por estadio |
| Sin `gh` → sin auto-merge | setup | PR manual vía URL de `wt pr` |

## 8. Rúbrica → evidencia
| Criterio | Peso | Evidencia |
|---|---:|---|
| C1 Calidad | 25 | RMSE/log-loss/calibración vs baseline nulo por conteo (HACK-005/014) |
| C2 Robustez | 25 | Pitcher + season + park holdout, estabilidad año-a-año (HACK-014) |
| C3 Arsenal + altitud | 25 | ρ̂ por juego, ΔIVB intra-pitcher, ΔStuff+ por pitch shape con IC (HACK-004/009/015) |
| C4 Aplicabilidad | 25 | Simulador, perfilador de prospectos, memo de recomendaciones, entrevista (HACK-018/019/021/023) |

## 9. Alcance
Fuera: tracking de corredores (no está en los datos), datos MLB externos para entrenar. UI: español. Ética: IDs anónimos, sin apuestas, datos crudos nunca en git ni en el deploy.

## 10. Hechos citables (verificados 2026-10-12 en los datos)
| Hecho | Fuente |
|---|---|
| Coef. de arrastre por juego (fastballs): Extreme/No = 0.838 → ~16 % menos densidad | análisis exploratorio, `analysis/` (HACK-004 lo formaliza) |
| Mismo pitcher, four-seam: IVB −3.7" en Extreme vs No (n=404 pitchers, sd 1.0), velo +0.08 mph | idem |
| Curveball cae +1.7" menos; changeup pierde 4.1" de HB (fade) en Extreme | idem (pone a prueba H2) |
| Harp Helú ≈ 2,240 m; Coors 1,609 m; break 18" → 14–15" en Coors (Alan Nathan) | reto ISAC, SABR *High Altitude Offense* |
