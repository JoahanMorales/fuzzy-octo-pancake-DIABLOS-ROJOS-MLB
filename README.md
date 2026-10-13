# Stuff+ 2240

**El primer Stuff+ que respira el aire de la Ciudad de México.**
ISAC Sports Analytics Hackathon 2026 · reto Diablos Rojos: *calidad de pitcheo ajustada por entorno*.

Stuff+ 2240 evalúa cada lanzamiento de la LMB por sus propiedades físicas, su ubicación y su relación con el arsenal del pitcher, y estima cuánto vale **ese mismo pitch** en el aire del Estadio Alfredo Harp Helú (~2,240 m) frente a un estadio a nivel del mar. Escala: 100 = promedio de la liga, 110 = una desviación estándar mejor.

| Qué | Dónde |
|---|---|
| Idea, flujo de demo y hallazgos | [`IDEA.md`](IDEA.md) |
| Plan del equipo y calendario | [`docs/PLAN-EQUIPO.md`](docs/PLAN-EQUIPO.md) |
| Backlog (36 tareas) y grafo | [`.uak/TASKS.md`](.uak/TASKS.md) · [`docs/backlog-graph.md`](docs/backlog-graph.md) |
| Contrato de datos y API | `docs/CONTRACT.md` (HACK-002) |
| Documento técnico | `docs/technical/` (HACK-008 / HACK-023) |

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

## Dashboard

```bash
python -m streamlit run app/Home.py
```

(HACK-007 / HACK-020; corre solo con `artifacts/`, sin datos crudos.)

## Cómo trabajamos

Cuatro personas y ocho agentes coordinados con el [UPIIXIA Agentic Kit](https://github.com/JoahanMorales/upiixia-agentic-kit) en modo sprint: `bash .uak/bin/uak next` dice qué sigue y `bash .uak/bin/uak board` muestra el tablero.

Equipo: Joahan Samuel Morales Piña · Victor Manuel Ruiz Lopez · Carlos Sebastian Jara Hernandez · Luis Fernando Vargas Maldonado.
