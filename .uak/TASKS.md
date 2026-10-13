# TASKS · Stuff+ 2240 (ISAC Hackathon 2026 · Diablos Rojos) · 4 humans × 2 agents · deadline 2026-10-22

State lives on the `claims` branch (`uak status`); this file holds only tasks. Rubric: C1 model quality · C2 OOS robustness · C3 arsenal + altitude · C4 applicability (25 % each).

Global rules for every task (read before claiming):
- Raw data lives ONLY in `data/raw/stuff_model_df.parquet` (git-ignored, each human copies it). **Never commit raw data or pitch-level outputs**; commit code, aggregated tables (CSV ≤ 2 MB) and figures. Results can be shown, data cannot. Anything deployed (HACK-024) shows aggregates only: centroids, density contours, binned shapes, never a scatter of individual pitches.
- Load data only through `stuffplus.io.load_raw()` / `stuffplus.schema.clean()`. Tests run on the synthetic fixture from `tests/conftest.py` (no raw data in CI). Heavy runs go in `analysis/<task>/run.py` and write to `reports/<task>/`.
- Use the shared splits in `stuffplus/splits.py` and the null baseline in `stuffplus/baseline.py`. Every model reports vs the baseline.
- **Pitch identity must not depend on altitude.** Trackman's `AutoPitchType` uses movement, and movement changes with air density: same pitchers in Extreme vs No games have −2.8 pp Sinker, −2.8 pp Changeup, +2.5 pp Cutter, +2.5 pp Slider (690 pitcher-seasons, se 0.003; verified 2026-10-12). Any within-pitcher comparison by pitch type uses `pitch_id` from `stuffplus.features.identity` (HACK-029), built from altitude-invariant traits (velo, spin rate, release point, extension). Until it exists, use the fallback documented in `docs/CONTRACT.md`.
- Two Stuff+ flavours, always labelled: **park-neutral** (scored at sea-level ρ, 100 = LMB average) and **environment** (scored at a given ρ, e.g. Harp Helú). ΔStuff+ CDMX = environment(ρ_HH) − neutral.
- Python ≥ 3.11, `pip install -r requirements.txt` (`pyarrow>=20` is required to read the parquet). On Windows use `python`, not `python3`.
- Physics constants and the Harp Helú density live in `stuffplus/physics/constants.py` (HACK-004). Do not hardcode 2240 elsewhere.

## HACK-001 · Setup: package skeleton, requirements, data loader, synthetic fixture, smoke test

- **Type:** setup
- **Priority:** P0
- **Estimate:** 1 h
- **Rubric / Spec:** C1 C2 C3 C4
- **Depends on:** None
- **Paths:** requirements.txt, pyproject.toml, stuffplus/__init__.py, stuffplus/io.py, stuffplus/config.py, tests/__init__.py, tests/conftest.py, tests/fixtures/, tests/test_io.py, README.md, Makefile
- **Freeze-Allowed:** no
- **Acceptance:**
  - `requirements.txt` pins `pyarrow>=20`, pandas, numpy, scipy, scikit-learn, lightgbm, shap, streamlit, plotly, matplotlib, networkx, pytest, pygam, kaleido; optional extra `econml`.
  - `stuffplus.config` resolves `DATA_PATH` from env `STUFFPLUS_DATA` (default `data/raw/stuff_model_df.parquet`), `ARTIFACTS_DIR=artifacts/`, `REPORTS_DIR=reports/`.
  - `stuffplus.io.load_raw(columns=None)` reads the parquet with pyarrow; clear error if pyarrow < 20 or the file is missing.
  - `tests/conftest.py` exposes `synthetic_pitches`: ~5,000 rows with the SAME 84 columns/dtypes as the raw file, 3 seasons, 3 altitude buckets, ≥ 40 pitchers, ≥ 60 batters in fixed 9-man lineups, ≥ 30 games, realistic ranges (velo 75–100, IVB −20–25, spin 1500–3000), Extreme games with ~16 % lower drag and ~20 % less Magnus break. Generated in code (no real rows).
  - README (replace the placeholder): what the project is, install, where to put the data, how to run tests and the dashboard.
- **Verify:** `python -m pytest -q tests/test_io.py`
- **Next step:** write `requirements.txt` and `tests/conftest.py` with the column list from `data/stuff_plus_data_dictionary.csv`.

## HACK-002 · Contract: clean schema, splits, predict API + artifact bundle format (fast, everyone consumes it)

