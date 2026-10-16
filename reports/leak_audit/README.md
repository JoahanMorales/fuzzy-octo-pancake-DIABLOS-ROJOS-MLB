# Auditoría de fugas: ¿cuánto del AUC es ubicación? (HACK-054)

Generado por `python -m analysis.leak_audit.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.

El ángulo de llegada vertical (VAA) es física, pero casi toda su variación es *dónde* cruzó el plato el lanzamiento y desde qué altura salió. Un modelo que ve el VAA crudo ve la ubicación. Medimos cuánto pesa eso con validación fuera de pliegue por pitcher (5 pliegues).

| Variables | AUC swing fallido (IC 95 %) | Stuff+: habilidad vs nulo | 50 → resto | 200 → resto | Mitad contra mitad |
|---|---|---|---|---|---|
| Solo física | 0.642 [0.638, 0.647] | -0.025 % [-0.051, +0.004] | 0.265 | 0.306 | 0.807 |
| + VAA/HAA crudos | 0.738 [0.734, 0.741] | +2.184 % [+2.111, +2.270] | 0.247 | 0.323 | 0.749 |
| + VAA/HAA netos de ubicación | 0.672 [0.668, 0.677] | +0.634 % [+0.590, +0.679] | 0.264 | 0.322 | 0.800 |
| + diferencias por mano del bateador | 0.641 [0.638, 0.646] | -0.032 % [-0.054, -0.004] | 0.263 | 0.286 | 0.808 |
| + ubicación en el plato (techo) | 0.747 [0.743, 0.750] | no permitido en Stuff+ | - | - | - |

**Lectura.** Agregar el VAA crudo sube el AUC de 0.642 a 0.738; quitarle lo que explican la ubicación y la salida lo deja en 0.672, y ver la ubicación directamente da 0.747. La ubicación y la altura de salida explican entre 66 % y 86 % de la varianza del VAA según la familia (`r2.csv`). Un AUC alto con VAA crudo mide en buena parte *dónde* se lanzó, no *qué* se lanzó.

## Decisión para Stuff+ en producción (regla fijada antes de correr; `decision.csv`)

- **+ VAA/HAA netos de ubicación: no adoptar**.
- **+ diferencias por mano del bateador: no adoptar**.
- **+ VAA/HAA crudos: no adoptar** (lleva ubicación: nunca en Stuff+).

## Límites
- Las diferencias por mano usan la recta principal de la temporada (rasgos físicos, sin resultados), preparadas una vez como las demás variables de arsenal.
- Stuff+ v2 (HACK-052) recibe las variables adoptadas en HACK-057; aquí se mide con la arquitectura v1.
