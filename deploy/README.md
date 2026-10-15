# Deploy del dashboard (HACK-024)

El dashboard público muestra **solo agregados**: modelos LightGBM en texto, tablas agregadas (`deploy/bundle/`) y los
CSV de `reports/`. Los datos crudos de ISAC nunca salen de la laptop.

## Antes de publicar (cada vez)

```sh
python deploy/build_bundle.py                    # copia artifacts/bundle → deploy/bundle y corre el verificador
python scripts/check_no_raw_data.py              # falla si hay parquet/pkl/rds o tablas por lanzamiento (> 1,000 filas)
python -m pytest -q tests/test_no_raw_data.py
```

Para probar localmente como en la nube, con el bundle versionado y sin datos crudos:

```sh
STUFFPLUS_BUNDLE=deploy/bundle STUFFPLUS_DATA=/nonexistent streamlit run app/Home.py
```

## Publicar en Streamlit Community Cloud (lo hace el humano responsable: joahan)

Publicar es una decisión humana: crear la cuenta, autorizar GitHub y elegir la visibilidad no lo hace ningún agente.

1. En share.streamlit.io, entrar con la cuenta de GitHub que tiene acceso al repo privado.
2. **New app**: repo `JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB`, rama `main`, archivo `app/Home.py`, Python 3.12.
3. **Advanced settings → Secrets**: pegar el contenido de `deploy/streamlit_settings.example.toml`.
4. **Deploy**. Luego, en *Share*, dejar la app sin listar: solo con el enlace. Las apps de repos privados son privadas
   por defecto; para el jurado, invitar sus correos o activar el acceso por enlace.
5. Copiar el enlace en el `README.md` principal y en `submission/checklist.md` (HACK-025).

## Si la nube falla (respaldo local)

```sh
git clone git@github.com:JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB.git && cd fuzzy-octo-pancake-DIABLOS-ROJOS-MLB
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt     # Windows; en macOS/Linux: .venv/bin/pip
STUFFPLUS_BUNDLE=deploy/bundle streamlit run app/Home.py                  # http://localhost:8501
```

No hace falta el parquet: todas las páginas corren con `deploy/bundle` y `reports/`. La vista opcional de lanzamientos
crudos en *Altitud* solo aparece si existe el archivo local de datos, y en la nube `STUFFPLUS_DATA` apunta a un archivo
inexistente.

## Qué contiene el bundle

`manifest.json` (versión, SHA, variables de cada modelo), `models/*.txt` (LightGBM en texto: árboles, sin
filas de datos) y `tables/*.csv` (agregados: formas, parques, buckets de altitud y pitcher-temporada con ids anónimos). Tamaño: el
que imprime `check_no_raw_data.py`, con un límite de 100 MB.
