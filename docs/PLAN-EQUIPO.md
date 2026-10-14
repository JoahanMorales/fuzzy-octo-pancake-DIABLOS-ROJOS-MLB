# Plan de equipo · Stuff+ 2240 · 10 días (13 → 22 oct 2026)

4 humanos × 2 agentes = 8 agentes.

> **Agentes retirados (2026-10-13):** `victor-3`, `victor-4` y `victor-5` **ya no existen** (los creó por error una sesión anterior). De Victor solo trabajan `victor-1` y `victor-2`, una terminal cada uno. No asignarles tareas ni mensajes: reasignar a `victor-1`/`victor-2`. Sus claims vencidos (p.ej. HACK-007) se recuperan con `uak release ID --expired --read-summary`. Backlog: `.uak/TASKS.md` (36 tareas). Grafo: `docs/backlog-graph.md`. Estado en vivo: `bash .uak/bin/uak board --watch 10`.
`uak next` siempre dice qué sigue; la tabla de abajo es la ruta **sugerida** (el kit reparte según dependencias y rutas libres).

## Quién hace qué
| Humano · herramienta | Frente | Agente 1 | Agente 2 |
|---|---|---|---|
| **Joahan** · Claude Code (lead, responsable del envío) | Núcleo ML | HACK-002 contrato → **HACK-031 esqueleto v0** → HACK-010 Stuff+ → HACK-012 Pitching+ → HACK-028 tuning | HACK-001 setup → HACK-030 run value LMB → HACK-013 escala → HACK-016 scoring → HACK-019 SHAP |
| **Victor** · Claude Code | Física y altitud | HACK-004 densidad / Magnus / traducción → HACK-015 ΔStuff+ por shape → HACK-017 perfil ideal → HACK-033 laboratorio de diseño | HACK-003 **identificar Harp Helú y staff de Diablos** → HACK-009 hipótesis H1–H4 → HACK-018 sensibilidad por pitcher → HACK-032 auditoría del staff |
| **Sebastián** · Codex | Features y validación | HACK-006 arsenal + túnel + secuencia → HACK-011 Location+ → HACK-026 GAM → HACK-027 Causal Forest | HACK-005 baseline + métricas → HACK-029 identidad de pitch → HACK-014 validación → HACK-035 valor de negocio |
| **Luis** · Cursor | Dashboard y producto | HACK-007 dashboard + design lock → HACK-020 integración → HACK-021 prospectos → HACK-034 tarjeta de pitcher → HACK-024 deploy | HACK-008 documento técnico → HACK-036 deck + one-pager → HACK-022 memo → HACK-023 PDF final → HACK-025 demo y envío |

## Calendario
| Días | Meta | Hito verificable |
|---|---|---|
| 1–2 (13–14 oct) | Ola 1 + **esqueleto v0 de punta a punta** | El dashboard muestra un Stuff+ real v0; ρ̂ por estadio; Harp Helú candidato identificado |
| 3–5 (15–17 oct) | Stuff+ / Location+ / Pitching+, validación, ΔStuff+ por altitud | Tabla de validación vs baseline; **video plan B v1 (17 oct)** |
| 6–7 (18–19 oct) | Scoring, staff de Diablos, tarjetas, laboratorio, tuning | Simulador CDMX vs nivel del mar con modelos finales |
| 8–9 (20–21 oct) | Memo, deck, PDF de 6–10 páginas, deploy, ensayo desde clon limpio | PDF compilado; deck listo; dashboard desplegado sin datos crudos |
| 10 (22 oct) | **Freeze 17:59**, ensayo, envío | Correo enviado con los 4 correos (`submission/EQUIPO.local.md`); acuse guardado |

## Tres hallazgos que ya tenemos (y que los otros equipos no van a ver)
1. **La densidad del aire se mide en los datos:** el arrastre de cada lanzamiento da ρ̂ por juego; Extreme ≈ 0.84 del nivel del mar. Mismo pitcher, su recta pierde 3.7" de ride.
2. **Trackman cambia la etiqueta del pitch con la altitud** (−2.8 pp sinkers y changeups, +2.5 pp cutters y sliders, mismos pitchers). Quien compare "por tipo de pitch" con `AutoPitchType` está midiendo mal; nosotros usamos una identidad invariante (HACK-029).
3. **Los estadios y equipos se pueden reconstruir** con las alineaciones de bateadores (~20 equipos, ~45 juegos en casa cada uno). Dos franquicias son siempre las de aire más ligero (CDMX y Puebla) → staff candidato de Diablos.

## Reglas que no se negocian
1. **Los datos crudos NUNCA van a git ni al deploy** (las bases: se muestran resultados, no datos). Cada quien copia el parquet a `data/raw/`.
2. Todo modelo se reporta contra el baseline nulo (xRV medio por conteo) y con los splits de `stuffplus/splits.py`.
3. Ningún número va al PDF, deck o dashboard sin un CSV en `reports/` que lo respalde.
4. Windows: `python` (no `python3`) y Git Bash para `.uak/bin/*`.

## Arranque de cada laptop (una vez)
```bash
git clone git@github.com:JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB.git && cd fuzzy-octo-pancake-DIABLOS-ROJOS-MLB
mkdir -p data/raw   # copia aquí stuff_model_df.parquet
python -m venv .venv && .venv/Scripts/pip install "pyarrow>=20" pandas numpy scipy scikit-learn lightgbm shap streamlit plotly matplotlib networkx pytest
winget install GitHub.cli && gh auth login
bash .uak/bin/doctor
```
Por herramienta:
- **Claude Code (Joahan, Victor):** `claude update` (≥ 2.1.293). Abre Claude en la carpeta del worktree; los hooks ya vienen en `.claude/settings.json`.
- **Codex (Sebastián):** confía en el proyecto una vez para que cargue `.codex/config.toml` y `.codex/hooks.json` (`/hooks` para revisarlos). Codex lee `AGENTS.md` solo.
- **Cursor (Luis):** abre la carpeta del worktree; `.cursor/rules/uak.mdc` y `.cursor/hooks.json` se cargan solos.

Cada agente, por tarea:
```bash
bash .uak/bin/wt new HACK-00X --agent <nombre>-1    # rama + worktree + identidad + claim
```