- **Type:** contract
- **Priority:** P0
- **Estimate:** 1.5 h
- **Rubric / Spec:** C1 C2
- **Depends on:** None
- **Uses contract:** HACK-001
- **Paths:** stuffplus/schema.py, stuffplus/splits.py, stuffplus/api.py, docs/CONTRACT.md, tests/test_contract.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `schema.clean(df)`: drops NaN `altitude_category`, `Undefined` hands, pitch types `Other/OneSeamFastBall/TwoSeamFastBall/Knuckleball`; `Switch` batters → side faced; `Sweeper → Slider` (documented); `EffectiveVelo` → float; adds `pitch_idx_in_game`, `pa_id` (game + inning + half + batter run), `is_rhp`, `same_side`, `home_batting` (= half == Bottom). Lists `PHYSICAL_FEATURES`, `LOCATION_FEATURES`, `CONTEXT_FEATURES`, `TARGET_COLUMNS`, `ID_COLUMNS`; `assert_no_target_leak(features)`.
  - `splits.py`: `pitcher_group_kfold(df, k=5, seed=2240)`, `season_holdout(df, train=(2024, 2025), test=(2026,))`, `park_holdout(df, train=('No Altitude','Medium Altitude'), test=('Extreme Altitude',))`. Deterministic.
  - `api.py`: dataclass `PitchInput` (pitch_type, throws, velo, spin_rate, spin_axis, ivb, hb, rel_height, rel_side, extension, optional plate_x/plate_z/balls/strikes/batter_side, optional arsenal context) and `predict_pitch(p, rho="harp_helu", flavour="environment") -> dict` with `{stuff_plus, stuff_plus_neutral, location_plus, pitching_plus, xrv, probs:{...}, movement_expected:{ivb,hb}, demo_data}`. Deterministic MOCK until `stuffplus/serving.py` exists (then it dispatches to it).
  - **Bundle format** (documented): `artifacts/bundle/` = `manifest.json` (version, features, ρ refs, scaler stats), `models/*.txt` (LightGBM), `tables/*.csv` (aggregates only). Everything downstream reads this layout.
  - **Pitch-identity fallback** documented: per pitcher-season KMeans on (velo, spin rate, RelHeight, RelSide, Extension), k = number of AutoPitchType labels with ≥ 5 % usage, label = majority AutoPitchType in No-Altitude games.
  - `docs/CONTRACT.md` documents all of the above with examples.
- **Verify:** `python -m pytest -q tests/test_contract.py`
- **Next step:** `stuffplus/api.py` dataclass + mock; publish with `uak msg related:HACK-002 --kind contract` as soon as it is pushed.

## HACK-030 · Targets + LMB run value (count-transition RE + linear weights calibrated to LMB)

- **Type:** contract
- **Priority:** P0
- **Estimate:** 4 h
- **Rubric / Spec:** C1
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002
- **Paths:** stuffplus/targets.py, reports/targets/, tests/test_targets.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Outcome flags: whiff (StrikeSwinging over swings), chase (swing outside zone), called strike, weak contact (EV < 88 mph or popup), groundball, hard/barrel (EV ≥ 95 & LA 8–32; documented), out within PA.
  - **Run value per pitch calibrated to LMB:** run expectancy RE(outs, balls, strikes) = mean runs until end of half-inning from `RunsScored` (rows are in game order; verified 99.99 %); pitch rv = ΔRE + runs on play; event linear weights (1B/2B/3B/HR/BB/HBP/out) fitted on LMB. `add_run_value(df)` → `rv`. Tables to `reports/targets/` (RE matrix, linear weights, LMB vs MLB comparison: LMB is a high-offense league).
  - Per-park-cluster run environment when `artifacts/park_map.parquet` exists (HR/FB, runs/game by park) for the business layer.
  - Tests: RE monotone in strikes/decreasing with outs on the fixture; rv sums to runs per half-inning.
- **Verify:** `python -m pytest -q tests/test_targets.py`
- **Next step:** compute runs-to-end-of-half-inning with a reverse cumulative sum of `RunsScored` per (game, inning, half).

## HACK-031 · Walking skeleton: Stuff+ v0 end to end (crude model → bundle → serving → dashboard) by day 2

- **Type:** integration
- **Priority:** P0
- **Estimate:** 4 h
- **Rubric / Spec:** C1 C4
- **Depends on:** HACK-001, HACK-002
- **Uses contract:** HACK-030
- **Paths:** stuffplus/models/__init__.py, stuffplus/models/common.py, stuffplus/bundle.py, stuffplus/serving.py, analysis/v0/, tests/test_serving.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `models/common.py::train_lgbm_oof(df, features, target, folds, objective)` (shared by every model task).
  - v0 xRV LightGBM on physical features + ρ̂ (bucket fallback) with the simple rv (HACK-030 if ready, else count-based rv); saved in the bundle format; `serving.load_bundle()` + `predict_pitch` real implementation; `api.py` dispatches to it.
  - `streamlit run app/Home.py` shows a REAL v0 number for a pitch (labelled "v0"). From here on every task improves a working system.
- **Verify:** `python -m pytest -q tests/test_serving.py`
- **Next step:** `analysis/v0/run.py` → `bundle.save(...)` → `serving.load_bundle()`.

## HACK-003 · Park identification: teams from batter lineups → home park → Harp Helú + Diablos staff

- **Type:** spike
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C3 C4
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-004
- **Paths:** stuffplus/physics/parks.py, analysis/park_id/, reports/park_id/, tests/test_parks.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - **Method (prototype verified 2026-10-12):** per season, graph of batters weighted by shared (game, half) lineups (edge ≥ 3), Louvain (`networkx.community.louvain_communities(weight='weight', seed=2240)`) → 17–21 teams (LMB has 20). Home team = majority team of the **Bottom-half** batters. Prototype: most teams ~45 home games with altitude purity 1.0 and tight per-park ρ̂ (IQR ≈ 0.03). Pitcher clustering does NOT work (trades merge everything).
  - Link franchises across seasons by batter overlap. Prototype: two franchises are the lowest-ρ̂ Extreme parks every year — A: 0.808 / 0.832 / 0.818, B: 0.819 / 0.828 / 0.829 (CDMX 2,240 m vs Puebla 2,135 m). Decide the **Harp Helú candidate** with a pooled bootstrap of game-level ρ̂ per franchise; report P(A lower than B) and the theoretical gap (~1.2 % pressure for 105 m). If not decisive, report "two highest parks" and use their pooled ρ̂ as the CDMX environment.
  - Map pitchers to teams (pitchers pitch the half where their team is NOT batting) → `diablos_candidate_staff` per season (anonymized IDs).
  - Outputs: `reports/park_id/parks.csv` (franchise, season, home games, bucket, purity, ρ̂ median/IQR, runs/game, HR per fly ball), `artifacts/park_map.parquet` (game → park, home team, is_harp_helu), `artifacts/team_map.parquet` (pitcher/batter-season → team). Fix inconsistent splits (purity < 0.9) with Louvain resolution tuning.
