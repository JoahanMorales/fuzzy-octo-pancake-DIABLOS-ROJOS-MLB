# TASKS · Stuff+ 2240 (ISAC Hackathon 2026 · Diablos Rojos) · 4 humans × 2 agents · deadline 2026-10-22

State lives on the `claims` branch (`uak status`); this file holds only tasks. Rubric: C1 model quality · C2 OOS robustness · C3 arsenal + altitude · C4 applicability (25 % each).

Global rules for every task (read before claiming):
- Raw data lives ONLY in `data/raw/stuff_model_df.parquet` (git-ignored, each human copies it). **Never commit raw data or pitch-level outputs**; commit code, aggregated tables (CSV ≤ 2 MB) and figures. Results can be shown, data cannot.
- Load data only through `stuffplus.io.load_raw()` / `stuffplus.schema.clean()`. Tests run on the synthetic fixture from `tests/conftest.py` (no raw data in CI). Heavy runs go in `analysis/<task>/run.py` and write to `reports/<task>/`.
- Use the shared splits in `stuffplus/splits.py` and the null baseline in `stuffplus/baseline.py`. Every model reports vs the baseline.
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
  - `requirements.txt` pins `pyarrow>=20`, pandas, numpy, scipy, scikit-learn, lightgbm, shap, streamlit, plotly, matplotlib, networkx, python-louvain (or `networkx.community.louvain_communities`), pytest, pygam, econml (optional extra).
  - `stuffplus.config` resolves `DATA_PATH` from env `STUFFPLUS_DATA` (default `data/raw/stuff_model_df.parquet`), `ARTIFACTS_DIR=artifacts/`, `REPORTS_DIR=reports/`.
  - `stuffplus.io.load_raw(columns=None)` reads the parquet with pyarrow; clear error message if pyarrow < 20 or the file is missing.
  - `tests/conftest.py` exposes a `synthetic_pitches` fixture: ~5,000 rows with the SAME 84 columns/dtypes as the raw file, 3 seasons, 3 altitude buckets, ≥ 40 pitchers, ≥ 30 games, realistic ranges (velo 75–100, IVB −20–25, spin 1500–3000), Extreme games with ~16 % lower drag. Generated in code (no real rows).
  - README: what the project is, how to install, where to put the data, how to run tests and the dashboard.
- **Verify:** `python -m pytest -q tests/test_io.py`
- **Next step:** write `requirements.txt` and `tests/conftest.py` with the column list from `data/stuff_plus_data_dictionary.csv`.

## HACK-002 · Contract: clean table schema, targets & run value, shared splits, predict API (mock)

- **Type:** contract
- **Priority:** P0
- **Estimate:** 4 h
- **Rubric / Spec:** C1 C2
- **Depends on:** None
- **Uses contract:** HACK-001
- **Paths:** stuffplus/schema.py, stuffplus/targets.py, stuffplus/splits.py, stuffplus/api.py, docs/CONTRACT.md, tests/test_contract.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `schema.clean(df)`: drops rows with NaN `altitude_category`, `Undefined` hands, `Switch` batters (or maps to the side faced), pitch types `Other/OneSeam/TwoSeam/Knuckleball`; maps `Sweeper → Slider` (document it); casts `EffectiveVelo` to float; adds `pitch_idx_in_game`, `pa_id` (game + inning + half + batter run), `is_rhp`, `same_side`. Exposes `PHYSICAL_FEATURES`, `LOCATION_FEATURES`, `CONTEXT_FEATURES`, `TARGET_COLUMNS`, `ID_COLUMNS` lists. Leakage guard: `assert_no_target_leak(features)`.
  - `targets.py`: outcome flags (whiff = StrikeSwinging / swings, chase = swing outside zone, called strike, weak contact = ExitSpeed < 88 mph or popup, groundball, hard/barrel = EV ≥ 95 & LA 8–32 (document definition), out in PA). **Run value per pitch, calibrated to LMB:** count-transition value (RE by outs×count estimated from `RunsScored` to end of half-inning on LMB data) + event linear weights (1B/2B/3B/HR/BB/HBP/out) fitted on LMB. Function `add_run_value(df)` → `rv` column; table of linear weights saved to `reports/contract/linear_weights.csv`.
  - `splits.py`: `pitcher_group_kfold(df, k=5, seed=2240)`, `season_holdout(df, train=(2024, 2025), test=(2026,))`, `park_holdout(df, train=('No Altitude','Medium Altitude'), test=('Extreme Altitude',))`. Deterministic.
  - `api.py`: dataclass `PitchInput` (pitch_type, throws, velo, spin_rate, spin_axis, ivb, hb, rel_height, rel_side, extension, optional plate_x/plate_z/balls/strikes/batter_side, optional arsenal context) and `predict_pitch(p: PitchInput, rho: float | str = "harp_helu") -> dict` returning `{stuff_plus, location_plus, pitching_plus, xrv, probs:{...}, movement_expected:{ivb,hb}, demo_data: bool}`. Backed by a deterministic MOCK until `stuffplus/serving.py` exists (then dispatch to it).
  - `docs/CONTRACT.md` documents all of the above with examples.
