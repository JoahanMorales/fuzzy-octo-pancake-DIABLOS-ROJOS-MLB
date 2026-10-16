# Calibración de probabilidades (HACK-053)

Generado por `python -m analysis.calibration.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.

Los árboles potenciados deforman las probabilidades (Niculescu-Mizil y Caruana 2005). Probamos dos correcciones sobre los 5 resultados (bola, strike cantado, swing fallido, foul, en juego): **temperatura** (un parámetro, conserva el orden; Guo et al. 2017) e **isotónica uno contra todos** renormalizada. Siempre **anidado**: el calibrador se ajusta con predicciones fuera de pliegue dentro del entrenamiento y nunca ve a los pitchers que evalúa (5 pliegues externos por pitcher, 3 internos).

| Modelo | Método | Log-loss | ECE por clase | Pendiente xRV | Habilidad vs nulo | 50 → resto | 200 → resto | Mitad contra mitad |
|---|---|---|---|---|---|---|---|---|
| Stuff+ v1 | sin calibrar | 1.5013 | 0.0091 | 0.69 | -0.025 % [-0.051, +0.004] | 0.265 | 0.306 | 0.807 |
| Stuff+ v1 | temperatura | 1.5007 | 0.0092 | 0.73 | -0.029 % [-0.052, +0.001] | 0.264 | 0.306 | 0.800 |
| Stuff+ v1 | isotónica | 1.4988 | 0.0020 | 0.88 | -0.003 % [-0.025, +0.022] | 0.258 | 0.297 | 0.781 |
| Location+ | sin calibrar | 1.0419 | 0.0048 | 0.92 | +2.783 % [+2.708, +2.871] | 0.119 | 0.182 | 0.565 |
| Location+ | temperatura | 1.0417 | 0.0041 | 0.94 | +2.791 % [+2.719, +2.880] | 0.120 | 0.181 | 0.566 |
| Location+ | isotónica | 1.0413 | 0.0023 | 0.94 | +2.797 % [+2.726, +2.880] | 0.122 | 0.182 | 0.558 |

## Decisión (regla fijada antes de correr; `decision.csv`)

- **Stuff+ v1: sin calibrar**.
  - temperatura: no cumple: nivel pitcher no baja.
  - isotónica: no cumple: nivel pitcher no baja.
- **Location+: temperatura**.
  - temperatura: pasa.
  - isotónica: no cumple: nivel pitcher no baja.

El nivel pitcher de Stuff+ v2 usa su valor integrado sobre conteos (`stuff_value`); el de los demás, el xRV.
El calibrador elegido se aplica en producción en HACK-057 con `stuffplus.calibration.fit_nested`. Stuff+ v2 (HACK-052) se evalúa con este mismo script (`--models stuff_v2`) cuando esté integrado; HACK-057 aplica su veredicto.
