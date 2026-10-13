---
title: "Stuff+ 2240: calidad de pitcheo ajustada por la densidad del aire del Harp Helú"
subtitle: "Documento técnico · ISAC Sports Analytics Hackathon 2026 · Diablos Rojos"
author: "Equipo Stuff+ 2240"
date: "Octubre 2026"
lang: es
---

<!--
ESTADO: esqueleto (HACK-008). Cada marcador "TODO(HACK-NNN)" nombra la tarea que llena la sección.
Presupuesto final: 6–10 páginas (HACK-023 hace la versión final). Cifras con fuente en reports/<tarea>/;
lo que no está verificado se dice explícitamente. Compilar: bash docs/technical/build.sh
-->

# Introducción

El Harp Helú (Ciudad de México, ~2,240 m) tiene un aire más ligero que el de cualquier parque de nivel del mar. Los modelos públicos de calidad de pitcheo, como Stuff+, Location+ y Pitching+ de FanGraphs [@mcgrattan2023primer], se entrenan con datos de MLB y su descripción pública no menciona parques, altitud ni ajustes de entorno. Para un cuerpo técnico que evalúa lanzadores en la LMB, el mismo lanzamiento no vale lo mismo en dos aires distintos.

**Pregunta del reto.** ¿Cuánto vale cada lanzamiento en el aire de la CDMX, y qué perfiles conviene reclutar?

**Contribución.** *Stuff+ 2240* (i) mide la densidad del aire por juego a partir de la física de cada trayectoria, en lugar de usar una etiqueta de altitud; (ii) identifica estadios y equipos sin metadatos de parque; (iii) define la identidad del lanzamiento con rasgos que el aire no cambia; y (iv) separa un modelo físico de uno de resultado para poder responder el contrafactual *el mismo release, en el aire de la CDMX contra el de nivel del mar*.

<!-- TODO(HACK-023): resumen de resultados con cifras finales (ΔStuff+ por forma, validación, valor en victorias). -->

# Marco teórico

## Stuff+, Location+ y Pitching+

Stuff+ evalúa un lanzamiento solo por sus rasgos físicos (velocidad, movimiento, extensión, ángulo de salida; los secundarios se comparan contra la recta principal del lanzador). Location+ evalúa dónde y en qué conteo se lanzó, y Pitching+ combina ambas [@mcgrattan2023primer]. En el modelo de FanGraphs, 10 puntos equivalen a una desviación estándar a nivel de lanzamiento [@mcgrattan2023primer]. Nosotros adoptamos la misma lectura de la escala (§2.3) y añadimos lo que ese modelo no documenta: el entorno.

## Por qué el aire cambia el lanzamiento

Sobre la pelota actúan el arrastre y la fuerza de Magnus, ambas proporcionales a la densidad del aire $\rho$ [@nathan2006spin]:
$$
a_D = \tfrac{1}{2}\,\frac{\rho A}{m}\,C_D\,v^2, \qquad a_L = \tfrac{1}{2}\,\frac{\rho A}{m}\,C_L\,v^2,
$$
con $A$ el área frontal, $m$ la masa, $v$ la rapidez, y $C_D$, $C_L$ los coeficientes de arrastre y sustentación. Con $C_L$ y $v$ dados, la desviación lateral o vertical acumulada en un tiempo de vuelo $T$ es aproximadamente
$$
\Delta x \;\approx\; \tfrac{1}{2}\,a_L\,T^2 \;\propto\; \rho .
$$
Si $\rho$ baja 16 %, la curvatura inducida por el giro baja en esa misma proporción, de primer orden. El arrastre también cae, de modo que el tiempo de vuelo $T$ es algo menor y la recta llega al plato con más velocidad. De ahí la pérdida de "ride" de la recta y la caída más corta de la curva.

La sustentación se relaciona con el giro mediante la eficiencia de giro $S$, con la relación empírica de Nathan $C_L = 1/(2.32 + 0.4/S)$ que usa `stuffplus/physics/aero.py` (la forma exacta no la reverificamos contra la fuente; ver [@nathan2006spin; @nathan2021hawkeye] para las mediciones y para separar el movimiento Magnus del no Magnus, y [@nathan2017allspin; @nathan2018everything] como lectura sobre componentes del giro). El planteamiento del reto afirma que el *break* de una curva de 18" baja a 14–15" en Coors (1,609 m); es la cifra del reto y no la verificamos de forma independiente. Para la relación entre altitud y carreras: [@richardson2014altitude].

## Definición formal de las dos escalas

Sea $i$ un lanzamiento con rasgos de release y arsenal $\mathbf{z}_i$ (velocidad, giro, eje, extensión, ángulo de brazo, diferencias contra la recta del lanzador, etc.) y sea $\rho$ la densidad relativa del aire, con $\rho=1$ a nivel del mar. El modelo de dos etapas es:

