# Jurado · 30 preguntas y respuestas

Cifras de reportes versionados; preparación exploratoria/transductiva. Cada respuesta ocupa dos líneas: explicación y fuente. No convertir una estimación en promesa de campo.

## Pitching coach

1. **¿Qué decisión cambia mañana?**
   Revisar con el coach qué pitch pierde menos en casa y ensayar un ajuste de mezcla; el escenario mueve hasta 10 puntos porcentuales de uso, no ordena eliminar un pitch.
   Fuente: [staff y supuestos](../reports/staff_audit/README.md).
2. **¿Qué significa Stuff+ 110?**
   Una desviación estándar por encima del promedio de referencia 100; no significa 10 % más victorias.
   Fuente: [escala](../README.md).
3. **¿Qué le pasa a la recta en altura?**
   En el ajuste empírico Extreme−No, su IVB cambia −3.54 in [−3.60, −3.46]; la velocidad de llegada aumenta 1.30 mph.
   Fuente: [física y límites del intervalo](../reports/physics/README.md).
4. **¿Entonces gana el sweeper?**
   Pierde 4.6351 puntos frente al mar, menos que otras formas: su ventaja es relativa; no mejora en términos absolutos.
   Fuente: [fila sweeper, delta_stuff](../reports/altitude_delta/delta_by_shape.csv).
5. **¿Todas las rectas sufren igual?**
   No; la fila 4S pierde 8.7259 puntos en promedio. El movimiento propio y el perfil importan, no sólo la etiqueta.
   Fuente: [fila 4S](../reports/altitude_delta/delta_by_shape.csv).
6. **¿Cómo captura el coach un pitch?**
   Con unidades explícitas: mph, rpm, grados, pulgadas y pies; declara el aire de medición y pulsa Calcular después de cambiar cualquier entrada.
   Fuente: [formulario del simulador](../app/pages/1_Simulador.py).
7. **¿Cambian al abridor por el score?**
   La franquicia 11 mantiene el orden de sus cinco abridores entre casa y visita; el escenario redistribuye aperturas bajo restricciones.
   Fuente: [rotación candidata](../reports/staff_audit/README.md).
8. **¿Es una recomendación lista para juego?**
   Es una hipótesis para bullpen y observación del coach; los intervalos no incluyen toda la incertidumbre física ni una intervención real.
   Fuente: [advertencias físicas](../reports/physics/README.md).

## Director deportivo / GM

9. **¿A quién conviene reclutar?**
   A perfiles cuyo arsenal conserve valor en el aire de casa, revisando cobertura y comparables; no hay garantía contractual de rendimiento.
   Fuente: [perfil físico](../docs/technical/paper.md).
10. **¿Es realmente el staff de Diablos?**
    No está confirmado: las franquicias anónimas 5 y 11 son candidatas de aire ligero; deben validarse con el club.
    Fuente: [identificación y separación](../reports/staff_audit/README.md).
11. **¿Cuánto se ganaría?**
    Los escenarios estiman 3.2 carreras/0.23 victorias para franquicia 11 y 4.4/0.30 para franquicia 5; son alternativas y no se suman.
    Fuente: [totales y supuestos](../reports/staff_audit/README.md).
12. **¿Una carrera vale lo mismo en todos los parques?**
    No; el escenario del staff usa 14.3 carreras por victoria para altitud extrema, una conversión estimada en LMB.
    Fuente: [conversión usada](../reports/staff_audit/README.md).
13. **¿Puedo comparar ligas con este 100?**
    La referencia es LMB por temporada; 100 no establece equivalencia con MLB ni con una liga no calibrada.
    Fuente: [definición de escala](../docs/technical/paper.md).
14. **¿Qué se puede entregar sin exponer la base?**
    Modelos y agregados revisados; el archivo por pitch debe pasar por revisión de reglas y canal privado autorizado, sin publicarlo en repo o dashboard.
    Fuente: [reglas y entregables](../.uak/PROJECT.md).
15. **¿Quién hace el envío final?**
    Joahan es responsable de submission; faltan confirmación de enlaces, cuatro correos, pruebas de matrícula y comprobante de recepción.
    Fuente: [checklist operativa](../submission/checklist.md).

## Ciencia de datos

