# Lessons (uak learn)

Append-only. Format: - N | epoch | agent | task | paths | text. `uak recall` and `uak next` show the ones for your paths.

- 1 | 1792182957 | joahan-1 | HACK-052 | stuffplus/models/stuff_v2.py,analysis/stuff_v2/,reports/stuff_v2/,tests/test_stuff_v2.py | Stuff+ sin conteo nunca supera al nulo por conteo por lanzamiento · stuffplus/models/ · usar stuff_v2: el conteo valora resultados + recentrado por conteo; reportar como valor incremental --paths stuffplus/models/
- 2 | 1792182976 | joahan-1 | HACK-052 | stuffplus/models/stuff_v2.py,analysis/stuff_v2/,reports/stuff_v2/,tests/test_stuff_v2.py | Los fixtures de paridad TS vs Python con filas del parquet son datos por lanzamiento en git (no los atrapa el limite de 1000 filas) · web/, tests/ · generar golden sinteticos --paths web/,tests/
- 3 | 1792182995 | joahan-1 | HACK-052 | stuffplus/models/stuff_v2.py,analysis/stuff_v2/,reports/stuff_v2/,tests/test_stuff_v2.py | La consola de Windows (cp1252) truena al imprimir rho/Delta · analysis/*/run.py · escribir el texto a archivo con utf-8 y solo imprimir la ruta --paths analysis/
- 4 | 1792183015 | joahan-1 | HACK-052 | stuffplus/models/stuff_v2.py,analysis/stuff_v2/,reports/stuff_v2/,tests/test_stuff_v2.py | Heredoc en Git Bash con comillas o backslash falla en silencio · scripts largos · escribir el archivo con el editor y correrlo con python
- 5 | 1792183086 | joahan-1 | - | - | forget #4
- 6 | 1792183104 | joahan-1 | - | - | forget #3
- 7 | 1792183123 | joahan-1 | - | - | forget #2
- 8 | 1792183142 | joahan-1 | HACK-052 | web/,tests/,stuffplus/export_trees.py | Los fixtures de paridad TS vs Python con filas del parquet son datos por lanzamiento en git (el limite de 1000 filas no los atrapa) · generar golden sinteticos
- 9 | 1792183160 | joahan-1 | HACK-052 | analysis/ | La consola de Windows (cp1252) truena al imprimir rho o Delta · escribir el texto a archivo utf-8 y solo imprimir la ruta
- 10 | 1792183179 | joahan-1 | HACK-052 | scripts/,analysis/ | Heredoc en Git Bash con comillas o backslash falla en silencio · escribir el script con el editor y correrlo con python
- 11 | 1792187357 | joahan-1 | HACK-037 | web/ | UI: cargar la skill design-taste-frontend antes de disenar o revisar; nada con look de plantilla (pedido de joahan)
- 12 | 1792268771 | luis-2 | HACK-044 | web/src/features/simulador/scene/ | prospect CSV snake_case · stuffplus/prospect.py:_from_mapping · leer rel_height/rel_side/extension además de Trackman; default rel_side=1.8 debe ser lado del brazo en zurdos (web HACK-048 ya lo hace)
- 13 | 1792314094 | joahan-3 | HACK-045 | web/src/features/simulador/flight/,web/src/features/simulador/panel/,web/src/features/simulador/index.tsx | Stuff+ v2 is non-linear: a shape's centroid misses its mean ΔStuff+ · simulador/flight/presets.ts · search near the shapes.csv centroid; stuff.json itself matches delta_by_shape.csv within 0.25
- 14 | 1792374916 | luis-1 | HACK-051 | web/e2e/ | Verify de HACK-051 desde la raiz (npx --prefix web playwright test) recoge los .test.tsx de vitest · web/e2e · usar npm --prefix web run build && npm --prefix web run e2e