- **Verify:** `python -m pytest -q tests/test_parks.py`
- **Next step:** port the prototype (Louvain on batter co-lineups) into `stuffplus/physics/parks.py::infer_teams(df, season)`.

## HACK-004 · Physics: per-game air density, drag/Magnus decomposition, spin efficiency, movement translation

- **Type:** feature
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002, HACK-029
- **Paths:** stuffplus/physics/__init__.py, stuffplus/physics/constants.py, stuffplus/physics/aero.py, stuffplus/physics/translate.py, analysis/physics/, reports/physics/, tests/test_physics.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `aero.decompose(df)`: from the 9-parameter fit compute drag acceleration (along −v), Magnus acceleration (⊥ v, gravity removed), Cd-proxy = drag/v², Cl-proxy = Magnus/v², **spin efficiency** = Magnus-implied transverse spin / `SpinRate` (Nathan's method), active spin. Unit tests on a synthetic trajectory with known Cd/Cl.
  - `aero.game_density_index(df)`: per game ρ̂ = median Cd-proxy of fastballs ÷ sea-level median. Exploration: Extreme/No ≈ 0.838, Medium/No ≈ 0.89. Shrink games with < 30 fastballs toward their park (HACK-003) or bucket mean. **Validate:** Cl-proxy/Cd-proxy should NOT depend on ρ (both scale with ρ) — this rules out a Trackman calibration artefact by park.
  - `constants.py`: `RHO_SEA_LEVEL=1.0`, `RHO_HARP_HELU` (empirical from HACK-003, else barometric 2,240 m with typical CDMX temperature; document both), `RHO_COORS`.
  - `translate.py`: `expected_movement(release + spin features, rho) → (ivb, hb, speed_drop, plate_velo)` fitted on **within-pitcher × pitch_id** variation; reproduces four-seam ΔIVB ≈ −3.7" (Extreme vs No, n≈404, sd 1.0) within CI; `translate_pitch(pitch, rho_from, rho_to)`. Note the hidden gain: less drag → −1.36 mph less speed drop → the fastball arrives faster in CDMX.
  - `reports/physics/`: ρ̂ by park, ΔIVB/ΔHB/Δplate velo by pitch_id family with bootstrap 95 % CI, 1-page physics README (Magnus ∝ ρ, drag ∝ ρ) for the tech doc.
- **Verify:** `python -m pytest -q tests/test_physics.py`
- **Next step:** implement `aero.decompose` with numpy; test with a trajectory built from known Cd/Cl.

## HACK-005 · Null baseline + evaluation harness (RMSE, log-loss, calibration, by split)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C1 C2
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002, HACK-030
- **Paths:** stuffplus/baseline.py, stuffplus/evaluate.py, reports/baseline/, tests/test_evaluate.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `baseline.CountBaseline`: mean `rv` (and each target probability) by count, plus a stronger count × pitch_id-family baseline. This is the rubric's null model.
  - `evaluate.report(y_true, y_pred, kind)`: RMSE / MAE / R² for xRV; log-loss, Brier, AUC, ECE + reliability-curve data; tidy DataFrame. `evaluate.compare(models, split)` → one table with **skill vs baseline** (% RMSE / log-loss reduction) and bootstrap CIs.
  - Pitcher-level predictiveness: correlation of pitcher-season mean predicted xRV with next-season observed RV per pitch (how public Stuff+ is judged).
  - `reports/baseline/baseline_metrics.csv` for all three splits.
- **Verify:** `python -m pytest -q tests/test_evaluate.py`
- **Next step:** `CountBaseline.fit/predict` with groupby on `count`.

## HACK-006 · Arsenal & sequence features: primary fastball diffs, tunneling, usage, previous pitch

- **Type:** feature
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002, HACK-029
- **Paths:** stuffplus/features/__init__.py, stuffplus/features/arsenal.py, stuffplus/features/sequence.py, tests/test_features.py, reports/features/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Primary fastball per pitcher-season (most used fastball pitch_id). `velo_diff_vs_fb`, `ivb_diff_vs_fb`, `hb_diff_vs_fb` (HB mirrored for LHP), `spin_diff_vs_fb`, `axis_diff_vs_fb`, `pitch_usage_pct`, arsenal size, arsenal movement spread. Diffs computed **within the same game** where possible, so both pitches share the same air.
  - **Tunneling:** release distance to the primary FB and position difference at the decision point (~23.8 ft from plate) from the `PitchTrajectory*c0..c2` polynomials vs plate-location difference → `tunnel_ratio`.
  - Sequence (rows are in game order): `prev_pitch_id`, `prev_velo_diff`, `prev_loc_diff`, pitch number in PA, times through order.
  - No leakage: `fit_arsenal(train) → transform(test)`; own pitches only. Handedness mirroring documented.
- **Verify:** `python -m pytest -q tests/test_features.py`
- **Next step:** `arsenal.primary_fastball(df)` grouped by (pitcher_anon_id, year).

## HACK-029 · Altitude-invariant pitch identity + pitch shape clustering (shape over label)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-002, HACK-004
- **Paths:** stuffplus/features/identity.py, stuffplus/features/shapes.py, tests/test_shapes.py, reports/shapes/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `identity.assign_pitch_id(df)`: per pitcher-season, Gaussian mixture on altitude-invariant traits (velo, spin rate, RelHeight, RelSide, Extension, spin axis only if stable) → `pitch_id` + family label from No-Altitude games. **Test of success:** pitch_id usage shares per pitcher are equal in Extreme vs No games (|Δ| < 0.5 pp vs the 2.8 pp shift of AutoPitchType). Ship this part first (≤ 3 h) and message consumers.
  - `shapes.py`: interpretable shapes ("riding 4S", "sinking 2S", "gyro slider", "sweeper", "12-6 CB", "power CH", "splitter") from **sea-level-translated** movement (HACK-004) + velo + arm angle; `assign_shape(pitch)` for a single dashboard input; ≥ 90 % of pitches assigned.
  - `reports/shapes/`: label-shift table (AutoPitchType vs pitch_id), shapes.csv, centroid figure.
- **Verify:** `python -m pytest -q tests/test_shapes.py`
- **Next step:** reproduce the label shift table, then fit the per pitcher-season mixture.

## HACK-007 · Dashboard skeleton + design lock (Streamlit, Diablos theme) on the predict API

- **Type:** feature
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C4
- **Depends on:** None
- **Uses contract:** HACK-002, HACK-031
- **Paths:** app/Home.py, app/theme.py, app/DESIGN.md, app/pages/, app/assets/, .streamlit/, tests/test_app_smoke.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `/uak-design-lock`: 3 visual directions with screenshots at 1280×720; the human (luis) picks; tokens frozen in `app/theme.py` + `.streamlit/config.toml` + custom CSS. Direction brief: dark broadcast look ("Statcast meets Diablos"), Diablos red, white, black; condensed sport font; large numbers.
  - `Home.py` + pages: `1_Simulador`, `2_Leaderboard`, `3_Prospecto`, `4_Altitud`, `5_Recomendaciones`, `6_Laboratorio`, `7_Tarjeta`, `8_Staff_Diablos`. Spanish UI.
  - Simulator: form → `predict_pitch` → two big gauges (Harp Helú vs nivel del mar) + plotly movement map (HB vs IVB) with an arrow from sea-level movement to CDMX movement. The wow fits 1280×720 without scrolling. Mock numbers show a `demo_data` badge; every number has a source tooltip.
  - Empty / loading / error states. `streamlit run app/Home.py`.
- **Verify:** `python -m pytest -q tests/test_app_smoke.py`
- **Next step:** `tests/test_app_smoke.py` with `streamlit.testing.v1.AppTest.from_file("app/Home.py").run()`.

## HACK-008 · Technical document skeleton + literature + theory (sabermetrics × physics × LMB)

- **Type:** docs
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C1 C2 C3 C4
- **Depends on:** None
- **Paths:** docs/technical/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `docs/technical/paper.md` (Spanish; pandoc → PDF via `docs/technical/build.sh`, LaTeX template with Diablos styling): 1 Introducción · 2 Marco teórico (Stuff+/Location+/Pitching+; Magnus ∝ ρ, drag ∝ ρ; Nathan; SABR *High Altitude Offense*; LMB/Harp Helú) · 3 Datos (incl. label shift and park identification) · 4 Metodología (two-stage physics → outcome, targets, LMB run value, neutral vs environment scale) · 5 Validación · 6 Altitud · 7 Recomendaciones y valor de negocio · 8 Alcance y fronteras · Referencias. TODO markers name the task that fills each one.
  - `references.bib`: every challenge reference + Nathan (trajectory, spin efficiency), FanGraphs Stuff+ primer, run value. Verified URLs only.
  - Formal definition of both Stuff+ flavours in LaTeX math, written now. Page budget 6–10.
- **Verify:** `test -s docs/technical/paper.md`
- **Next step:** draft §2 with the physics derivation of why break scales with ρ.

## HACK-009 · Hypotheses H1–H4 with LMB evidence (within-pitcher design, bootstrap CIs)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002, HACK-004, HACK-029, HACK-030
- **Paths:** analysis/hypotheses/, reports/hypotheses/, stuffplus/hypotheses.py, tests/test_hypotheses.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - All comparisons by `pitch_id` (not AutoPitchType), pitcher-cluster bootstrap 95 % CI, and dose-response vs ρ̂ (slope per 0.1 ρ) using park-level ρ̂ (not just 3 buckets).
  - **H1** movement loss (ΔIVB, ΔHB, Δtotal break, Δspeed drop) · **H2** velocity-differential pitches (changeups/splitters vs breaking balls: Δwhiff, Δchase, ΔxRV, paired by pitcher; exploration suggests changeups lose ~4" of fade, so H2 may fail; report honestly) · **H3** groundballs (HR/FB, distance, xRV of FB vs GB by altitude; pitcher-level regression with GB% × altitude) · **H4** spin vs movement (ΔAUC / partial R² of SpinRate alone vs movement + spin efficiency, by altitude).
  - `reports/hypotheses/summary.md`: table per hypothesis with verdict (Supported / Partially / Rejected), effect size, CI, n; PNG figures.
- **Verify:** `python -m pytest -q tests/test_hypotheses.py`
- **Next step:** `hypotheses.within_pitcher_delta(df, metric, pitch_id_family, a, b, min_n=20, n_boot=2000)`.

## HACK-013 · Stuff+ scale & normalization (park-neutral and environment flavours)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 2 h
- **Rubric / Spec:** C1
- **Depends on:** None
- **Uses contract:** HACK-002
- **Paths:** stuffplus/scale.py, tests/test_scale.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `PlusScaler(by=("year",), sign=-1)` → 100 + 10·z with reference mean/sd = LMB pitches of that season scored at sea-level ρ (**park-neutral**). Environment flavour = the same scaler applied to predictions at another ρ, so "96 in Harp Helú" and "112 at sea level" share one ruler. `by=("year","pitch_family")` variant for within-type views.
  - JSON save/load (bundle). Aggregations pitch → pitcher / pitch_id / arsenal (usage-weighted) with min-pitch thresholds and empirical-Bayes shrinkage toward 100.
  - Test: synthetic normal xRV → mean 100, sd 10; 120 ≈ p97.7.
- **Verify:** `python -m pytest -q tests/test_scale.py`
- **Next step:** `PlusScaler.fit` storing per-group mean/sd.

## HACK-010 · Stuff+ model (physics at release + arsenal + ρ), LightGBM, pitcher GroupKFold

- **Type:** feature
- **Priority:** P0
- **Estimate:** 10 h
- **Rubric / Spec:** C1 C2 C3
- **Depends on:** HACK-031
- **Uses contract:** HACK-004, HACK-005, HACK-006, HACK-013, HACK-029, HACK-030
- **Paths:** stuffplus/models/stuff.py, analysis/stuff_model/, reports/stuff_model/, tests/test_model_stuff.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Two-stage design: movement inputs are **sea-level-translated** (HACK-004) + ρ̂ as an explicit feature, so the counterfactual "same release in another air" is a model evaluation, not an extrapolation.
  - Features: velo, spin, axis, translated IVB/HB, release height/side, extension, arm angle, spin efficiency, VAA (justified), arsenal diffs, handedness, ρ̂. No location, count or outcome columns (leak guard).
  - Targets: xRV regression (main) + whiff / called-strike / GB / hard-contact classifiers; OOF with `pitcher_group_kfold`.
  - Metrics vs `CountBaseline` (RMSE skill, log-loss, calibration). Bundle to `artifacts/bundle/` (git-ignored); metrics to `reports/stuff_model/metrics.csv`. `predict_at_rho(df, rho)`.
- **Verify:** `python -m pytest -q tests/test_model_stuff.py`
- **Next step:** feature matrix builder using `train_lgbm_oof` from `models/common.py`.

## HACK-011 · Location+ model (zone × count × batter side × pitch shape)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-031
- **Uses contract:** HACK-005, HACK-029, HACK-030
- **Paths:** stuffplus/models/location.py, analysis/location_model/, reports/location_model/, tests/test_model_location.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Marginal value of location: xRV from (PlateLocSide mirrored, PlateLocHeight, balls, strikes, same_side, pitch shape) WITHOUT pitch physics → Location+. 9-quadrant + chase-zone summaries.
  - Heatmaps per shape × count bucket (ahead / even / behind); does the best location change in altitude (e.g. elevated fastballs lose value)?
  - OOF vs baseline metrics; bundle under `artifacts/bundle/models/location*`.
- **Verify:** `python -m pytest -q tests/test_model_location.py`
- **Next step:** 2-D smoothed target encoding vs LightGBM on (x, z, count); pick by OOF RMSE.

## HACK-012 · Pitching+ multi-target model, batter-quality adjustment, fitted combination weights

- **Type:** feature
- **Priority:** P0
- **Estimate:** 10 h
- **Rubric / Spec:** C1 C2 C3
- **Depends on:** HACK-010, HACK-011
- **Uses contract:** HACK-006, HACK-013, HACK-030
- **Paths:** stuffplus/models/pitching.py, stuffplus/models/multitarget.py, analysis/pitching_model/, reports/pitching_model/, tests/test_model_pitching.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Targets: P(whiff | swing), P(chase), P(called strike), P(weak contact), P(GB), P(hard/barrel), xRV, P(out within PA).
  - Features: stuff + location + arsenal + sequence + context (count, outs, inning, same_side) + ρ̂ + **batter quality** (out-of-fold batter rv/whiff rates) as a nuisance covariate, set to league average at scoring time (removes opponent luck).
  - **Combination weights fitted:** regress observed `rv` on OOF probabilities (ridge, sign-constrained) → combined xRV → Pitching+. Weights table + stability across folds.
  - Calibration plots per target, OOF metrics vs baseline; bundle.
- **Verify:** `python -m pytest -q tests/test_model_pitching.py`
- **Next step:** loop over targets with `train_lgbm_oof`.

## HACK-014 · Validation suite: pitcher, season, park holdout + reliability + predictiveness

- **Type:** feature
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-005, HACK-010
- **Uses contract:** HACK-011, HACK-012
- **Paths:** stuffplus/validation/, analysis/validation/, reports/validation/, tests/test_validation.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - One command runs all splits for Stuff+, Location+, Pitching+ and the baseline → `reports/validation/validation_table.csv` + `validation.md` (model × split × metric, skill vs baseline, CIs).
  - **Park holdout:** train No + Medium → test Extreme; calibration in Extreme with vs without ρ̂ and translated movement (proves the physics layer helps). Also leave-one-park-out with HACK-003 parks.
  - **Stability:** split-half reliability (odd/even games), year-to-year correlation 2024→2025→2026, and next-season predictiveness vs raw whiff% / run-allowed proxies; how many pitches until Stuff+ stabilizes.
- **Verify:** `python -m pytest -q tests/test_validation.py`
- **Next step:** `stuffplus/validation/run_all.py` iterating `splits.*` × models.

## HACK-015 · Altitude effect: ΔStuff+ by pitch shape, Harp Helú vs sea level (counterfactual + observed)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C3
- **Depends on:** HACK-004, HACK-010, HACK-013
- **Uses contract:** HACK-003, HACK-009, HACK-029
- **Paths:** stuffplus/altitude.py, analysis/altitude_delta/, reports/altitude_delta/, tests/test_altitude.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - **Counterfactual:** every pitch scored at ρ_sea and ρ_HarpHelú → ΔStuff+ per pitch.
  - **Observed triangulation:** within-pitcher (by pitch_id) Stuff+ in Harp Helú-candidate games vs sea-level games agrees in sign/magnitude.
  - Table by shape and pitch family: mean ΔStuff+, 95 % CI, n, Δwhiff, Δhard contact, ΔHR/FB risk, with a physical explanation column. Ranking of shapes that **gain** vs **lose** in CDMX.
  - Same for every LMB park (ρ̂ curve): ΔStuff+ as a function of ρ for each shape → "altitude curves" figure.
  - `reports/altitude_delta/delta_by_shape.csv` + forest plot.
- **Verify:** `python -m pytest -q tests/test_altitude.py`
- **Next step:** `altitude.counterfactual_scores(df, bundle, rho_a, rho_b)`.

## HACK-016 · Scoring pipeline + leaderboards per pitch, pitcher, arsenal (both flavours)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C1 C4
- **Depends on:** HACK-012, HACK-013
- **Uses contract:** HACK-003, HACK-015
- **Paths:** stuffplus/score.py, analysis/scoring/, reports/leaderboards/, tests/test_score.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `python -m stuffplus.score` → `artifacts/scores/pitch_scores.parquet` (git-ignored; PitchUID + Stuff+ neutral / Harp Helú, Location+, Pitching+) — this file is the required per-pitch deliverable, sent by email, never committed.
  - Aggregated CSVs in `reports/leaderboards/`: pitcher-season, pitcher × pitch_id, arsenal (usage-weighted), with n and shrinkage.
  - "¿Qué arsenal produce el Stuff+ más alto en Harp Helú?" table; Stuff+ by park.
- **Verify:** `python -m pytest -q tests/test_score.py`
- **Next step:** batch predict with `serving.load_bundle()`.

## HACK-017 · Ideal physical profile for Diablos Rojos (what maximizes Stuff+ at 2,240 m)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C3 C4
- **Depends on:** HACK-004, HACK-010
- **Uses contract:** HACK-015, HACK-019, HACK-029
- **Paths:** stuffplus/profile.py, analysis/ideal_profile/, reports/ideal_profile/, tests/test_profile.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - 2-D partial dependence + SHAP interaction of each physical feature **with ρ̂**: which matter MORE in altitude (velocity, extension, VAA, low-spin-efficiency / seam-shifted pitches) vs less (spin-driven ride).
  - Constrained optimization inside the observed data hull (kNN density): best primary fastball, best secondary given that fastball, best 3-pitch arsenal at ρ_HarpHelú vs sea level.
  - `reports/ideal_profile/profile.md` with the physical + statistical argument and one "receta" figure for scouts.
- **Verify:** `python -m pytest -q tests/test_profile.py`
- **Next step:** 2-D PDP (feature × ρ̂) for velo, IVB, HB, spin efficiency, extension.

## HACK-018 · Pitcher altitude sensitivity: most affected vs most consistent pitchers

- **Type:** feature
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C3 C4
- **Depends on:** HACK-015
- **Uses contract:** HACK-016
- **Paths:** analysis/pitcher_sensitivity/, reports/pitcher_sensitivity/, stuffplus/sensitivity.py, tests/test_sensitivity.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Per pitcher: arsenal ΔStuff+ (CDMX − neutral) + observed high-altitude/sea-level split, empirical-Bayes shrinkage and CI → **altitude-proof index**.
  - Top/bottom 15 pitchers (anonymized) with the pitch driving the loss/gain and the physical reason — the intro's explicit ask.
- **Verify:** `python -m pytest -q tests/test_sensitivity.py`
- **Next step:** usage-weighted aggregation of per-pitch ΔStuff+ by pitcher-season.

## HACK-019 · Explainability: SHAP per pitch and global, coach-friendly Spanish text

- **Type:** feature
- **Priority:** P1
- **Estimate:** 4 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-010
- **Paths:** stuffplus/explain.py, reports/explain/, tests/test_explain.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `explain_pitch(pitch, rho)` → top-5 SHAP contributions in Stuff+ points + one Spanish sentence each ("+4 por velocidad de 96 mph"; "−3 porque el aire de la CDMX le quita 3.5\" de ride"). Global beeswarm + dependence plots for the doc.
- **Verify:** `python -m pytest -q tests/test_explain.py`
- **Next step:** `shap.TreeExplainer` on the Stuff+ model, converted to Stuff+ units with the scaler sd.

## HACK-020 · Dashboard integration: real models, CDMX vs sea level, movement map, SHAP

- **Type:** integration
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C4 C3
- **Depends on:** HACK-007, HACK-015, HACK-016
- **Uses contract:** HACK-019
- **Paths:** app/pages/1_Simulador.py, app/pages/2_Leaderboard.py, app/pages/4_Altitud.py, app/components/, stuffplus/serving.py, tests/test_app_pages.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Simulator: Stuff+ / Location+ / Pitching+ at Harp Helú vs sea level side by side, movement translation arrows, SHAP "¿por qué?", park selector (every LMB park by ρ̂).
  - "Mapa de movimiento": most and least effective pitches per shape as **density contours + centroids** (raw scatter only when the local raw file exists), toggle CDMX / sea level.
  - Leaderboard and Altitud pages read only `artifacts/bundle/tables/` (no raw data needed).
- **Verify:** `python -m pytest -q tests/test_serving.py tests/test_app_smoke.py tests/test_app_pages.py`
- **Next step:** cache `serving.load_bundle()` with `st.cache_resource`.

## HACK-021 · Prospect / free-agent profiler (arsenal → Stuff+ in CDMX + comparables + verdict)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-016
- **Uses contract:** HACK-018, HACK-020
- **Paths:** stuffplus/prospect.py, app/pages/3_Prospecto.py, tests/test_prospect.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Input: 2–5 pitches or a Trackman-format CSV. Output: Stuff+ per pitch and arsenal at Harp Helú vs sea level, altitude-proof index, HR-risk flag, 5 nearest LMB comparables (anonymized), expected runs saved per season at home, and a verdict "Firmar / Desarrollar / Evitar para casa".
- **Verify:** `python -m pytest -q tests/test_prospect.py`
- **Next step:** `prospect.evaluate_arsenal(pitches)` reusing serving.

## HACK-032 · Diablos staff audit: home vs road usage, which pitch to cut at home

- **Type:** feature
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C4 C3
- **Depends on:** HACK-003, HACK-016
- **Uses contract:** HACK-018, HACK-035
- **Paths:** stuffplus/staff.py, analysis/staff_audit/, reports/staff_audit/, app/pages/8_Staff_Diablos.py, tests/test_staff.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - For the Harp Helú-candidate staff (anonymized): each pitcher's Stuff+ at home vs road, the pitch to reduce at home and the one to lean on, recommended starter rotation order for home series vs road series, bullpen matchups.
  - Projected runs saved per season if the recommendations are applied (HACK-035 conversion). Clear caveat: identification is inferred.
- **Verify:** `python -m pytest -q tests/test_staff.py`
- **Next step:** join `artifacts/team_map.parquet` with the pitcher × pitch_id leaderboard.

## HACK-033 · Pitch design lab: "what tweak gains the most Stuff+ at 2,240 m"

- **Type:** feature
- **Priority:** P1
- **Estimate:** 6 h
- **Rubric / Spec:** C4 C3
- **Depends on:** HACK-004, HACK-010
- **Uses contract:** HACK-017, HACK-019
- **Paths:** stuffplus/design_lab.py, app/pages/6_Laboratorio.py, reports/design_lab/, tests/test_design_lab.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - For a pitcher's arsenal: marginal ΔStuff+ in CDMX for realistic tweaks (+1 mph, ±5° spin axis, +5 % spin efficiency, lower arm slot, add a splitter / sinker / sweeper at the pitcher's own velo and slot), constrained to tweaks observed in comparable pitchers. Ranked "development plan" of the top 3 tweaks.
- **Verify:** `python -m pytest -q tests/test_design_lab.py`
- **Next step:** finite differences on the bundle through `physics.translate` + the Stuff+ model.

## HACK-034 · Pitcher card (Savant-style one-pager, PNG/PDF export) for coach and deck

- **Type:** feature
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-016
- **Uses contract:** HACK-015, HACK-018, HACK-019
- **Paths:** stuffplus/cards.py, app/pages/7_Tarjeta.py, reports/cards/, tests/test_cards.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - One card per pitcher: arsenal table (usage, velo, movement, Stuff+ neutral vs Harp Helú, Location+, Pitching+), movement plot with CDMX arrows, altitude-proof index, top 3 recommendations. Diablos visual identity; export PNG (kaleido/matplotlib) and PDF.
  - Batch export for the Diablos-candidate staff and for the deck examples.
- **Verify:** `python -m pytest -q tests/test_cards.py`
- **Next step:** layout with matplotlib gridspec at 1600×900.

## HACK-035 · Business value: Stuff+ → runs → wins → recruiting value for LMB

- **Type:** feature
- **Priority:** P1
- **Estimate:** 4 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-030
- **Uses contract:** HACK-016, HACK-003
- **Paths:** stuffplus/value.py, analysis/business_value/, reports/business_value/, tests/test_value.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - LMB runs-per-win from the data (team runs per game from halves, game winners, Pythagorean exponent fit). Conversion table: +1 Stuff+ point over N pitches → runs saved → wins, at home (CDMX environment) and league-wide.
  - "Value of an altitude-proof arm" example: runs/wins difference between a high-loss and an altitude-proof pitcher over a season of home starts.
- **Verify:** `python -m pytest -q tests/test_value.py`
- **Next step:** reconstruct game scores by summing `RunsScored` per (game, half).

## HACK-022 · Operational recommendations memo (gainers, losers, recruiting guide, tactics)

- **Type:** docs
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C4 C3
- **Depends on:** HACK-015, HACK-017, HACK-018
- **Uses contract:** HACK-009, HACK-032, HACK-035
- **Paths:** reports/recommendations/, app/pages/5_Recomendaciones.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `reports/recommendations/memo.md` (Spanish, 2 pages): 1) perfiles que GANAN en CDMX + física; 2) perfiles que PIERDEN + riesgo cuantificado de contacto duro/HR; 3) cómo perfilar un prospecto/agente libre (checklist con umbrales numéricos); 4) tácticas en casa vs gira (secuencias, conteos, ubicación); 5) valor en carreras y victorias.
  - Every number traces to a CSV in `reports/`. Page `5_Recomendaciones` renders it.
