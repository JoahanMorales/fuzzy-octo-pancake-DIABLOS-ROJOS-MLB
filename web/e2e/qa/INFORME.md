# Informe QA · HACK-070

Recorrido de todas las rutas (`routes.spec.ts`, desktop y móvil) y revisión visual de las capturas a 1440 y 390 px
(`shots/`) contra `web/DESIGN.md`. La revisión visual la hizo el subagente `design-critic` mirando las capturas: son
observaciones de un modelo, no mediciones; cada una conviene confirmarla a ojo antes de actuar.

Regenerar capturas: `QA_SHOTS=1 npm --prefix web run e2e -- --project=desktop e2e/qa/shots.spec.ts`

## Comprobado por el script (falla si se rompe)

| Criterio | Cómo |
|---|---|
| Sin errores de consola, excepciones ni 4xx/5xx del mismo origen | `watch()` en cada ruta |
| h1 visible, no es el placeholder ni el 404, sin `undefined`/`NaN` | `routes.spec.ts` |
| Sin desborde horizontal (desktop y móvil) | `scrollWidth - innerWidth` |
| Cero em-dashes en texto y etiquetas accesibles (DESIGN.md §Copy) | `routes.spec.ts` |
| Foco visible con Tab (contorno o sombra de 2 px o más) | `tabStopsWithoutRing()` |
| `/pitcher/:id` con un pitcher real del leaderboard, navegación y 404 | `routes.spec.ts` |

## Corregido en esta tarea

1. `/simulador` no tenía h1: se agrega un `<h1 class="sr-only">` y la clase `.sr-only` en `base.css`.
2. Sin regla global de foco: `:focus-visible { outline: 2px solid var(--fg) }` en `base.css` (DESIGN.md §Accesibilidad).
   Arregla un enlace de la navegación en móvil.
3. `/pitcher/:id`: el gráfico de movimiento quitaba el contorno (`outline: none` en `.mv-pitch`); ahora usa el anillo global.

## Hallazgos del design-critic, sin corregir (listados)

No se corrigen aquí: tocan features de otras tareas (simulador, presentación, inicio, altitud, laboratorio…) y el
freeze es hoy; mezclar CSS ajeno en esta PR arriesga conflictos. Severidad según el crítico.

### Alta

| # | Ruta · ancho | Hallazgo | Arreglo sugerido |
|---|---|---|---|
| 1 | inicio · 390 | El chip "informe" se encima con la leyenda del gráfico y tapa "nivel del mar" | flex-wrap, leyenda en fila aparte, o quitar la leyenda superior (ya hay otra abajo) |
| 2 | presentación · 390 | La barra fija inferior tapa el hero, el gráfico y los datos | Una sola fila (contador, Siguiente, Salir) y `padding-bottom` igual a su alto |
| 3 | simulador · 1440 | El panel derecho se corta abajo; los presets (el CTA) quedan bajo el pliegue y hay una franja negra bajo la escena | Altura `calc(100dvh - header)`, `overflow-y: auto` en el panel, compactar "¿Por qué?" |
| 4 | altitud · 390 | Puntos de ~8 px en tarjetas casi vacías, sin eje ni leyenda | Pista de ancho 100 %, escala común con línea cero, puntos r ≥ 4, leyenda y eje mínimo |
| 5 | laboratorio · 390 | La tabla desborda: "Ganancia en CDMX [IC 95 %]" en 4 líneas y "Aplica a" cortado | Contenedor con `overflow-x: auto`, `th { white-space: nowrap }` |
| 15 | simulador · 390 | La escena se recorta a la izquierda y las etiquetas se cortan a la derecha; controles de cámara en dos filas | Encuadre propio en móvil (cámara/fov), etiquetas con wrap, lectura bajo la escena. Es rediseño |

### Media

| # | Ruta · ancho | Hallazgo | Arreglo sugerido |
|---|---|---|---|
| 6 | inicio y presentación | Copy interno: "Stuff+ v2 (familia)", "season holdout", "park holdout", "Pitching+ contra el nulo" | Reescribir en frases concretas; si vienen de JSON, cambiar el JSON |
| 7 | inicio · 1440 | Hero asimétrico con mucho vacío arriba y leyenda duplicada | Quitar una leyenda, reducir `padding-top` |
| 8 | leaderboard · 1440 | Columna de arsenal truncada sin elipsis ni scroll; símbolos ± poco contrastados | `overflow-x: auto` o elipsis con `title`; ± a 11 px con `--fg-muted` |
| 9 | leaderboard · 390 | Filtros apilados y desiguales; selects de ~36 px (mínimo táctil 44 px) | `min-height: 44px` en controles bajo 900 px |
| 10 | metodología · 390 / 1440 | La tabla de métricas no entra en el viewport; bloque ámbar con título cortado | Subir la tabla (`order`), `overflow-x: auto`, confirmar que el ámbar sea el token `--warn` |
| 11 | reclutamiento · 390 | Controles desalineados; input más bajo que el select, bajo 44 px | Grid de una columna y `min-height: 44px` |
| 16 | altitud · 1440 | Gráfico con la mitad derecha vacía, sin leyenda ni referencia "nivel del mar" ni conclusión | Rediseñar con eje, línea de referencia, leyenda y frase de conclusión |
| 17 | pitcher · 1440 / 390 | Gráfico de movimiento sin leyenda (punto lleno = Harp Helú, punteado = nivel del mar) | Leyenda con swatches y conclusión junto al gráfico |

### Baja

| # | Ruta · ancho | Hallazgo | Arreglo sugerido |
|---|---|---|---|
| 12 | reclutamiento · 1440 | Casillas nativas de ~13 px | `accent-color` del rojo, 18 px, área táctil de 44 px |
| 13 | todas menos simulador · 390 | El menú ocupa 3 filas (~100 px) y los enlaces miden ~28 px | `min-height: 44px` o colapsar en botón "Menú" |
| 14 | cuerpo-tecnico · 1440 | Estado vacío: casi toda la pantalla en negro | Texto de orientación o menos `min-height` |
| 18 | inicio y presentación · 1440 | Cifras hero con acento mezclado (rojo y blanco) | Rojo solo para lo del Harp Helú, o documentarlo |
| 19 | metodología, staff, laboratorio, reclutamiento | Insignia "Datos reales" y mayúsculas de títulos inconsistentes; exceso de eyebrows | Un componente de insignia y un criterio de títulos |
| 20 | física · 1440 | Los gráficos arrancan bajo el pliegue y la conclusión no se ve en 720 px | Compactar controles y KPIs |

Sin hallazgos graves: staff y prospecto.

## Nota de prueba existente

`flow.spec.ts` (landing a pitcher) tardó 51-57 s de 60 s en una corrida en paralelo (lo avisó el revisor); pasa solo.