16. **¿Cuál es el baseline?**
    El xRV medio por conteo, ajustado sólo en entrenamiento; la habilidad es reducción de RMSE contra ese nulo.
    Fuente: [definición y tabla](../reports/validation/summary.md).
17. **¿Qué mejora fuera de muestra reportan?**
    Pitching+: 3.88 % por pitcher [3.78, 4.00], 3.74 % por temporada y 3.28 % por altitud extrema; condicionado a preparación transductiva.
    Fuente: [resultados y límites](../reports/validation/summary.md).
18. **¿Y Stuff+ supera al nulo?**
    Por lanzamiento no: −0.03 % en pitcher holdout; no usa conteo ni ubicación. No transferimos a Stuff+ la mejora de Pitching+.
    Fuente: [comparación de modelos](../reports/validation/summary.md).
19. **¿Hay sobreajuste o fuga?**
    Los modelos se entrenan por partición, pero targets, densidad, identidad y arsenal se preparan globalmente; falta evaluación inductiva con toda preparación dentro del fold.
    Fuente: [límites transductivos](../reports/validation/summary.md).
20. **¿Cómo probaron robustez temporal y geográfica?**
    Entrenar 2024–25 y evaluar 2026; entrenar No+Medium y evaluar Extreme. Leave-one-park-out rápido mejora Pitching+ en 20/20 parques inferidos.
    Fuente: [particiones y corrida rápida](../reports/validation/summary.md).
21. **¿Qué hicieron con el label shift de Trackman?**
    Comparan identidades por forma; Sinker cambia −2.81 pp como AutoPitchType frente a +0.17 pp por familia. No basta controlar por etiqueta original.
    Fuente: [label_shift.csv, fila Sinker](../reports/shapes/label_shift.csv).
22. **¿Por qué no entrenar con MLB?**
    La referencia y los pesos de carrera se calibran a LMB para este reto; no se incorporan datos MLB externos al entrenamiento.
    Fuente: [alcance y targets](../IDEA.md).
23. **¿Cuál es la evidencia de estabilidad?**
    Stuff+ correlaciona 0.707 de 2024→2025 y 0.711 de 2025→2026; es estabilidad de la corrida rápida, no causalidad ni garantía individual.
    Fuente: [estabilidad](../reports/validation/summary.md).
24. **¿Está calibrado para cualquier uso?**
    La mejora de RMSE no prueba calibración de todas las probabilidades; hay que revisar métricas y método por componente antes de tomar decisiones.
    Fuente: [discusión de calibración](../docs/technical/paper.md).

## Física

25. **¿Cómo miden la densidad sin meteorología?**
    Usan mediana por juego de Cd-proxy de rectas, relativa a juegos sin altitud; con menos de 30 rectas encogen al promedio del bucket.
    Fuente: [estimador](../reports/physics/README.md).
26. **¿Qué densidades encontraron?**
    Medias relativas 1.001, 0.892 y 0.841 para No, Medium y Extreme; son estimaciones por ambiente, no mediciones meteorológicas directas.
    Fuente: [rho por bucket](../reports/physics/README.md).
27. **¿Qué confianza tienen en identificar Harp Helú?**
    La referencia agrupada 0.819 tiene IC 0.814–0.824, pero ese intervalo no resuelve la identidad CDMX/Puebla; falta confirmación externa del club.
    Fuente: [advertencia de identidad](../reports/physics/README.md).
28. **¿Menos aire sólo cambia Magnus?**
    Cambia arrastre y Magnus; la recta frena menos y curva menos. El simulador no debe interpretarse como prueba de un cambio causal de resultados.
    Fuente: [ecuaciones y resultados](../reports/physics/README.md).
29. **¿La física está completamente validada?**
    No: Cd-proxy cae ~16 % y Cl-proxy ~24 %; el residuo puede ser Reynolds/giro o calibración Trackman, que estos datos no distinguen.
    Fuente: [validación parcial Cl/Cd](../reports/physics/README.md).
30. **¿Qué cubren sus intervalos?**
    Los IC físicos propagan incertidumbre del coeficiente de densidad, no toda la de Δρ o identidad; se necesitan validación prospectiva y análisis de sensibilidad.
    Fuente: [alcance de los IC](../reports/physics/README.md).
