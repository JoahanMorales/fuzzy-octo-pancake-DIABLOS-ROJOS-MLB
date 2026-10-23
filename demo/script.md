# Demo Stuff+ 2240 · guion de 3 minutos

Estado: guion para la app React (`web/`, Stuff+ v2 en producción desde HACK-057). Ensayo cronometrado en otra laptop pendiente.
Respaldo: [deck](deck/deck.pdf) y [resumen de una página](one-pager/one-pager.pdf). Entrevista larga: [deck y tiempos](deck/README.md) y [30 preguntas](qa.md).

## Preparación del presentador

- Abrir el sitio publicado (o `npm --prefix web run preview` en local) en ventana privada, 1280×720.
- Confirmar que la insignia dice **datos reales** (no "ejemplo"). Si dice "ejemplo", decirlo en voz alta y no atribuir cifras oficiales al mock.
- Dejar abierto `/simulador` con el preset **Recta de ride**, parque **Harp Helú** y cámara **Receptor**. El panel se calcula en vivo: no hay botón de calcular.
- Pestañas listas: `/fisica`, `/altitud`, `/staff`, `/metodologia`. No abrir datos por lanzamiento: la app solo trae agregados.

## Recorrido (180 s; wow antes de 40 s)

| Tiempo | Pantalla | Acción | Narración |
|---|---|---|---|
| 0–10 s | Simulador, cámara Receptor | Lanzar la recta de ride. | «Es el mismo lanzamiento, soltado igual, en dos aires: el gris a nivel del mar, el rojo en el Harp Helú.» |
| 10–35 s | Simulador, panel | Señalar ΔStuff+ y "en el plato". Cambiar a cámara Transmisión. | «En el aire de la CDMX la recta sube menos y llega más abajo, y el modelo le quita puntos de Stuff+.» Leer el ΔStuff+ del panel, no una cifra de memoria. |
| 35–60 s | Simulador | Cambiar el preset a **Sweeper** y lanzar. | «El sweeper pierde menos que la liga: la ventaja es relativa, en absoluto todas las formas pierden.» |
| 60–85 s | `/fisica` | Mover la densidad de nivel del mar al Harp Helú. | «Medimos cuánto cae la fuerza de Magnus con el aire: cae más rápido que la densidad. Esa elasticidad medida es la que usa el simulador.» |
| 85–110 s | `/altitud` | Recorrer el forest por forma. | «La pérdida depende de la forma: la recta de mucho ride es la que más pierde; la curva 12-6 y el sweeper, las que menos.» |
| 110–140 s | `/staff` | Mostrar una franquicia candidata a la vez. | «Identificación inferida: las franquicias 5 y 11 son candidatas y nunca se suman. Proponemos mover uso en casa al lanzamiento que mejor aguanta y dar las aperturas de casa al abridor más resistente.» |
| 140–170 s | `/metodologia` | Señalar la tabla contra el nulo. | «Todo se mide contra el modelo nulo de la rúbrica: Stuff+ v2 y Pitching+ le ganan fuera de muestra, por pitcher, por temporada y en una altitud que el modelo no vio.» |
| 170–180 s | Simulador | Volver a la recta de ride. | «La decisión es qué perfil reclutar y qué lanzar en casa. El siguiente paso es confirmar la sede con el club.» |

Cifras para responder si preguntan (no leerlas en la demo, leer la pantalla): ΔStuff+ de la liga −13.0, sweeper −9.6, recta 4S −11.4, recta de ride −17.9 ([memo](../reports/recommendations/memo.md), [deltas](../reports/altitude_delta/delta_by_shape.csv)); habilidad contra el nulo por pitcher: Stuff+ v2 +0.18 %, Pitching+ +3.88 % ([validación](../reports/validation/summary.md)).
El cronograma es un objetivo: no hay evidencia de 40 s ni de 180 s hasta completar el ensayo.

## Fallos y plan B

- Si el sitio no carga o solo ofrece datos de ejemplo, decirlo y pasar al [deck](deck/deck.pdf): las láminas 1, 3, 4 y 8 cuentan la misma historia con capturas del producto.
- Si el 3D va lento en la laptop del jurado, el simulador baja de calidad solo; si no hay WebGL2, muestra la vista 2D del receptor con los mismos datos.
- No simular clics exitosos ni atribuir al mock las cifras oficiales.
- El video `demo/planb.mp4` lo graba una persona; mientras no exista, el PDF es el respaldo estático y no sustituye el video ni el ensayo.
