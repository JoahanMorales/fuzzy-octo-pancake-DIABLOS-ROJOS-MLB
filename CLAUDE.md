# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Shared instructions

@AGENTS.md

## Project: Stuff+ 2240 (ISAC Hackathon 2026 · Diablos Rojos, sprint mode)
Stuff+ model for LMB pitching adjusted for air density (Harp Helú, CDMX, 2240 m). Deadline 2026-10-22 23:59 CDMX. Read `IDEA.md` for the thesis, `.uak/PROJECT.md` for the rubric (C1–C4, 25 % each) and event rules, `.uak/TASKS.md` for the HACK-NNN backlog (each task has `Paths`, `Acceptance`, `Verify`). The repo is at the planning stage: the `stuffplus/` package, `tests/` and `requirements.txt` come from HACK-001 and may not exist yet.

Planned layout (from TASKS.md): `stuffplus/` (library: `io`, `schema`, `splits`, `baseline`, `features/identity`, `physics/constants`), `analysis/<task>/run.py` (heavy runs, write to `reports/<task>/`), `artifacts/` (models + aggregates the dashboard ships), Streamlit dashboard on port 8501.

Commands (Python ≥ 3.11; use `python`, not `python3`, on Windows):
- `pip install -r requirements.txt` (`pyarrow>=20` required for the parquet)
- Tests: `bash .uak/bin/q python -m pytest -q --tb=short -x tests/test_x.py::test_name`; always use the task's own `Verify` line.

Domain rules that span many tasks:
- Raw data lives only in git-ignored `data/raw/stuff_model_df.parquet`. Never commit raw data or pitch-level outputs; commit code, aggregates (CSV ≤ 2 MB) and figures. Deployed views show aggregates only, never per-pitch scatters. Load data only via `stuffplus.io.load_raw()` / `stuffplus.schema.clean()`; tests use the synthetic fixture in `tests/conftest.py`.
- Pitch identity must not depend on altitude: Trackman's `AutoPitchType` shifts with air density. Compare by `pitch_id` from `stuffplus.features.identity` (HACK-029), never by `AutoPitchType`.
- Two Stuff+ flavours, always labelled: park-neutral (sea-level ρ, 100 = LMB average) and environment (scored at a given ρ). ΔStuff+ CDMX = environment(ρ_HH) − neutral.
- Use the shared splits (`stuffplus/splits.py`) and the null baseline (`stuffplus/baseline.py`); every model reports against the baseline. Physics constants (incl. the Harp Helú density) live in `stuffplus/physics/constants.py`; never hardcode 2240.
- UI text is in Spanish; visual identity is Diablos red + black.

Load `.uak/docs/` only when `AGENTS.md` §7 or your mode says so. Minimal context leaves tokens for the task.

## Claude Code only
- Hooks:
  - `SessionStart` already ran `uak next` and showed your inbox.
  - `PostToolUse` sends heartbeats and injects only actionable messages. On Bash, an output over 12k chars reaches you as head + tail + the path of the full log: read it by ranges (`sed -n`, `grep -n`), or rerun with `UAK_RAW=1` only if you need everything.
  - `Stop` won't let you finish with unhandled messages.
  - `PreToolUse` (`guard`) blocks destructive or publishing commands, even when chained.
  - `UserPromptSubmit` blocks pasted secrets.
  - The status line shows task, 5 h/7 d plan usage and `uak pace`; when the pace level changes, a hook tells you once.
- Commands:
  - All modes: `/uak-setup`, `/uak-plan`, `/uak-start`, `/uak-loop`, `/uak-advise`, `/uak-ship`, `/uak-review`, `/uak-handoff`, `/uak-secure`, `/uak-retro`.
  - sprint: `/uak-design-lock`, `/uak-demo`.
  - marathon: `/uak-spec`.
- Subagents (isolated context, summary only):
  - `uak-scout` (Haiku): read-only lookups.
  - `uak-runner` (Haiku): tests, smoke, app.
  - `uak-reviewer`: reviews.
  - `design-critic`: sprint UI screenshots.
  - `security-reviewer` (Opus): marathon sensitive PRs.
  - `uak-architect` (Opus): checkpoints only.
  - `Explore`: only when uak-scout is not enough (it runs on the lead model, so it is pricier).
- Orchestration (`.uak/docs/ORCHESTRATION.md`):
  - You are the Sonnet lead. Send `uak-scout` (Haiku) for any lookup needing 3 or more searches, up to 3 in parallel on disjoint questions. Do one-search lookups yourself.
  - Consult the Opus advisor only at the 3 checkpoints: plan lock (more than 2 files or a contract), the same failure twice, done on risky diffs. If the advisor tool is missing or the session is long, use `/uak-advise <plan|stuck|done>` instead.
  - Never fan out Opus subagents. The `guard agent` hook caps parallel subagents and the Opus budget per session, scaled by `uak pace` (surge 2×, conserve ½, critical 1 and no Opus).
- Run tests with `bash .uak/bin/q ...`, using pytest `-q --tb=short -x`. Edit with Edit; never rewrite whole files.
- Avoid editing `AGENTS.md` or `CLAUDE.md` while agents are running: it invalidates every agent's prompt cache. Urgent amendments go through `uak decision`.

## When compacting
Keep only: ID, branch, worktree, exact next step, pending criteria, failures with exact errors, verify commands, decisions and unanswered inbox. Drop command output, diffs and explorations.
