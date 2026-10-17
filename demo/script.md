# Demo Stuff+ 2240 · guion de 3 minutos

Estado: guion preparado; ensayo cronometrado y aceptación en otra laptop pendientes.
Referencia de implementación: Streamlit (`app/pages/1_Simulador.py`); la interfaz React debe ensayarse por separado antes de sustituirla. No se afirma que su despliegue esté listo.

## Preparación del presentador

- Abrir Simulador antes de comenzar; comprobar bundle real y esperar el estado final sin errores. Si aparece `demo_data: true`, decir «demostración con modelo de ejemplo» y no atribuirle resultados oficiales.
- Capturar una entrada ilustrativa, no un pitcher real: Four-Seam, derecho, 95 mph, 2350 rpm, eje 205°, IVB 17 in, HB 8 in, extensión 6.2 ft; plato X=0 ft, Z=2.5 ft, bateador derecho; aire de medición «Nivel del mar». Mantener estos valores durante la comparación.
- Seleccionar «Harp Helú (constante física)» y pulsar **Calcular**. Después de cualquier cambio volver a pulsarlo: la página conserva el resultado anterior hasta recalcular.
- Comprobar que se ven las dos puntuaciones y el movimiento a 1280×720, con movimiento reducido. Leer únicamente cifras del resultado final. Registrar versión/bundle, valores visibles, captura, duración y etiqueta demo en la checklist.
- Abrir también [validación](../reports/validation/summary.md), [deltas por forma](../reports/altitude_delta/delta_by_shape.csv) y [PDF de respaldo](deck/stuffplus2240.pdf). No abrir datos por lanzamiento.

## Recorrido (180 s; objetivo de wow antes de 40 s)

| Tiempo | Acción | Narración |
|---|---|---|
| 0–10 s | Mostrar las dos columnas del Simulador ya calculadas. | «Evaluamos el mismo lanzamiento en dos aires para decidir qué conviene lanzar en casa.» |
| 10–35 s | Señalar Stuff+ de cada ambiente y su cambio de movimiento. | «Esta entrada es ilustrativa. Estos son los dos valores que devuelve el modelo. Cambia el ambiente, conservamos el lanzamiento y el aire donde medimos su movimiento.» Leer los valores visibles, sin sustituirlos por 112/96 de la propuesta. |
| 35–60 s | Abrir Altitud; si falta la tabla, abrir delta_by_shape.csv. | «La sensibilidad depende de la forma: el sweeper pierde 4.6 puntos estimados; una recta 4S pierde 8.7. Perder menos que la liga es una ventaja relativa, no una ganancia absoluta.» |
| 60–85 s | Mostrar Leaderboard, filtro de temporada y arsenal de un ID anónimo disponible. | «100 es el promedio de referencia; 10 puntos son una desviación estándar. Separamos Stuff+, Location+ y Pitching+ y revisamos tamaño de muestra.» |
| 85–115 s | Abrir Staff Diablos, una franquicia candidata a la vez. | «Proponemos revisar la mezcla de lanzamientos en casa. La sede no está confirmada: las franquicias 5 y 11 son alternativas, nunca se suman. Las carreras son escenarios bajo supuestos.» |
| 115–140 s | Mostrar Prospecto con un arsenal disponible; si falta, mostrar el reporte agregado. | «La herramienta sirve para comparar perfiles antes de observar al jugador. La recomendación exige cobertura, incertidumbre y revisión del coach.» |
| 140–170 s | Mostrar summary.md. | «Pitching+ reduce RMSE 3.88 % por pitcher, 3.74 % en 2026 y 3.28 % en altitud extrema frente al promedio por conteo. La preparación es transductiva; aún no es una validación inductiva completa.» |
| 170–180 s | Volver a la comparación inicial. | «La decisión es qué lanzamiento probar y qué perfil observar en casa. El siguiente paso es confirmar sede y validar las recomendaciones con el cuerpo técnico.» |

Fuentes: [escala](../README.md), [validación y límites](../reports/validation/summary.md), [deltas](../reports/altitude_delta/delta_by_shape.csv), [staff](../reports/staff_audit/README.md).
El cronograma es un objetivo; no existe evidencia de haber alcanzado 35 s ni 180 s hasta completar el ensayo.

## Fallos y plan B

Si la app falla, queda cargando o sólo ofrece mocks, anunciarlo y pasar al PDF local. Mostrar fuentes agregadas y límites; no simular clics exitosos ni atribuir al mock las cifras oficiales.
El video `demo/planb.mp4` debe grabarlo una persona; mientras no exista usar el PDF como respaldo estático y registrar que no sustituye el video ni el ensayo.
Para la entrevista de 10 minutos usar [deck y tiempos](deck/README.md) y las [30 preguntas](qa.md).
