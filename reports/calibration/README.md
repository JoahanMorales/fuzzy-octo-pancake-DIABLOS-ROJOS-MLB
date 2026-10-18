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
| Pitching+ (componentes) | sin calibrar | 0.9924 | 0.0048 | 0.92 | +3.370 % [+3.288, +3.475] | 0.243 | 0.344 | 0.631 |
| Pitching+ (componentes) | temperatura | 0.9925 | 0.0043 | 0.94 | +3.383 % [+3.303, +3.488] | 0.243 | 0.345 | 0.628 |
| Pitching+ (componentes) | isotónica | 0.9919 | 0.0026 | 0.94 | +3.394 % [+3.314, +3.495] | 0.244 | 0.346 | 0.621 |
| Stuff+ v2 | sin calibrar | 1.4372 | 0.0068 | 0.80 | +0.178 % [+0.147, +0.215] | 0.269 | 0.323 | 0.803 |
| Stuff+ v2 | temperatura | 1.4368 | 0.0056 | 0.83 | +0.185 % [+0.157, +0.221] | 0.269 | 0.323 | 0.798 |
| Stuff+ v2 | isotónica | 1.4362 | 0.0023 | 0.89 | +0.193 % [+0.168, +0.225] | 0.266 | 0.322 | 0.787 |

## Decisión (regla fijada antes de correr; `decision.csv`)

- **Stuff+ v1: sin calibrar**.
  - temperatura: no cumple: nivel pitcher no baja.
  - isotónica: no cumple: nivel pitcher no baja.
- **Location+: temperatura**.
  - temperatura: pasa.
  - isotónica: no cumple: nivel pitcher no baja.
- **Pitching+ (componentes): sin calibrar**.
  - temperatura: no cumple: log-loss baja.
  - isotónica: no cumple: nivel pitcher no baja.
- **Stuff+ v2: temperatura**.
  - temperatura: pasa.
  - isotónica: no cumple: nivel pitcher no baja.

Pitching+ se calibra en su composición de 5 resultados (`PitchingComponents`, la misma forma que Stuff+, con ubicación y contexto); la calidad del bateador se aprende solo con el entrenamiento de cada pliegue. La combinación de 8 objetivos de HACK-012 se ajusta encima de estas probabilidades y no se recalibra aquí.

El nivel pitcher de Stuff+ v2 usa su valor integrado sobre conteos (`stuff_value`); el de los demás, el xRV.
El calibrador elegido se aplica en producción en HACK-057 con `stuffplus.calibration.fit_nested`. Stuff+ v2 (HACK-052) se evalúa con este mismo script (`--models stuff_v2`) cuando esté integrado; HACK-057 aplica su veredicto.