- **Verify:** `python -m pytest -q tests/test_contract.py`
- **Next step:** in `stuffplus/targets.py`, compute RE(outs, balls, strikes) = mean runs scored until end of half-inning; validate it is monotone in strikes.

## HACK-003 · Spike: identify parks / Harp Helú from pitcher co-appearance + air density

- **Type:** spike
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-004
- **Paths:** stuffplus/physics/parks.py, analysis/park_id/, reports/park_id/, tests/test_parks.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Per season, build a weighted graph of pitchers who pitched in the same (game, half) with ≥ 5 pitches; run Louvain/Leiden community detection → teams. (Naive connected components merge everything because of trades: proven 2026-10-12.)
  - Home team per game = team of the **Top-half** pitchers (home team pitches the top). Validate: each team should be home in ~50 % of its games and its home games should share one `altitude_category` with purity ≥ 0.9.
  - Join per-game drag index ρ̂ (from HACK-004, or a local copy of `kdrag = −(a·v)/|v|³` with `az0 + 32.174`). The Extreme-altitude home team with the lowest median ρ̂ is the **Harp Helú candidate**; report its ρ̂ vs theoretical 2,240 m (~0.78–0.80 of sea level) and vs other Extreme parks (e.g. Puebla 2,135 m).
  - Output `reports/park_id/park_map_summary.csv` (cluster, n_home_games, altitude bucket, purity, ρ̂ median/IQR) and `artifacts/park_map.parquet` (game → park_cluster, is_harp_helu_candidate). Clear statement of confidence; fallback if not separable: use the "Extreme bucket" + note.
- **Verify:** `python -m pytest -q tests/test_parks.py`
- **Next step:** `analysis/park_id/run.py`: networkx graph per season with edge weights = shared (game, half) appearances; `louvain_communities(weight='weight', seed=2240)`.

## HACK-004 · Physics: per-game air density index, drag/Magnus decomposition, movement translation model

