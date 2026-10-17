# One-command pipeline (HACK-056)

```bash
python -m analysis.pipeline.run --dry-run          # order + exact commands, nothing runs
python -m analysis.pipeline.run                    # everything (hours; needs data/raw/stuff_model_df.parquet)
python -m analysis.pipeline.run --from score       # resume at a step (e.g. after a failure)
python -m analysis.pipeline.run --only staff_audit # one step
make pipeline-dry / make pipeline
```

Each step runs in its own subprocess from the repo root. The terminal shows one status line per step with the
elapsed seconds; the run stops at the first non-zero exit and names the step (exit code = the step's). Full
output of every step goes to `artifacts/pipeline/<timestamp>.log` (git-ignored). `--dry-run` writes no log.

## Steps, in dependency order

| # | Step | Command | Writes |
|---|---|---|---|
| 1 | targets | `python -m stuffplus.targets` | `reports/targets/` |
| 2 | baseline | `python -m stuffplus.baseline` | `reports/baseline/` |
| 3 | park_id | `python -m analysis.park_id.run` | `reports/park_id/`, `artifacts/*_map.parquet` |
| 4 | physics | `python -m analysis.physics.run` | `reports/physics/` |
| 5 | stuff_model | `python -m analysis.stuff_model.run` | `artifacts/bundle`, `reports/stuff_model/` |
| 6 | location_model | `python -m analysis.location_model.run` | bundle, `reports/location_model/` |
| 7 | pitching_model | `python -m analysis.pitching_model.run` | bundle, `reports/pitching_model/` |
| 8 | hypotheses | `python -m analysis.hypotheses.run` | `reports/hypotheses/` (the memo cites `results.csv`) |
| 9 | validation_holdouts | `python -m analysis.validation.run --splits holdouts --pitching-inner-k 3 --out reports/validation/official_full` | `official_full/` |
| 10 | validation_fast | `python -m analysis.validation.run --fast --out reports/validation/official_fast` | `official_fast/` |
| 11 | validation_summary | `python -m stuffplus.validation.summary` | `reports/validation/summary.md`, `headline.csv` |
| 12 | altitude_delta | `python -m analysis.altitude_delta.run` | `reports/altitude_delta/` |
| 13 | score | `python -m stuffplus.score` | `artifacts/scores/pitch_scores.parquet`, `reports/leaderboards/` |
| 14 | pitcher_sensitivity | `python -m analysis.pitcher_sensitivity.run` | `reports/pitcher_sensitivity/` |
| 15 | ideal_profile | `python -m analysis.ideal_profile.run` | `reports/ideal_profile/` |
| 16 | design_lab | `python reports/design_lab/run.py` | `reports/design_lab/` |
| 17 | business_value | `python -m analysis.business_value.run` | `reports/business_value/` |
| 18 | staff_audit | `python -m analysis.staff_audit.run` | `reports/staff_audit/` |
| 19 | cards | `python -m stuffplus.cards` | `reports/cards/` |
| 20 | roster_names | `python -m analysis.pipeline.names` | names in `reports/leaderboards/` and `reports/staff_audit/` CSVs (no-op without a roster) |
| 21 | memo | `python reports/recommendations/build_memo.py` | `reports/recommendations/memo.md` |
| 22 | web_export | `python -m analysis.export_web.run` | skipped while `analysis/export_web/` does not exist |

Not in the pipeline (exploratory, not needed for the shipped numbers): `analysis.benchmark.run`, `analysis.causal.run`, `analysis.v0.run`, `stuffplus.explain`.
Add a `Step` to `STEPS` in `run.py` (dependencies must be listed earlier; `tests/test_pipeline.py` checks it).

## Roster drop-in (named finals data)

Optional CSV `pitcher_anon_id,name,team,role` at `data/roster.csv` (or the path in `STUFFPLUS_ROSTER`). It must stay
out of git: `.gitignore` belongs to HACK-057 in `.uak/OWNERS.md`, and HACK-057 adds the `data/roster.csv` rule; until
then keep it under `data/raw/` and point `STUFFPLUS_ROSTER` at it. The `roster_names` step
writes `pitcher_name` (plus `team_roster` / `role_roster` when given) into the leaderboard and staff CSVs, which the
web export reads; without the file the step does nothing.

Names are attached at presentation time; nothing is refitted and the anonymous id stays the key:

```python
from stuffplus.roster import apply_names, load_roster

board = apply_names(pd.read_csv("reports/leaderboards/pitcher_season.csv"))     # adds pitcher_name
board = apply_names(staff_pitchers, col="pitcher_anon_id")                      # staff_audit tables
# web / dashboard: call it once on the aggregate frame before rendering; pitcher_name falls back to the id
roster = load_roster()   # None when there is no file
```

Aggregates committed to git must keep the anonymous ids; apply names only in local output, the dashboard
session or an export that is not committed.
