# PROJECT · Stuff+ 2240 — ISAC Hackathon 2026 · Diablos Rojos (sprint mode)

> Filled in by `/uak-setup` with the human at minute 0. uak reads the flat fields of the last block from
> the remote `main`, so a stale worktree can never change permissions.

## Event
| Field | Value |
|---|---|
| Event / challenge | ISAC Sports Analytics Hackathon 2026 · Diablos Rojos: *Stuff Plus Model, calidad de pitcheo ajustada por entorno* |
| Start | 2026-10-12 23:00 America/Mexico_City (our kickoff; official event window 2026-07-11 → 2026-11-12) |
| Official deadline | 2026-10-22 23:59 America/Mexico_City (**hour TO CONFIRM**) · platform: email to itamsportsanalytics@gmail.com with ALL member emails |
| Freeze | Thu 2026-10-22 17:59 (`Freeze-Epoch` below) |
| Clean rehearsal / plan B | 2026-10-22 21:59 |
| Internal submission | 2026-10-22 22:59 (target: send on 2026-10-22 morning) |
| Humans | `joahan` (Joahan Samuel Morales Piña · Claude Code · lead ML, **submission owner**) · `victor` (Victor Manuel Ruiz Lopez · Claude Code · physics & altitude) · `sebastian` (Carlos Sebastian Jara Hernandez · Codex · features & validation) · `luis` (Luis Fernando Vargas Maldonado · Cursor · dashboard & product) · emails in git-ignored `submission/EQUIPO.local.md` |
| Agents | `joahan-1, joahan-2, victor-1, victor-2, sebastian-1, sebastian-2, luis-1, luis-2` |
| Machines | 4 laptops (Windows + Git Bash) · Streamlit port 8501 + `$UAK_PORT` |
| Finalists / final | finalists announced 2026-11-02 · final (10-min jury interview) 2026-11-11 |

## Official rubric (weights sum to 100)
| ID | Criterion | Weight | Evidence in the demo |
|---|---|---:|---|
| C1 | Stuff+ model quality: calibrated, discriminates good vs bad pitches; RMSE + calibration in holdout; beats null baseline (mean xRV by count) | 25 | `reports/validation/` table: model vs null baseline, calibration curves |
| C2 | Out-of-sample robustness: pitcher holdout + park holdout (+ season holdout) correctly reported | 25 | validation suite (HACK-014), tech doc §5 |
| C3 | Arsenal + altitude integration: relational arsenal features; altitude effect quantified with LMB evidence; ΔStuff+ per pitch shape Harp Helú vs sea level | 25 | HACK-004/009/015 tables + dashboard side-by-side |
| C4 | Real applicability: pitching coach / GM would change recruiting & tactics (10-min jury interview) | 25 | Dashboard simulator, prospect profiler, recommendations memo |

## Event rules
| Topic | Confirmed rule | Source |
|---|---|---|
| Data | ISAC/Diablos data only for the competition; **results may be shown, data may NOT** → raw data never in git (`.gitignore`), deploy ships only models + aggregates | challenge page, Disclaimers |
| Team | 2–4 members, all enrolled in licenciatura/maestría (proof needed if we win) | challenge page |
| Ethics | No betting use; anonymized IDs only; no PII | challenge page |
| Deliverables | 1) Stuff+/Location+/Pitching+ per pitch, pitcher, arsenal; CDMX vs other parks · 2) ideal physical profile · 3) operational recs · 4) dashboard simulator · 5) technical doc 6–10 pages | challenge page |

## Plan B
- Screen recording of the dashboard flow at `demo/planb.mp4` (v1 on 2026-10-17, final 2026-10-22). Use it if Streamlit Cloud or the network fails; dashboard also runs locally from `artifacts/` with no raw data.

## Executable config
A human sets `yes`. A missing field means `no`.

```text
Mode: sprint
Backlog-Proposed-Epoch: 0
Backlog-Approved: no
Autonomy: yes
Auto-Merge: yes
Review-Mode: claims
Plan-Channel: claims
Freeze-Epoch: 1792691940
Lease-Seconds: 2700
Review-Lease-Seconds: 14400
Events-Per-Session: 100
Checkpoint-Percent: 60
Merge-Lease-Seconds: 1800
Merge-Wait-Seconds: 180
Max-Parallel-Subagents: 4
Opus-Subagents-Per-Session: 2
Pace: auto
Subagent-Hard-Cap: 6
Strong-Hard-Cap: 3
Subagents-Per-Session: 40
Subagents-Per-Machine: 8
Subagent-Burst-Per-Minute: 6
Max-Worktree-Agents: 6
Blackbox: on
Additive-Paths: -
```