- **Type:** feature
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002
- **Paths:** stuffplus/physics/__init__.py, stuffplus/physics/constants.py, stuffplus/physics/aero.py, stuffplus/physics/translate.py, analysis/physics/, reports/physics/, tests/test_physics.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `aero.decompose(df)`: from the 9-parameter fit (`vx0..vz0`, `ax0..az0`) compute drag acceleration (along −v), Magnus acceleration (perpendicular to v, gravity removed), `Cd`-proxy = drag/v², `Cl`-proxy = magnus/v², **spin efficiency** = Magnus-implied transverse spin / `SpinRate` (Nathan's method), and active-spin estimate. Unit tests on a synthetic trajectory with known values.
  - `aero.game_density_index(df)`: per game ρ̂ = median Cd-proxy of fastballs (Four-Seam + Sinker) ÷ sea-level median (No Altitude). Report distribution by bucket (exploration found Extreme/No ≈ 0.838, Medium/No ≈ 0.89). Shrink games with < 30 fastballs toward their bucket mean.
  - `constants.py`: `RHO_SEA_LEVEL=1.0`, `RHO_HARP_HELU` (empirical from HACK-003 if available, else barometric formula at 2,240 m with a typical CDMX temperature; document both), `RHO_COORS`.
  - `translate.py`: movement model `expected_movement(release+spin features, rho) → (ivb, hb, speed_drop)` fit on **within-pitcher** variation (pitcher × pitch type fixed effects, or LightGBM on physical features + ρ̂ with pitcher-mean centering). Must reproduce the within-pitcher four-seam ΔIVB ≈ −3.7" (Extreme vs No, n≈404) within its CI. `translate_pitch(pitch, rho_from, rho_to)` returns movement in the other air.
  - `reports/physics/`: ρ̂ histogram per bucket, ΔIVB/ΔHB by pitch type with bootstrap 95 % CI, a 1-page `README.md` explaining the physics (Magnus ∝ ρ, drag ∝ ρ) for the tech doc.
- **Verify:** `python -m pytest -q tests/test_physics.py`
- **Next step:** implement `aero.decompose` with numpy; test with a trajectory built from known Cd/Cl.

## HACK-005 · Null baseline + evaluation harness (RMSE, log-loss, calibration, by split)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C1 C2
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002
- **Paths:** stuffplus/baseline.py, stuffplus/evaluate.py, reports/baseline/, tests/test_evaluate.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `baseline.CountBaseline`: predicts mean `rv` (and each target probability) by count (and by count × pitch type as a stronger baseline). This is the rubric's "null model".
  - `evaluate.report(y_true, y_pred, kind)`: RMSE / MAE / R² for xRV; log-loss, Brier, AUC, ECE + reliability-curve data for probabilities; returns a tidy DataFrame; `evaluate.compare(models: dict, split)` produces one table with **skill vs baseline** (% RMSE reduction).
  - Pitcher-level metric: correlation of pitcher-season mean predicted xRV with next-season observed RV / runs-allowed proxy (the "predictiveness" that defines a good Stuff+).
  - `reports/baseline/baseline_metrics.csv` for all three splits.
- **Verify:** `python -m pytest -q tests/test_evaluate.py`
- **Next step:** write `CountBaseline.fit/predict` with groupby on `count`.

## HACK-006 · Arsenal & sequence features: primary fastball diffs, tunneling, usage, previous pitch

- **Type:** feature
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002
- **Paths:** stuffplus/features/__init__.py, stuffplus/features/arsenal.py, stuffplus/features/sequence.py, tests/test_features.py, reports/features/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Primary fastball per pitcher-season (most used of Four-Seam/Sinker/Cutter fallback). `velo_diff_vs_fb`, `ivb_diff_vs_fb`, `hb_diff_vs_fb` (HB mirrored for LHP), `spin_diff_vs_fb`, `axis_diff_vs_fb`, `pitch_usage_pct`, arsenal size, arsenal spread (movement range).
  - **Tunneling:** release-point distance to the primary FB (`RelHeight`, `RelSide`, `Extension`) AND position difference at the batter decision point (~23.8 ft from plate, ~0.167 s before plate) computed from `PitchTrajectory*c0..c2` polynomials, vs plate-location difference → `tunnel_ratio` (late break vs early similarity).
  - Sequence (rows are in game order — verified): `prev_pitch_type`, `prev_velo_diff`, `prev_loc_diff`, same-PA pitch number, `times_through_order` estimate.
  - **No leakage:** arsenal stats computed out-of-fold/out-of-season option (`fit_arsenal(train) → transform(test)`), and computed on the pitcher's OWN pitches only.
  - All features mirrored for handedness consistently (document convention).
- **Verify:** `python -m pytest -q tests/test_features.py`
- **Next step:** `arsenal.primary_fastball(df)` grouped by (pitcher_anon_id, year).

## HACK-007 · Dashboard skeleton + design lock (Streamlit, Diablos theme) on the mock predict API

- **Type:** feature
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C4
- **Depends on:** None
- **Uses contract:** HACK-002
- **Paths:** app/, .streamlit/, tests/test_app_smoke.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `app/Home.py` (entry) + pages placeholders: `1_Simulador`, `2_Leaderboard`, `3_Prospecto`, `4_Altitud`, `5_Recomendaciones`. Spanish UI.
  - `app/DESIGN.md` + `.streamlit/config.toml`: one visual direction (Diablos red `#C8102E`-ish, black, white; condensed sport font), tokens in one place `app/theme.py`. Projector check at 1280×720: the wow (Stuff+ CDMX vs nivel del mar side-by-side + movement map with arrows) fits without scrolling.
  - Simulator form → `stuffplus.api.predict_pitch` (mock) → two gauges (Harp Helú vs nivel del mar) + plotly movement map (HB vs IVB) with arrow from sea-level movement to CDMX movement. Every mock number shows a `demo_data` badge. Every number has a tooltip with its source.
  - Empty / loading / error states. Runs with `streamlit run app/Home.py`.
- **Verify:** `python -m pytest -q tests/test_app_smoke.py`
- **Next step:** `tests/test_app_smoke.py` with `streamlit.testing.v1.AppTest.from_file("app/Home.py").run()` asserting no exception.

## HACK-008 · Technical document skeleton + literature + theory (sabermetrics × physics × LMB)

- **Type:** docs
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C1 C2 C3 C4
- **Depends on:** None
- **Paths:** docs/technical/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `docs/technical/paper.md` (Spanish, pandoc → PDF via `docs/technical/build.sh`; LaTeX template optional) with sections: 1 Introducción · 2 Marco teórico (Stuff+/Location+/Pitching+ FanGraphs; física: Magnus ∝ ρ, drag ∝ ρ, Nathan, SABR High Altitude Offense; LMB/Harp Helú) · 3 Datos · 4 Metodología (física en dos etapas, targets, run value LMB, escala) · 5 Validación · 6 Resultados de altitud · 7 Recomendaciones · 8 Alcance y fronteras · Referencias. Each section has TODO markers naming the task that fills it.
  - `docs/technical/references.bib` with every reference from the challenge + Nathan (pitch trajectory / spin efficiency), FanGraphs Stuff+ primer, Statcast run value. Only verified URLs.
  - Formal definition of the Stuff+ scale (LaTeX math) written now (100 + 10·z, normalization per season over all LMB pitches).
  - Page budget plan: 6–10 pages.
- **Verify:** `test -s docs/technical/paper.md`
- **Next step:** draft §2 Marco teórico with the physics derivation of why movement scales with ρ.

## HACK-009 · Hypotheses H1–H4 with LMB evidence (bootstrap CIs, within-pitcher design)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-001, HACK-002, HACK-004
- **Paths:** analysis/hypotheses/, reports/hypotheses/, stuffplus/hypotheses.py, tests/test_hypotheses.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - **H1** movement loss: within-pitcher × pitch-type ΔIVB, ΔHB, Δtotal break, Δspeed drop (Extreme vs No, Medium vs No) with pitcher-cluster bootstrap 95 % CI; dose-response vs ρ̂ (slope per 0.1 ρ).
  - **H2** velocity-differential pitches: change in whiff/chase/xRV for changeups/splitters vs breaking balls across altitude, controlling for pitcher (paired). Note the exploratory finding: changeups lose ~4.1" of fade, so the hypothesis might fail; report honestly.
  - **H3** groundballs: HR/FB, ISO-proxy, distance, xRV of fly balls vs grounders by altitude; does GB% correlate more with run prevention in Extreme? (pitcher-level regressions with interaction).
  - **H4** spin vs movement: predictive power of SpinRate alone vs movement/spin efficiency for whiff and xRV, by altitude (ΔAUC, partial R²).
  - `reports/hypotheses/summary.md`: one table per hypothesis, verdict (Supported / Partially / Rejected), effect size, CI, n. Figures in PNG.
- **Verify:** `python -m pytest -q tests/test_hypotheses.py`
- **Next step:** `stuffplus/hypotheses.py::within_pitcher_delta(df, metric, pitch_type, a, b, min_n=20, n_boot=2000)`.

## HACK-013 · Stuff+ scale & normalization module

- **Type:** feature
- **Priority:** P0
- **Estimate:** 2 h
- **Rubric / Spec:** C1
- **Depends on:** None
- **Uses contract:** HACK-002
- **Paths:** stuffplus/scale.py, tests/test_scale.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `PlusScaler(by=("year",), sign=-1).fit(xrv_pred, groups).transform(...)` → 100 + 10·z, where the reference mean/sd are LMB pitches of that season (park-neutral reference ρ = sea level by default; option `reference="harp_helu"`). Also `by=("year","pitch_type")` variant.
  - Saves/loads the reference stats to JSON (so the dashboard can score new pitches). Aggregation helpers: pitch → pitcher / pitch type / arsenal (usage-weighted) with min-pitch thresholds and shrinkage toward 100 (empirical Bayes) for small samples.
  - Test: synthetic normal xRV → mean 100, sd 10; 120 ≈ p97.7.
- **Verify:** `python -m pytest -q tests/test_scale.py`
- **Next step:** implement `PlusScaler.fit` storing per-group mean/sd.

## HACK-029 · Pitch shape clustering (shape over label) per handedness

- **Type:** feature
- **Priority:** P0
- **Estimate:** 4 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-002, HACK-004
- **Paths:** stuffplus/features/shapes.py, tests/test_shapes.py, reports/shapes/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Cluster pitches into interpretable **pitch shapes** (e.g. "riding 4S", "sinking 2S", "gyro slider", "sweeper", "12-6 CB", "power CH", "splitter") using velo, IVB, HB (mirrored for LHP), spin, axis, arm angle (from RelHeight/RelSide). Use **sea-level-translated movement** when HACK-004 is available so altitude does not create fake clusters.
  - Each shape has a name, centroid, n, and ≥ 90 % of pitches assigned. `assign_shape(pitch)` works for a single dashboard input.
  - `reports/shapes/shapes.csv` + scatter figure.
- **Verify:** `python -m pytest -q tests/test_shapes.py`
- **Next step:** Gaussian mixture per (throws, AutoPitchType family) with BIC-selected k.

## HACK-010 · Stuff+ model (physics at release + arsenal + ρ), LightGBM, pitcher GroupKFold

- **Type:** feature
- **Priority:** P0
- **Estimate:** 10 h
- **Rubric / Spec:** C1 C2 C3
- **Depends on:** HACK-001, HACK-002
- **Uses contract:** HACK-004, HACK-005, HACK-006, HACK-013
- **Paths:** stuffplus/models/__init__.py, stuffplus/models/common.py, stuffplus/models/stuff.py, analysis/stuff_model/, reports/stuff_model/, tests/test_model_stuff.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Features: physical only (velo, spin, axis, IVB, HB, release height/side, extension, VAA/HAA optional with justification, spin efficiency from HACK-004) + arsenal diffs (HACK-006) + handedness + **ρ̂** (continuous, not the bucket). No location, count or outcome columns (leak guard from schema).
  - Targets: xRV regression (main) + whiff/called-strike/GB/hard-contact classifiers. Out-of-fold predictions with `pitcher_group_kfold`.
  - Report vs `CountBaseline`: RMSE skill, log-loss, calibration on OOF. Save model + feature list + reference stats to `artifacts/models/stuff/` (git-ignored) and metrics to `reports/stuff_model/metrics.csv`.
  - `predict_at_rho(df, rho)`: evaluates the same pitches at a counterfactual density, translating movement with `physics.translate` when available.
- **Verify:** `python -m pytest -q tests/test_model_stuff.py`
- **Next step:** `models/common.py::train_lgbm_oof(df, features, target, folds, objective)`.

## HACK-011 · Location+ model (zone × count × batter side × pitch shape)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-001, HACK-002
- **Uses contract:** HACK-005, HACK-029
- **Paths:** stuffplus/models/location.py, analysis/location_model/, reports/location_model/, tests/test_model_location.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Marginal value of location: xRV from (PlateLocSide mirrored, PlateLocHeight, balls, strikes, batter side / same_side, pitch shape) WITHOUT pitch physics → Location+ scale. 9-quadrant + chase-zone summaries.
  - Heatmaps per pitch shape × count bucket (ahead / even / behind) in `reports/location_model/`.
  - OOF vs baseline metrics; artifacts in `artifacts/models/location/`.
- **Verify:** `python -m pytest -q tests/test_model_location.py`
- **Next step:** smooth 2-D target encoding vs LightGBM on (x, z, count); pick by OOF RMSE.

## HACK-012 · Pitching+ multi-target model and weighted combination to the final score

- **Type:** feature
- **Priority:** P0
- **Estimate:** 10 h
- **Rubric / Spec:** C1 C2 C3
- **Depends on:** HACK-010, HACK-011
- **Uses contract:** HACK-006, HACK-013
- **Paths:** stuffplus/models/pitching.py, stuffplus/models/multitarget.py, analysis/pitching_model/, reports/pitching_model/, tests/test_model_pitching.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Targets: P(whiff | swing), P(chase), P(called strike), P(weak contact), P(groundball), P(hard/barrel), xRV, P(out within PA).
  - Features: stuff + location + arsenal + sequence + context (count, outs, inning, same_side) + ρ̂.
  - **Combination weights fitted, not chosen:** regress observed `rv` on the out-of-fold probabilities (ridge, non-negative where sensible) → combined xRV → Pitching+. Report weights table and its stability across folds.
  - Calibration plots per target, OOF metrics vs baseline. Artifacts in `artifacts/models/pitching/`.
- **Verify:** `python -m pytest -q tests/test_model_pitching.py`
- **Next step:** loop over targets with `train_lgbm_oof` from `models/common.py`.

## HACK-014 · Validation suite: pitcher, season, park holdout + year-to-year stability

- **Type:** feature
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-005, HACK-010
- **Uses contract:** HACK-011, HACK-012
- **Paths:** stuffplus/validation/, analysis/validation/, reports/validation/, tests/test_validation.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - One command runs all splits for Stuff+, Location+, Pitching+ and the baseline; output `reports/validation/validation_table.csv` + `validation.md` (model × split × metric, skill vs baseline).
  - **Park holdout:** train No + Medium → test Extreme; show calibration in Extreme with and without ρ̂ (proves the altitude feature matters).
  - **Stability:** split-half reliability of pitcher Stuff+ (odd/even games), year-to-year correlation 2024→2025, 2025→2026, and predictiveness of next-season RV vs raw stats (whiff%, ERA-proxy). This is how public Stuff+ models are judged.
  - Bootstrap CIs on every headline number.
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
  - **Counterfactual:** every pitch scored at ρ_sea and ρ_HarpHelú (movement translated by `physics.translate`, then Stuff+ model) → ΔStuff+ per pitch.
  - **Observed check:** within-pitcher Stuff+ in Extreme vs No games agrees in sign/magnitude with the counterfactual (triangulation).
  - Table by pitch shape (HACK-029) and AutoPitchType: mean ΔStuff+, 95 % CI, n, Δwhiff, Δhard-contact, ΔHR/FB risk. Ranking of shapes that **gain** vs **lose** in CDMX with the physical explanation column.
  - `reports/altitude_delta/delta_by_shape.csv` + figure (forest plot) for the tech doc and dashboard page `4_Altitud`.
- **Verify:** `python -m pytest -q tests/test_altitude.py`
- **Next step:** `altitude.counterfactual_scores(df, model, rho_a, rho_b)`.

## HACK-016 · Scoring pipeline + leaderboards per pitch, pitcher, arsenal (Stuff+/Location+/Pitching+)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C1 C4
- **Depends on:** HACK-012, HACK-013
- **Uses contract:** HACK-003, HACK-015
- **Paths:** stuffplus/score.py, analysis/scoring/, reports/leaderboards/, tests/test_score.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `python -m stuffplus.score` scores all pitches → `artifacts/scores/pitch_scores.parquet` (git-ignored; PitchUID + 3 scores) and aggregated CSVs in `reports/leaderboards/`: pitcher-season, pitcher × pitch type, arsenal (usage-weighted), with n and shrinkage.
  - "¿Qué arsenal produce el Stuff+ más alto en Harp Helú?": top arsenals by Stuff+ evaluated at ρ_HarpHelú.
  - Comparison table Stuff+ CDMX vs other LMB parks (by bucket and by park cluster from HACK-003 if available).
- **Verify:** `python -m pytest -q tests/test_score.py`
- **Next step:** load artifacts from `artifacts/models/*` and the scaler JSON; batch predict.

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
  - Partial dependence + SHAP interaction of each physical feature **with ρ̂**: which features matter MORE in altitude (e.g. velocity, VAA, extension, seam-shifted/low-spin-efficiency pitches) vs less (spin-driven ride).
  - Constrained optimization over realistic, jointly-observed regions (stay inside the data's convex hull / kNN density) for: best primary fastball, best secondary given that fastball, best 3-pitch arsenal at ρ_HarpHelú vs at sea level.
  - `reports/ideal_profile/profile.md` with the physical + statistical argument and a 1-figure "receta" for scouts.
- **Verify:** `python -m pytest -q tests/test_profile.py`
- **Next step:** compute 2-D PDP (feature × ρ̂) for velo, IVB, HB, spin efficiency, extension.

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
  - Per pitcher: arsenal ΔStuff+ (CDMX − sea level, counterfactual) + observed home/away split when available, with empirical-Bayes shrinkage and CI. "Altitude-proof index".
  - Top/bottom 15 pitchers (anonymized IDs) with the pitch that drives the loss/gain and the physical reason. This is the intro's explicit ask: who is most affected by altitude and who is most consistent.
- **Verify:** `python -m pytest -q tests/test_sensitivity.py`
- **Next step:** usage-weighted aggregation of per-pitch ΔStuff+ by pitcher-season.

## HACK-019 · Explainability module: SHAP per pitch and global, coach-friendly text

- **Type:** feature
- **Priority:** P1
- **Estimate:** 4 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-010
- **Paths:** stuffplus/explain.py, reports/explain/, tests/test_explain.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `explain_pitch(pitch, rho)` → top-5 SHAP contributions in Stuff+ points + 1-sentence Spanish explanation per feature ("+4 por velocidad 96 mph"). Global beeswarm + dependence plots for the tech doc.
- **Verify:** `python -m pytest -q tests/test_explain.py`
- **Next step:** `shap.TreeExplainer` on the Stuff+ LightGBM; convert to Stuff+ units with the scaler sd.

## HACK-020 · Dashboard integration: real models, CDMX vs sea level, movement map of best/worst pitches

- **Type:** integration
- **Priority:** P0
- **Estimate:** 8 h
- **Rubric / Spec:** C4 C3
- **Depends on:** HACK-007, HACK-015, HACK-016
- **Uses contract:** HACK-019
- **Paths:** stuffplus/serving.py, app/pages/1_Simulador.py, app/pages/2_Leaderboard.py, app/pages/4_Altitud.py, app/components/, tests/test_serving.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `stuffplus/serving.py` loads `artifacts/` (models + scaler + aggregated tables) and implements the `predict_pitch` contract; `api.py` dispatches to it automatically (no `demo_data` badge when real).
  - Simulator: inputs → Stuff+ / Location+ / Pitching+ at Harp Helú vs sea level side by side, movement translation arrows, SHAP "¿por qué?".
  - "Mapa de movimiento": HB vs IVB scatter of the most and least effective pitches per shape, toggle CDMX/sea level.
  - Leaderboard and Altitud pages read only aggregated CSVs (no raw data needed to run the app).
- **Verify:** `python -m pytest -q tests/test_serving.py tests/test_app_smoke.py`
- **Next step:** `serving.load_bundle(artifacts_dir)` + cache with `st.cache_resource`.

## HACK-021 · Prospect / free-agent profiler (arsenal → Stuff+ in CDMX + comparables)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-016
- **Uses contract:** HACK-018, HACK-020
- **Paths:** stuffplus/prospect.py, app/pages/3_Prospecto.py, tests/test_prospect.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Input: 2–5 pitches (type + physical traits) or a CSV in Trackman format. Output: Stuff+ per pitch and arsenal at ρ_HarpHelú vs sea level, altitude-proof index, HR-risk flag, 5 nearest LMB comparables (anonymized) and a 3-line scouting verdict ("Firmar / Desarrollar / Evitar para casa").
- **Verify:** `python -m pytest -q tests/test_prospect.py`
- **Next step:** `prospect.evaluate_arsenal(pitches: list[PitchInput])` reusing serving.

## HACK-022 · Operational recommendations memo (gainers, losers, recruiting guide)

- **Type:** docs
- **Priority:** P0
- **Estimate:** 5 h
- **Rubric / Spec:** C4 C3
- **Depends on:** HACK-015, HACK-017, HACK-018
- **Uses contract:** HACK-009
- **Paths:** reports/recommendations/, app/pages/5_Recomendaciones.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `reports/recommendations/memo.md` (Spanish, 2 pages): 1) perfiles que GANAN Stuff+ relativo en CDMX + física; 2) perfiles que PIERDEN + riesgo cuantificado de contacto duro/HR; 3) cómo perfilar un prospecto/agente libre (checklist con umbrales numéricos); 4) tácticas de uso (secuencias, conteos) en casa vs gira.
  - Every number traces to a CSV in `reports/`. Page `5_Recomendaciones` renders the memo.
