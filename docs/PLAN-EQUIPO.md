# Plan de equipo · Stuff+ 2240 · 10 días (13 → 22 oct 2026)

4 humanos × 2 agentes. El backlog completo está en `.uak/TASKS.md` y el grafo en `docs/backlog-graph.md`. El estado en vivo se ve con `bash .uak/bin/uak board --watch 10`.

## Roles (los nombres H2–H4 están por llenar)
| Humano | Rol | Agente 1 (ola 1 → siguientes) | Agente 2 (ola 1 → siguientes) |
|---|---|---|---|
| **joahan** (lead, entrega) | Núcleo ML | HACK-002 contrato → HACK-010 Stuff+ → HACK-012 Pitching+ → HACK-028 tuning | HACK-001 setup → HACK-029 shapes → HACK-016 scoring → HACK-019 SHAP |
| **H2** | Física y altitud | HACK-004 densidad / Magnus / traducción → HACK-015 ΔStuff+ por shape → HACK-017 perfil ideal | HACK-003 identificar Harp Helú → HACK-009 hipótesis H1–H4 → HACK-018 sensibilidad por pitcher |
| **H3** | Features y validación | HACK-006 arsenal + túnel + secuencia → HACK-011 Location+ → HACK-026 GAM benchmark | HACK-005 baseline + métricas → HACK-013 escala → HACK-014 validación (pitcher / season / park) |
| **H4** | Producto y narrativa | HACK-007 dashboard + design lock → HACK-020 integración → HACK-021 perfilador de prospectos → HACK-024 deploy | HACK-008 documento técnico → HACK-022 memo de recomendaciones → HACK-023 PDF final → HACK-025 demo y entrega |

HACK-027 (Causal Forest, P2) queda para quien termine primero a partir del día 6.

## Calendario
| Días | Meta | Hito verificable |
|---|---|---|
| 1–2 (13–14 oct) | Ola 1: contrato, física, baseline, features, esqueleto del dashboard y doc | `pytest` en verde para HACK-001/002; ρ̂ por juego en `reports/physics/` |
| 3–5 (15–17 oct) | Modelos Stuff+ / Location+ / Pitching+, validación, ΔStuff+ por altitud | Tabla de validación contra el baseline; video plan B v1 el 17 |
| 6–7 (18–19 oct) | Scoring, leaderboards, sensibilidad, dashboard con modelos reales, tuning | Simulador CDMX vs nivel del mar funcionando con modelos reales |
| 8–9 (20–21 oct) | Memo, PDF de 6–10 páginas, deploy, ensayo desde un clon limpio | PDF compilado; dashboard desplegado sin datos crudos |
| 10 (22 oct) | **Freeze a las 17:59**, ensayo, envío del correo | Correo enviado con los correos de los 4 integrantes; acuse guardado |

## Reglas que no se negocian
1. **Los datos crudos NUNCA van a git** (las bases dicen que se muestran resultados, no datos). Cada persona copia el parquet a `data/raw/`.
2. Todo modelo se reporta contra el baseline nulo (xRV medio por conteo) y con los splits de `stuffplus/splits.py`.
3. Ningún número va al PDF ni al dashboard sin un CSV en `reports/` que lo respalde.
4. Windows: usar `python` (no `python3`) y Git Bash para `.uak/bin/*`.

## Arranque de cada laptop
```bash
git pull && python -m venv .venv && .venv/Scripts/pip install "pyarrow>=20" pandas numpy scipy scikit-learn lightgbm shap streamlit plotly matplotlib networkx pytest
bash .uak/bin/doctor
UAK_HUMAN=<tu-nombre> bash .uak/bin/wt new HACK-00X --agent <tu-nombre>-1
```
