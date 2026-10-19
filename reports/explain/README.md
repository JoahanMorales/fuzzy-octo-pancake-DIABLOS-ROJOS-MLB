# Explicaciones SHAP de Stuff+ v2 (HACK-080)

Generado por `python -m stuffplus.explain`; ninguna cifra se escribió a mano.

**Qué explica SHAP.** El objetivo es el valor de Stuff+ de producción (v2 con calibración por temperatura, neutral al conteo: promedio sobre los 12 conteos con los pesos de la familia del pitch; HACK-057), en puntos de Stuff+ con la escala de nivel del mar de la liga. Ese valor no es un solo ensamble de árboles, así que lo destilamos en un regresor LightGBM (300 rondas) sobre las variables de Stuff+ v2 sin el conteo, con 180,000 filas: cada lanzamiento de la muestra en su aire, a nivel del mar y en el aire del Harp Helú. TreeSHAP es exacto sobre ese sustituto (base + Σ puntos = Stuff+ del sustituto); la tabla dice cuánto se aleja del Stuff+ v2 real en lanzamientos que no vio.

| Objetivo | n | R² | r | Error medio (puntos) | p95 del error (puntos) |
|---|---|---|---|---|---|
| rho_1.000 | 20,000 | 0.913 | 0.956 | 2.29 | 5.91 |
| rho_0.819 | 20,000 | 0.914 | 0.956 | 2.20 | 5.62 |
| delta_cdmx | 20,000 | 0.794 | 0.891 | 2.60 | 6.50 |

R² del sustituto en su propia muestra: 0.958. El aire se traslada con el traductor físico del modelo (el mismo de `reports/altitude_delta/`), no con Magnus ∝ ρ.

Archivos: `global_importance.csv` (media de |puntos| por variable, lanzamientos en su aire), `fidelity.csv`, `examples.csv` (el lanzamiento mediano de cuatro formas, a nivel del mar y su ΔStuff+ en la CDMX, con las razones para el cuerpo técnico), `beeswarm.png` y `dependence.png`.
Sin datos por lanzamiento: solo agregados y lanzamientos medianos por forma.