- **Verify:** `test -s reports/recommendations/memo.md`
- **Next step:** pull top-3 gainers/losers from `reports/altitude_delta/delta_by_shape.csv`.

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
  - All TODOs filled with final numbers from `reports/`; figures embedded; 6–10 pages in PDF (`docs/technical/stuffplus2240.pdf`); sections required by the challenge: marco teórico, decisiones de modelado (arquitectura, features, función de pérdida), definición formal de Stuff+ y normalización, validación (pitcher/season/park holdout), alcance y fronteras.
  - Spelling/consistency pass; every claim cites a table or reference.
- **Verify:** `test -s docs/technical/stuffplus2240.pdf`
- **Next step:** run `docs/technical/build.sh` and fix overflow to fit 10 pages.

## HACK-024 · Deploy dashboard (Streamlit Community Cloud) with artifacts only + raw-data leak check

- **Type:** integration
- **Priority:** P1
- **Estimate:** 3 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-020
- **Paths:** deploy/, scripts/check_no_raw_data.py, tests/test_no_raw_data.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `scripts/check_no_raw_data.py` fails if any tracked file has > 1,000 rows with PitchUID or pitch-level physical columns, or any parquet/pkl/rds is tracked. Wired into the pre-commit hook docs.
  - Deploy bundle (model files + aggregated CSVs, ≤ 100 MB) published to a private/unlisted URL; README with the link; local fallback documented.