1. **Etapa física (A).** Movimiento esperado $\mathbf{m}_i(\rho)=f_A(\mathbf{z}_i,\rho)$ = (IVB, HB, pérdida de velocidad, velocidad al plato), ajustado con variación **intra-lanzador y por `pitch_id`**.
2. **Etapa de resultado (B).** Un valor de carreras esperado
$$
\widehat{xRV}_i(\rho) \;=\; \sum_{k\in\mathcal{K}} P_k\!\big(\mathbf{z}_i,\mathbf{m}_i(\rho),\rho\big)\, V_k ,
$$
donde $\mathcal{K}$ son los resultados del lanzamiento (strike cantado, swing y fallo, contacto por tipo, bola, etc.) y $V_k$ su valor en carreras **calibrado a la LMB** (cambio de conteo y *linear weights* [@fangraphs_lw; @tango2008woba], con `RunsScored`).

Sean $\mu_0$ y $\sigma_0$ la media y la desviación estándar de $-\widehat{xRV}_i(\rho_{\text{mar}})$ en los lanzamientos de la LMB de la temporada de referencia, evaluados a nivel del mar. Definimos
$$
\boxed{\;\text{Stuff+}^{\,N}_i \;=\; 100 + 10\,\frac{-\widehat{xRV}_i(\rho_{\text{mar}})-\mu_0}{\sigma_0}\;}
\qquad
\boxed{\;\text{Stuff+}^{\,E}_i(\rho) \;=\; 100 + 10\,\frac{-\widehat{xRV}_i(\rho)-\mu_0}{\sigma_0}\;}
$$
- **Neutral** ($N$, *park-neutral*): 100 = promedio de la LMB a nivel del mar.
- **Entorno** ($E$): el mismo lanzamiento evaluado a la densidad $\rho$ de un parque, con **la misma $\mu_0,\sigma_0$**; por eso no promedia 100 en un parque alto.
- **Efecto de la altitud:** $\Delta\text{Stuff+}_i=\text{Stuff+}^{E}_i(\rho_{HH})-\text{Stuff+}^{N}_i$, con $\rho_{HH}$ la densidad estimada del Harp Helú (`RHO_HARP_HELU`).

Location+ y Pitching+ siguen la misma regla con sus propias entradas. Location+ se centra por conteo y tipo de lanzamiento. Toda cifra del documento indica qué sabor usa.

# Datos

- **Fuente:** datos Trackman de la LMB proporcionados por el reto (no se publican). 635,002 lanzamientos, 84 columnas, temporadas 2024–2026, 1,134 lanzadores, 2,127 juegos; tras la limpieza (`stuffplus.schema.clean`) quedan 627,602 filas. La variable ambiental es `altitude_category` (No / Medium / Extreme), sin identificador de estadio.
- **Orden de los datos.** Las filas están en orden de juego y turno (el conteo no decrece en el 99.99 %), así que las secuencias son construibles. No hay corredores en base: el estado base-outs se reduce a *outs × conteo*.
- **Etiquetas de lanzamiento (label shift).** Trackman reetiqueta `AutoPitchType` según el aire. Para los mismos lanzadores, comparar Extreme con No cambia el uso de etiquetas hasta 3.33 pp (p. ej. Sinker y Changeup −2.8 pp, Cutter y Slider +2.5 pp). Una identidad basada en rasgos invariantes (`pitch_id`, HACK-029) lo reduce a 0.49 pp en `pitch_family`; el piso de ruido de la prueba de permutación es 0.40 pp, así que el margen es estrecho. `SpinRate` se excluyó de la identidad porque sube unos 17 rpm en Extreme dentro del mismo lanzamiento. Las subformas de slider siguen moviéndose más de 0.5 pp (sweeper −1.07 pp).
- **Identificación de parques (HACK-003).** Con comunidades de bateadores en las alineaciones (Louvain [@blondel2008louvain]) se recuperan 20 equipos por temporada, con pureza de altitud 1.00. Las dos franquicias de menor densidad son indistinguibles con los datos: $P$(11 menos densa que 5) = 0.832, por debajo del umbral de 0.95, por lo que se usan ambas combinadas. $\hat\rho=0.819$ (IC 95 % 0.814–0.824, 148 juegos). **La identidad CDMX frente a Puebla no está verificada** (los IDs son anónimos) y debe confirmarse con Diablos.
- **Ambiente de carreras.** La expectativa de carreras al inicio de la entrada es 0.739 (No), 1.004 (Medium) y 1.113 (Extreme) según `reports/targets/run_environment_by_altitude.csv`.

<!-- TODO(HACK-004/HACK-030): tabla final de ρ̂ por parque y comparación LMB-MLB (la de MLB está marcada "unverified" en el repo). -->

# Metodología

