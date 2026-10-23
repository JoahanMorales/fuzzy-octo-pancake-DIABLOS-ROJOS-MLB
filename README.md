# Stuff+ 2240

**El primer Stuff+ que respira el aire de la Ciudad de México.**
ISAC Sports Analytics Hackathon 2026 · reto Diablos Rojos: *calidad de pitcheo ajustada por entorno*.

Stuff+ 2240 evalúa cada lanzamiento de la LMB por sus propiedades físicas, su ubicación y su relación con el arsenal del pitcher, y estima cuánto vale **ese mismo pitch** en el aire del Estadio Alfredo Harp Helú (~2,240 m) frente a un estadio a nivel del mar. Escala: 100 = promedio de la liga, 110 = una desviación estándar mejor.

## Producto web (React)

**Sitio publicado: [stuffplus2240.vercel.app](https://stuffplus2240.vercel.app)** (empieza por el [simulador 3D](https://stuffplus2240.vercel.app/#/simulador)).

La entrega es una app React estática: simulador 3D de dos aires, altitud, leaderboard, fichas de pitcher, staff, prospecto, laboratorio, física, metodología y presentación. Corre en el navegador con agregados JSON y modelos de árboles exportados desde Python; no lleva datos por lanzamiento.

```bash
npm --prefix web ci
npm --prefix web run dev            # http://localhost:5173
npm --prefix web test -- --run      # vitest
npm --prefix web run build          # web/dist/
```

Publicación del sitio estático: [`deploy/web/README.md`](deploy/web/README.md). Detalles del frontend: [`web/README.md`](web/README.md).

## Cifras principales (Stuff+ v2)

- **El mismo lanzamiento pierde 13.0 puntos de Stuff+ en el aire del Harp Helú** (promedio de la liga sobre las formas de lanzamiento) (`reports/recommendations/memo.md`).
- **Stuff+ v2 le gana al modelo nulo de la rúbrica por lanzamiento** en las tres particiones: +0.18 %, +0.20 % y +0.23 % de RMSE, con IC que excluyen 0 (`reports/stuff_v2/skill.csv`).
- **La física corrige el sesgo de altitud.** Entrenado sin un solo juego de altitud extrema, el nulo subestima el daño allí en +0.0108 carreras por lanzamiento; Stuff+ v2 deja +0.0018 (`reports/stuff_v2/altitude_bias.csv`).

## Documentos

| Qué | Dónde |
|---|---|
| Documento técnico (paper) | [`docs/technical/paper.md`](docs/technical/paper.md) · [PDF](docs/technical/stuffplus2240.pdf) |
| Presentación ejecutiva v2 | [`demo/deck/deck.pdf`](demo/deck/deck.pdf) · [PPTX](demo/deck/deck.pptx) · [fuentes](demo/deck/README.md) |
| Resumen ejecutivo v2 (one-pager) | [`demo/one-pager/one-pager.pdf`](demo/one-pager/one-pager.pdf) |
| Idea y hallazgos | [`IDEA.md`](IDEA.md) |
| Contratos de datos | [`docs/CONTRACT.md`](docs/CONTRACT.md) · [`docs/CONTRACT-WEB.md`](docs/CONTRACT-WEB.md) |
| Backlog y grafo | [`.uak/TASKS.md`](.uak/TASKS.md) · [`docs/backlog-graph.md`](docs/backlog-graph.md) |

## Instalación

Python ≥ 3.11. Windows: usa Git Bash y `python` (no `python3`).

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # macOS/Linux: .venv/bin/pip
```

`pyarrow >= 20` es obligatorio: con la versión 19 el parquet falla con *Repetition level histogram size mismatch*.

## Datos

Los datos de ISAC **no se publican ni se suben a git** (las bases permiten mostrar resultados, no datos).
Copia `stuff_model_df.parquet` a `data/raw/`. Otra ubicación: `STUFFPLUS_DATA=/ruta/al/archivo.parquet`.
Dentro de un worktree de uak no hace falta otra copia: se usa la del checkout principal.

```python
from stuffplus.io import load_raw
df = load_raw(columns=["year", "pitcher_anon_id", "RelSpeed", "InducedVertBreak"])
```

Sin los datos reales puedes trabajar con datos sintéticos que tienen las mismas 84 columnas y tipos:

```bash
python -m tests.fixtures.synthetic data/sample/synthetic_pitches.parquet
```

## Tests

```bash
python -m pytest -q
```

Los tests usan el fixture `synthetic_pitches` de `tests/conftest.py` (~5,700 lanzamientos simulados en orden de juego, 6 equipos con estadios a 3 altitudes, alineaciones fijas). Nunca necesitan los datos reales. El único test que lee el archivo real verifica su esquema y se omite si el archivo no está.

## Dashboard Streamlit (legado)

La primera versión del producto. Se conserva como respaldo; la entrega es la app React de arriba.

```bash
python -m streamlit run app/Home.py
```

Corre solo con `artifacts/`, sin datos crudos.

## Uso de IA generativa y trabajo de terceros

**IA generativa.** Usamos asistentes de programación con IA generativa, principalmente Claude Code (Anthropic), como agentes que escribieron buena parte del código, los análisis, la app web y los borradores de los documentos. El equipo humano fijó la pregunta, las hipótesis y las reglas de decisión antes de cada corrida, revisó cada cambio y decidió qué modelo pasaba a producción. Ningún dato se generó con IA: todas las cifras salen de los datos oficiales del reto con los scripts del repo y se comprueban de forma automática:

- `python docs/technical/check_numbers.py` comprueba que cada número del paper esté en el archivo de `reports/` que cita.
- `python demo/deck/verify.py` recalcula cada cifra del deck desde su CSV (archivo, fila, columna y SHA-256 en `demo/deck/sources.json`).
- `python -m pytest` y `npm --prefix web test -- --run` cubren el código y la app; los modelos se validan contra el modelo nulo de la rúbrica con pliegues por pitcher.

La coordinación entre agentes usó el [UPIIXIA Agentic Kit](https://github.com/JoahanMorales/upiixia-agentic-kit) (tareas, revisiones y trazabilidad en la rama `claims`).

**Datos.** Trackman de la LMB entregado por el ISAC para el reto; no se publica ni se sube a git ni al sitio (solo agregados).

**Métodos y literatura.** Física del vuelo (Nathan; Kagan), Stuff+ y modelos públicos (FanGraphs, Driveline, Baseball Prospectus, PitchingBot), calibración, cambio de distribución e intervalos conformales: citas completas en la bibliografía del [paper](docs/technical/stuffplus2240.pdf) (`docs/technical/references.bib`).

**Software de terceros.** Python: pandas, NumPy, SciPy, scikit-learn, LightGBM, SHAP, pyGAM, NetworkX, pyarrow, matplotlib, Plotly, Streamlit, python-pptx, ReportLab, PyMuPDF, pytest. Web: React, React Router, three.js, react-three-fiber, drei, postprocessing, D3, Framer Motion, Zod, Phosphor Icons, Vite, Vitest, Testing Library y Playwright. Documentos: pandoc, Tectonic (XeTeX), Beamer, TikZ/pgfplots. Tipografías: Fira Sans, Libertinus, DejaVu Sans, Geist y Barlow Condensed. Cada una con su licencia; las versiones están en `requirements.txt`, `demo/deck/requirements.txt` y `web/package.json`.

## Cómo trabajamos

Cuatro personas y ocho agentes coordinados con el [UPIIXIA Agentic Kit](https://github.com/JoahanMorales/upiixia-agentic-kit) en modo sprint: `bash .uak/bin/uak next` dice qué sigue y `bash .uak/bin/uak board` muestra el tablero.

Equipo: Joahan Samuel Morales Piña · Victor Manuel Ruiz Lopez · Carlos Sebastian Jara Hernandez · Luis Fernando Vargas Maldonado.