- **Verify:** `python -m pytest -q tests/test_no_raw_data.py`
- **Next step:** write the leak checker over `git ls-files`.

## HACK-025 · Demo, jury interview prep and submission package

- **Type:** demo
- **Priority:** P0
- **Estimate:** 6 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-022, HACK-023
- **Uses contract:** HACK-020, HACK-024
- **Paths:** demo/, submission/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `demo/script.md`: 3-min dashboard flow with the wow ≤ 40 s; `demo/qa.md`: 25 likely jury questions (pitching coach + GM + data scientist) with 2-line answers backed by numbers; `demo/deck.md` (≤ 10 slides).
  - `demo/planb.mp4` recorded (human). `submission/checklist.md`: email to itamsportsanalytics@gmail.com with ALL member emails, PDF, scores files, dashboard link, repo link; proof of enrollment ready.
  - Rehearsal from a clean clone on another laptop.
- **Verify:** `test -s submission/checklist.md`
- **Next step:** draft `demo/script.md` around the IDEA §4 flow.

## HACK-026 · Benchmark model: GAM / hierarchical Bayesian vs LightGBM (robustness evidence)

- **Type:** feature
- **Priority:** P2
- **Estimate:** 6 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-002, HACK-005
- **Uses contract:** HACK-010
- **Paths:** stuffplus/models/bench/, analysis/benchmark/, reports/benchmark/, tests/test_benchmark.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - A pyGAM (or ridge-spline) xRV model with ρ̂ interactions and a partial-pooling estimate by pitch shape; same splits and metrics; table vs LightGBM and baseline. If competitive, consider an ensemble.
- **Verify:** `python -m pytest -q tests/test_benchmark.py`
- **Next step:** pyGAM `LinearGAM(s(velo)+s(ivb)+s(hb)+te(ivb, rho))`.