## Densidad del aire por juego
De la trayectoria ajustada de 9 parámetros se obtiene la aceleración por arrastre (a lo largo de $-\hat v$, con gravedad retirada) y la de Magnus (perpendicular a $v$). De ahí, $C_D$-proxy $=a_D/v^2$ y $C_L$-proxy $=a_L/v^2$. La densidad del juego es $\hat\rho$ = mediana del $C_D$-proxy de las rectas ÷ la de los juegos sin altitud; los juegos con menos de 30 rectas se encogen hacia su parque. Medias por bucket (`reports/physics/README.md`): 1.001 (No), 0.892 (Medium), 0.841 (Extreme).

**Advertencia.** Si ambos coeficientes fueran $\propto\rho$, el cociente $C_L/C_D$ sería constante. En los datos baja ~9 % en Extreme ($C_D$ −16 %, $C_L$ −24 %), y la eficiencia de giro cae de 0.61 a 0.52. No lo resolvimos: puede ser un efecto real (régimen de Reynolds/giro) o un artefacto de calibración de Trackman por parque. Por eso los $\Delta$ de movimiento se estiman **empíricamente** (efectos fijos por lanzador-temporada y `pitch_id`) y no con el modelo teórico de $C_L$, y no presentamos deltas de eficiencia de giro como hecho.

## Targets y valor de carreras en la LMB
Multi-target: $P$(swing), $P$(whiff), $P$(chase), $P$(strike cantado), $P$(contacto débil), $P$(rola), $P$(contacto fuerte) y el valor de carreras $xRV$, con *linear weights* y matriz de expectativa de carreras recalculados con datos LMB (no MLB). Los pesos para combinarlos salen de regresar el RV observado, no se fijan a mano.

<!-- TODO(HACK-010/HACK-011): descripción final de los sub-modelos (componentes de xRV, Location+) y sus hiperparámetros. -->

## Modelo, escala y explicación
LightGBM [@ke2017lightgbm] para la etapa de resultado, con validación agrupada por lanzador. Escala neutral/entorno según §2.3 (HACK-013). Explicaciones locales y globales con SHAP [@lundberg2017shap] (HACK-019).

# Validación

Siempre contra el **baseline nulo** (xRV medio por conteo, HACK-005). Planeado: *holdout* por lanzador (GroupKFold por `pitcher_anon_id`), por temporada (entrena 2024–25, prueba 2026) y por parque (entrena No + Medium, prueba Extreme); calibración en Extreme con y sin $\hat\rho$ y movimiento trasladado; estabilidad mitad-contra-mitad y año contra año.

<!-- TODO(HACK-014): tablas de RMSE / log-loss / calibración por split, con IC. -->
<!-- TODO(HACK-009): hipótesis H1–H4 con evidencia LMB (diseño intra-lanzador, IC bootstrap). -->

# Efecto de la altitud

**Evidencia física ya medida (HACK-004).** Para la recta, el efecto Extreme − No (efectos fijos por lanzador × temporada × `pitch_id`, IC bootstrap 95 %) es $\Delta$IVB $-3.54$" [$-3.60$, $-3.46$] y $\Delta$HB $-1.15$", y llega **+1.30 mph más rápida**. La curva *pierde caída*: $\Delta$IVB $+1.58$" [$+1.43$, $+1.74$]. Los IC solo propagan la incertidumbre del coeficiente de $\rho$, no la de $\Delta\rho$ ni la de la identidad del lanzamiento.

<!-- TODO(HACK-015): ΔStuff+ por forma y familia (contrafactual + observado), con IC y ranking de formas que ganan o pierden en la CDMX; curvas de altitud por parque. -->
<!-- TODO(HACK-018): sensibilidad por lanzador (más y menos afectados). -->

# Recomendaciones y valor de negocio

Del Stuff+ a carreras y a victorias con carreras-por-victoria estimadas en la LMB; auditoría del staff de Diablos (Stuff+ en casa y de gira); perfil físico ideal a 2,240 m; guía de reclutamiento; laboratorio de diseño de lanzamiento.

<!-- TODO(HACK-017): perfil físico ideal. TODO(HACK-021): perfilador de prospectos. TODO(HACK-022): memo operativo con ganadores, perdedores y tácticas. -->

# Alcance y fronteras

- **Fuera de alcance:** seguimiento de corredores (no está en los datos) y datos externos de MLB para entrenar.
- **Limitaciones que hoy conocemos:** (i) identidad CDMX frente a Puebla sin verificar; (ii) brecha de eficiencia de giro sin explicar; (iii) piso de muestreo de ~3 pp para el desplazamiento de etiquetas por lanzador individual, por lo que el criterio solo se evalúa agregado; (iv) la referencia MLB de los targets está marcada *unverified*.
- **Ética:** IDs anónimos, sin fines de apuesta, y los datos crudos nunca están en git ni en el despliegue (solo agregados).

<!-- TODO(HACK-023): revisar que cada limitación tenga su evidencia en el documento final. -->

# Referencias {-}

::: {#refs}
:::
