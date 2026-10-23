# Entrega · checklist y acta de ensayo

Estado: paquete documental preparado; entrega NO enviada y aceptación humana pendiente.
Responsable del envío: Joahan. Fuente de requisitos: [PROJECT](../.uak/PROJECT.md); guion: [demo](../demo/script.md); entrevista: [32 preguntas](../demo/qa.md).
Fecha límite oficial: 2026-10-22 23:59 America/Mexico_City; objetivo interno: 2026-10-22 por la mañana. Revalidar con las bases antes de enviar.

## Antes de enviar

- [ ] Fusionar en `main` los PR de HACK-085 (paper en LaTeX), HACK-086 (QA visual), HACK-087 (landing con −13.0) y HACK-088 (deck y one-pager en LaTeX): los PDF finales están en esas ramas. Después, adjuntar los PDF desde `main`.
- [ ] Joahan confirma instrucciones vigentes y correo destino `itamsportsanalytics@gmail.com`.
- [ ] Incluir los cuatro correos del equipo desde `submission/EQUIPO.local.md`, sólo por la persona responsable. Mantener ese archivo ignorado; no copiar correos ni matrícula a git.
- [ ] Revisar PDF técnico de 6–10 páginas: [stuffplus2240.pdf](../docs/technical/stuffplus2240.pdf) (LaTeX, 9 páginas; se reconstruye con `bash docs/technical/build.sh`); abrirlo y confirmar legibilidad y versión.
- [ ] Revisar [leaderboard por pitcher/temporada](../reports/leaderboards/pitcher_season.csv) y [por parque](../reports/leaderboards/by_park.csv), con sus columnas Stuff+/Location+/Pitching+ y referencia.
- [ ] Preparar archivo de scores por pitch: ruta privada, versión, esquema, cobertura y tamaño pendientes. No adjuntar parquet original ni publicar filas privadas.
- [ ] Joahan resuelve por escrito el permiso/canal privado de transferencia de scores por pitch: las bases permiten mostrar resultados, pero no divulgar datos. Si no está claro, consultar al organizador antes de transferir.
- [ ] Publicar `web/dist/` siguiendo [deploy/web](../deploy/web/README.md) (publica Joahan; `python scripts/check_web_dist.py` en verde) y confirmar la URL en una ventana privada con la insignia "datos reales": URL pendiente. No usar localhost como enlace de entrega.
- [ ] Confirmar acceso del jurado al [repositorio](https://github.com/JoahanMorales/Ethical-hoops) y revisar contenido público.
- [ ] Adjuntar o enlazar [deck v2](../demo/deck/deck.pdf), [resumen de una página](../demo/one-pager/one-pager.pdf) y [recomendaciones](../reports/recommendations/memo.md); comprobar que dicen Stuff+ v2 (liga −13.0).
- [ ] Tener listas constancias de inscripción/matrícula de cuatro miembros por canal privado; no versionarlas.
- [ ] Una persona graba `demo/planb.mp4`, lo reproduce completo y comprueba audio, duración y acceso. Estado actual: pendiente.
- [ ] Dos personas revisan correo, adjuntos, enlaces y restricciones de datos antes de enviarlo.

## Ensayo desde clon limpio en otra laptop

Pendiente: no se ha ejecutado este ensayo. La verificación automática de documentación no lo sustituye.

1. En otra laptop, clonar el repo a una carpeta nueva y registrar SHA, SO, arquitectura y versión Python (≥3.11). No copiar `.env` ni datos crudos.
2. Crear entorno e instalar dependencias con los comandos de [README](../README.md). Medir instalación y arranque; objetivo total ≤5 min, pendiente de comprobar.
3. La app web trae sus agregados y modelos en `web/public/data/` (versionados, sin datos crudos): `npm --prefix web ci && npm --prefix web run build && npm --prefix web run preview`. Registrar el puerto que imprime.
4. Abrir también el sitio publicado, si ya existe, desde esa laptop.
5. Navegador a 1280×720. Ejecutar el [guion](../demo/script.md) y esperar el estado final de cada pantalla; repetir una pasada con movimiento reducido.
6. Comprobar ambas puntuaciones, movimiento, unidades y estado real/mock. Probar sin red una vez cargados modelos y agregados, sin raw data.
7. Medir primer wow ≤40 s y flujo ≤180 s; abrir PDF si hay fallo y registrar el fallo. El respaldo no convierte el ensayo fallido en aprobado.
8. Repetir tras arreglar cualquier bloqueo y registrar evidencia nueva; la persona que ensaya confirma el acta.

| Evidencia | Registro |
|---|---|
| Persona / otra laptop / fecha | Pendiente |
| SHA / SO / arquitectura / Python | Pendiente |
| Bundle: versión, SHA-256 y origen autorizado | Pendiente |
| Instalación + arranque / puerto / URL local | Pendiente |
| Navegador / viewport / movimiento reducido | Pendiente |
| Estado demo_data / captura final / dos scores visibles | Pendiente |
| Segundos al wow / duración total | Pendiente |
| Prueba sin red y sin raw / fallos / repetición | Pendiente |
| Video: ubicación privada o enlace / reproducción | Pendiente |
| Veredicto del ensayo y persona responsable | Pendiente |

## Envío y recepción (persona responsable)

- [ ] Enviar correo con cuatro emails, PDF, scores por canal aprobado, leaderboards y enlaces confirmados.
- [ ] Guardar fecha/hora, Message-ID y comprobante de recepción por canal privado; aquí registrar sólo estado y referencia sin PII.
- [ ] Si no llega confirmación, dar seguimiento humano antes del cierre.

Comprobante: pendiente. No marcar enviada por tener este archivo o por pasar `test -s`.

## Comprobaciones de archivos públicos

Ejecutar desde la raíz; estos checks sólo prueban existencia, no aceptación del contenido ni permisos de transferencia.

```bash
test -s submission/checklist.md && test -s demo/script.md && test -s demo/qa.md
test -s docs/technical/stuffplus2240.pdf && test -s demo/deck/deck.pdf && test -s demo/one-pager/one-pager.pdf
test -s reports/leaderboards/pitcher_season.csv && test -s reports/leaderboards/by_park.csv
```

La entrega permanece pendiente mientras haya casillas abiertas. No empaquetar automáticamente `data/`, archivos locales del equipo ni scores por lanzamiento.
