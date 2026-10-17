# Contrato web · HACK-038

La app React lee solo agregados JSON. No hay filas de lanzamiento ni parquet.
El mock (`demo_data: true`) lo regenera:

```sh
python stuffplus/export_web.py --mock
```

Eso reescribe `web/public/data/mock/` desde `reports/` y `deploy/bundle/tables/`.
El export con datos de despliegue es HACK-050 (`web/public/data/real/`). Hasta entonces la interfaz lee `mock/`.

## Modelo

Todos los archivos llevan el mismo sobre:

| Campo | Valor en esta ola |
|---|---|
| `model_version` | `stuff_v2` |
| `model` | `pitch_family Stuff+ composite` |
| `translation` | `physics_translator` |
| `demo_data` | `true` en `mock/`, `false` cuando HACK-050 publique `real/` |
| `sources` | rutas de los CSV de donde salió cada cifra |

No se fija el ΔStuff+ de liga en código. `validation.json` → `highlights.league_delta_cdmx` se lee de la fila `Stuff+ v2 (familia)` en `reports/stuff_v2/altitude.csv`. HACK-057 puede cambiar esa cifra antes del congelamiento del 2026-10-20 12:00.

La identidad del arsenal es `pitch_id` (entero por pitcher-temporada). `AutoPitchType` no entra al contrato.

## Archivos

| Archivo | Contenido |
|---|---|
| `parks.json` | 20 parques: `id`, `rho`, `bucket`, `air_effect`, `altitude` |
| `shapes.json` | ΔStuff+ por forma, intervalo y deltas de movimiento |
| `leaderboard.json` | agregados pitcher-temporada |
| `pitcher/<id>.json` | temporadas y arsenal (`arsenal_pitches[].pitch_id`) |
| `staff.json` | franquicias 5 y 11 por separado (`pooled: false`) |
| `validation.json` | highlights, modelos de altitud, reglas de adopción y tabla de validación |
| `physics.json` | por `pitch_family`: C_D, C_L (nivel del mar y extremo) y elasticidad de Magnus |
| `models/stuff.json`, `models/location.json`, `models/pitching.json` | features, categorías, `class_values`, escala Plus (`100 + 10z`, referencia `park-neutral`) y árboles |

Los árboles de `models/*.json` en el mock son un tocón de una partición para que el esquema cierre. HACK-040 los sustituye por `booster.dump_model()` y tiene que respetar `tree_structure` (`split_feature`, `threshold`, `decision_type`, `default_left`, `left_child`, `right_child`, `leaf_value`). El evaluador TypeScript y Python deben coincidir a 1e-6.

## Límites

- El exportador aplica las reglas de `scripts/check_no_raw_data.py`: más de 1,000 filas con `PitchUID` o con tres o más columnas crudas de Trackman se rechaza.
- `web/public/data` pesa como máximo 25 MB.
- El mock de `pitcher/` incluye solo al personal de las franquicias 5 y 11. El leaderboard sí trae todas las temporadas agregadas.

Esquemas: `web/src/contract/types.ts` (zod). `parseContractFile(ruta, json)` elige el esquema por la ruta relativa dentro de `mock/` o `real/`.