## HACK-027 · Tactical layer: Causal Forest for pitch selection by count (optional)

- **Type:** feature
- **Priority:** P2
- **Estimate:** 6 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-012
- **Paths:** analysis/causal/, reports/causal/, tests/test_causal.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - econml `CausalForestDML` for treatment = breaking ball vs changeup (or vs fastball) on xRV, conditioning on count, batter side, pitcher Stuff+ profile, previous pitch, ρ̂. Heterogeneous effects table by count × altitude. Clear caveats (observational, confounding by intent).
- **Verify:** `python -m pytest -q tests/test_causal.py`
- **Next step:** build the treatment/outcome frame from the Pitching+ OOF predictions.

## HACK-028 · Model tuning, multi-seed ensemble and final retrain

- **Type:** feature
- **Priority:** P1
- **Estimate:** 6 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-014
- **Uses contract:** HACK-026
- **Paths:** stuffplus/models/tuning.py, analysis/tuning/, reports/tuning/, tests/test_tuning.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Randomized / Optuna search on pitcher-grouped CV (never touching the 2026 season holdout), monotone constraints where physics justifies them (e.g. velo ↑ ⇒ xRV ↓ for fastballs), multi-seed averaging; before/after table on the validation suite. Final retrain on all data for the deployed artifacts.
- **Verify:** `python -m pytest -q tests/test_tuning.py`
- **Next step:** define the search space and objective on `pitcher_group_kfold`.