- **Verify:** `test -s reports/recommendations/memo.md`
- **Next step:** top-3 gainers/losers from `reports/altitude_delta/delta_by_shape.csv`.

## HACK-023 · Technical document final (6–10 pages PDF)

- **Type:** docs
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C1 C2 C3 C4
- **Depends on:** HACK-008, HACK-014, HACK-015
- **Uses contract:** HACK-017, HACK-022
- **Paths:** docs/technical/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - All TODOs filled with numbers from `reports/`; figures embedded; 6–10 pages (`docs/technical/stuffplus2240.pdf`); required sections: marco teórico, decisiones de modelado (arquitectura, features, función de pérdida), definición formal de Stuff+ y normalización, validación (pitcher / season / park holdout), alcance y fronteras.
  - Every claim cites a table or reference; consistency pass.
- **Verify:** `test -s docs/technical/stuffplus2240.pdf`
- **Next step:** `docs/technical/build.sh`, then trim to ≤ 10 pages.

## HACK-036 · Visual storytelling: executive deck (≤ 10 slides) + one-page executive summary

- **Type:** docs
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-015
- **Uses contract:** HACK-022, HACK-032, HACK-034, HACK-035
- **Paths:** demo/deck/, demo/one-pager/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Deck for the 10-min interview, story arc: problema (aire de la CDMX) → evidencia (ρ̂ por estadio, −3.7" de ride) → modelo (validado vs baseline) → qué gana / qué pierde → staff de Diablos → prospectos → valor en victorias → demo en vivo. Diablos identity, one idea per slide, every number sourced.
  - One-page executive summary PDF for the GM. Export PDF + PPTX.
- **Verify:** `test -s demo/deck/README.md`
- **Next step:** storyboard the 10 slides in `demo/deck/README.md` with the source CSV of each number.

## HACK-024 · Deploy dashboard (Streamlit Community Cloud) with aggregates only + raw-data leak check

- **Type:** integration
- **Priority:** P1
- **Estimate:** 3 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-020
- **Paths:** deploy/, scripts/check_no_raw_data.py, tests/test_no_raw_data.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `scripts/check_no_raw_data.py` fails if any tracked or bundled file has > 1,000 pitch-level rows (PitchUID or per-pitch physical columns) or any parquet/pkl/rds is tracked.
  - Deploy bundle (models + aggregated tables, ≤ 100 MB), unlisted URL, README link, local fallback documented. The human (joahan) approves the publish.
- **Verify:** `python -m pytest -q tests/test_no_raw_data.py`
- **Next step:** leak checker over `git ls-files` and `artifacts/bundle/`.

## HACK-025 · Demo, jury interview prep and submission package

- **Type:** demo
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-022, HACK-023
- **Uses contract:** HACK-020, HACK-024, HACK-036
- **Paths:** demo/script.md, demo/qa.md, submission/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `demo/script.md`: 3-min flow with the wow ≤ 40 s; `demo/qa.md`: 30 likely jury questions (pitching coach, GM, data scientist, physicist) with 2-line answers backed by numbers, including the hard ones (label shift, park identification confidence, overfitting, why not MLB data).
  - `demo/planb.mp4` (human). `submission/checklist.md`: email to itamsportsanalytics@gmail.com with the 4 member emails (from the git-ignored `submission/EQUIPO.local.md`), PDF, per-pitch scores file, leaderboards, dashboard link, repo link; enrollment proofs ready.
  - Rehearsal from a clean clone on another laptop.
- **Verify:** `test -s submission/checklist.md`
- **Next step:** `demo/script.md` around the IDEA §4 flow.

## HACK-026 · Benchmark model: GAM / partial pooling vs LightGBM (robustness evidence)

- **Type:** feature
- **Priority:** P2
- **Estimate:** 6 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-002, HACK-005
- **Uses contract:** HACK-010
- **Paths:** stuffplus/models/bench/, analysis/benchmark/, reports/benchmark/, tests/test_benchmark.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - pyGAM xRV model with ρ̂ interactions (`te(ivb, rho)`) and partial pooling by shape; same splits and metrics; table vs LightGBM and baseline; ensemble if competitive.
- **Verify:** `python -m pytest -q tests/test_benchmark.py`
- **Next step:** `LinearGAM(s(velo)+s(ivb)+s(hb)+te(ivb, rho))`.

## HACK-027 · Tactical layer: Causal Forest for pitch selection by count (optional)

- **Type:** feature
- **Priority:** P2
- **Estimate:** 6 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-012
- **Paths:** analysis/causal/, reports/causal/, tests/test_causal.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - econml `CausalForestDML`: treatment = breaking ball vs changeup (or vs fastball) on xRV, conditioning on count, batter side, pitcher profile, previous pitch, ρ̂. Heterogeneous effects by count × altitude; caveats (observational, confounding by intent).
- **Verify:** `python -m pytest -q tests/test_causal.py`
- **Next step:** treatment/outcome frame from Pitching+ OOF predictions.

## HACK-028 · Model tuning, monotone constraints, multi-seed ensemble and final retrain

- **Type:** feature
- **Priority:** P1
- **Estimate:** 6 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-014
- **Uses contract:** HACK-026
- **Paths:** stuffplus/models/tuning.py, analysis/tuning/, reports/tuning/, tests/test_tuning.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Search on pitcher-grouped CV (never the 2026 holdout), monotone constraints where physics justifies them (velo ↑ ⇒ xRV ↓ for fastballs), multi-seed averaging; before/after table on the validation suite. Final retrain on all data for the deployed bundle.
- **Verify:** `python -m pytest -q tests/test_tuning.py`
- **Next step:** search space and objective on `pitcher_group_kfold`.
