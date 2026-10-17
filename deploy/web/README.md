# Deploy estático de la web (HACK-050)

La app React es un sitio estático: `base: './'` y `HashRouter`, así que `web/dist/` funciona en cualquier hosting
sin reglas de reescritura. Solo lleva agregados JSON; los datos crudos nunca salen de la laptop.

**Publica el humano (joahan).** Ningún agente sube el sitio ni crea cuentas.

## 1. Generar los datos y el build

Desde la raíz del repo, con el venv activo:

```bash
python -m analysis.export_web.run
```

Escribe `web/public/data/real/` (agregados con `demo_data: false` y una página por pitcher) y revisa que todo
`web/public/data` quede en 25 MB o menos. Los modelos del navegador ya están en `web/public/data/models/`
(HACK-040; se regeneran con `python -m stuffplus.export_trees`).

```bash
npm --prefix web ci && npm --prefix web run build
```

```bash
python scripts/check_web_dist.py
```

Debe imprimir `WEB_DIST_OK`. Si falla, no se publica: el mensaje dice qué archivo trae filas de lanzamiento o si
el build pasa de 25 MB.

## 2. Publicar `web/dist/` (elige uno)

| Opción | Pasos | Nota |
|---|---|---|
| Netlify Drop | Abrir app.netlify.com/drop y arrastrar la carpeta `web/dist/` | Lo más rápido; da una URL pública al instante |
| Vercel | `npx vercel deploy web/dist --prod` (pide iniciar sesión) | Proyecto estático, sin framework |
| GitHub Pages | Subir el contenido de `web/dist/` a la rama `gh-pages` y activar Pages en Settings | En repos privados Pages necesita plan de pago |

La URL que se entrega al jurado es la del sitio publicado; el repo sigue privado.

## 3. Qué lee la app

- Si existe `data/real/manifest.json`, la app lee `data/real/` y la insignia dice "datos reales".
- Si no, lee `data/mock/` y la insignia dice "ejemplo" (`demo_data: true`).
- Los modelos se leen de `data/models/` en los dos casos (`manifest.json` → `models_dir`).
- `data/real/validation_extra.json` (solo en `real/`): pliegues por pitcher, parque fuera, calibración y auditoría de fugas para la metodología.

## 4. Antes de cada publicación

1. Volver a correr el export después de cualquier cambio de modelo (HACK-057 adopta Stuff+ v2 y reexporta los
   modelos del navegador).
2. `python scripts/check_web_dist.py` en verde.
3. Abrir el sitio publicado en una ventana privada y revisar que la insignia diga "datos reales".
