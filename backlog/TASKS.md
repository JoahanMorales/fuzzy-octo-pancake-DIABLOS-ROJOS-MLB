# Backlog published on claims (uak plan)

Append-only; added to .uak/TASKS.md from main. Why: adding tasks never waits for a PR.
## HACK-037 · Web setup: Vite + React + TypeScript + three.js app shell with every page routed

- **Type:** setup
- **Priority:** P0
- **Estimate:** 60 min
- **Rubric / Spec:** C4
- **Depends on:** None
- **Paths:** web/package.json, web/package-lock.json, web/vite.config.ts, web/tsconfig.json, web/tsconfig.node.json, web/index.html, web/src/main.tsx, web/src/App.tsx, web/src/routes.tsx, web/src/shell/, web/src/styles/base.css, web/vitest.config.ts, web/playwright.config.ts, web/README.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - All foreseeable deps at once: react, react-dom, react-router-dom, three, @react-three/fiber, @react-three/drei, framer-motion, d3-scale, d3-shape, d3-geo, zod, html-to-image; dev: vite, typescript, vitest, @testing-library/react, jsdom, @playwright/test, eslint.
  - `routes.tsx` discovers pages with `import.meta.glob('./features/*/index.tsx')` and maps `/`, `/simulador`, `/altitud`, `/leaderboard`, `/pitcher/:id`, `/staff`, `/prospecto`, `/laboratorio`, `/metodologia`; a missing feature renders `web/src/shell/Placeholder.tsx`, so feature tasks only create their own folder and never touch the shell.
  - `npm --prefix web run build` produces `web/dist/` with a relative `base` (static hosting, no server); `npm --prefix web test -- --run` passes.
- **Verify:** `npm --prefix web ci && npm --prefix web run build && npm --prefix web test -- --run`
- **Next step:** `npm create vite@5 web -- --template react-ts`, then add the deps above in one install.

## HACK-038 · Web data contract: JSON exports, TS types, mocks and the tree-model format

- **Type:** contract
- **Priority:** P0
- **Estimate:** 60 min
- **Rubric / Spec:** C4 C1
- **Depends on:** HACK-037
- **Uses contract:** HACK-024
- **Paths:** docs/CONTRACT-WEB.md, web/src/contract/, web/public/data/mock/, stuffplus/export_web.py, tests/test_export_web.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `docs/CONTRACT-WEB.md` + `web/src/contract/types.ts` (zod schemas) for: `parks.json` (20 parks: id, ρ̂, bucket, Stuff+ air effect), `shapes.json` (ΔStuff+ by shape with CI, movement deltas), `leaderboard.json` (pitcher-season aggregates), `pitcher/<id>.json` (arsenal per pitch_id), `staff.json`, `validation.json`, `models/<name>.json` (the Stuff+/Location+/Pitching+ composites: multiclass + contact trees, class values, feature and category maps, Plus scaler) and `physics.json` (translator coefficients per family + C_D/C_L for the flight engine).
  - The contract names the model and translation the web uses (see "One model everywhere") and a `model_version` field every file carries.
  - `web/public/data/mock/` holds valid mocks for every file; `stuffplus/export_web.py --mock` regenerates them; zod parses every mock in a vitest test.
  - Exporter refuses pitch-level rows (calls `scripts/check_no_raw_data.py` rules); total `web/public/data` ≤ 25 MB.
- **Verify:** `python -m pytest -q tests/test_export_web.py && npm --prefix web test -- --run src/contract`
- **Next step:** write `types.ts` from the bundle tables in `deploy/bundle/tables/` and `reports/`.

## HACK-039 · Design lock for the React app: Diablos broadcast look, one direction, tokens

- **Type:** design
- **Priority:** P0
- **Estimate:** 45 min
- **Rubric / Spec:** C4
- **Depends on:** None
- **Uses contract:** HACK-037
- **Paths:** web/DESIGN.md, web/src/styles/tokens.css, web/design/
- **Freeze-Allowed:** no
- **Acceptance:**
  - One direction (sprint rule), screenshots of landing hero + simulator mock in `web/design/`; human (luis) picks; DESIGN.md frozen.
  - Diablos red #C8102E + black, type scale, motion rules (prefers-reduced-motion = no camera moves), mobile breakpoints, 3D style (stylized low-poly stadium, not photoreal; pixel-art only as an optional skin later).
- **Verify:** `test -s web/DESIGN.md && grep -q "Frozen" web/DESIGN.md`
- **Next step:** /uak-design-lock with the landing hero and the simulator HUD.

## HACK-040 · Browser model runtime: LightGBM tree evaluator in TypeScript with Python parity

- **Type:** feature
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** C4 C1
- **Depends on:** HACK-037
- **Uses contract:** HACK-038
- **Paths:** web/src/model/, stuffplus/export_trees.py, tests/test_export_trees.py, web/public/data/models/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `export_trees.py` exports the composites the paper uses (multiclass softmax + contact regressor + class values + Plus scaler, `pitch_family` features) to the contract JSON; `web/src/model/predict.ts` scores a feature vector.
  - Parity on **synthetic** golden rows (conftest fixture + random vectors in observed ranges, NaNs and every category): TS within 1e-6 of LightGBM (vitest).
  - Same Plus scaling as `stuffplus.scale` (100 + 10z, park-neutral reference) so browser and paper show identical Stuff+; JSON size budget ≤ 15 MB for all models (prune unused fields, round thresholds only if parity holds).
- **Verify:** `python -m pytest -q tests/test_export_trees.py && npm --prefix web test -- --run src/model`
- **Next step:** `booster.dump_model()` on `deploy/bundle/models/stuff_xrv.txt`.

## HACK-041 · Physics v2: C_L(S), C_D(Re) per air density, trajectory re-flight and elasticity with CIs

- **Type:** feature
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C3 C2 · Nathan et al. 2006 (arXiv physics/0605041); Kagan & Nathan 2014; Smith & Sciacchitano 2022
- **Depends on:** None
- **Paths:** stuffplus/physics/flight.py, stuffplus/physics/coefficients.py, analysis/physics_v2/, reports/physics_v2/, tests/test_physics_v2.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - From each pitch's 9-parameter fit: drag and Magnus accelerations → C_D, C_L, spin parameter S = Rω/v, Re; fit C_L(S) (SHS form: 1.5S below 0.1, a + bS above) and C_D(Re) by bucket with pitcher-cluster CIs.
  - Answer the open gap: how much of "C_L −24 % vs C_D −16 %" is explained by lower S (ball arrives faster) and how much remains (seam-shifted-wake hypothesis: test on ≥ 95 % efficiency four-seamers only). Report as measured vs hypothesis.
  - `flight.py`: RK4 re-flight of a release (v0, spin, axis, release point) at any ρ; elasticity of Magnus acceleration vs ρ per park (slope and 95 % CI; physics predicts ≈ 1).
  - `reports/physics_v2/physics.json` in the HACK-038 contract format (coefficients for the browser engine).
- **Verify:** `python -m pytest -q tests/test_physics_v2.py`
- **Next step:** reuse the drag/Magnus decomposition in `stuffplus/physics/aero.py`.

## HACK-042 · Browser physics engine: RK4 pitch flight in TypeScript with Python parity

- **Type:** feature
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** C4 C3
- **Depends on:** HACK-037
- **Uses contract:** HACK-038, HACK-041
- **Paths:** web/src/physics/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `flyPitch({velo, spin, axis, release, extension, rho})` returns positions every 1/240 s, plate crossing, IVB/HB, flight time, using the HACK-041 coefficients (mock until they land).
  - Parity with `stuffplus/physics/flight.py` on 50 **synthetic** releases (generated in ranges, not from data): plate location within 0.1 in, IVB/HB within 0.2 in.
  - Moving ρ from 1.0 to 0.819 reduces four-seam IVB by the amount reported in HACK-041 (± 0.3 in).
- **Verify:** `npm --prefix web test -- --run src/physics`
- **Next step:** port the RK4 step from HACK-041 and its golden CSV.

## HACK-043 · Landing page: the story in 40 seconds

- **Type:** feature
- **Priority:** P0
- **Estimate:** 2 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-037
- **Uses contract:** HACK-038, HACK-039
- **Paths:** web/src/features/landing/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Hero with an animated ball flying at sea level vs CDMX (three.js, reduced-motion fallback to a static diagram), the three numbers that win (league −10.3 Stuff+ in CDMX air; Pitching+ +3.88 % vs the null; bias −82 % in unseen altitude) read from `validation.json`/`shapes.json`, never typed.
  - Scroll story: problema → evidencia → modelo → qué gana/pierde → staff → prospectos → valor en victorias → CTA "Probar el simulador".
  - Lighthouse performance ≥ 80 and accessibility ≥ 90 on desktop (report in the PR).
- **Verify:** `npm --prefix web test -- --run src/features/landing`
- **Next step:** build the hero on the DESIGN.md mock.

## HACK-044 · 3D simulator I: stadium scene, cameras, batter that switches sides

- **Type:** feature
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-037
- **Uses contract:** HACK-039, HACK-042
- **Paths:** web/src/features/simulador/scene/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Stylized stadium (mound, plate, strike zone, Harp Helú skyline vs sea-level park toggle), cameras: catcher, pitcher, side, broadcast; smooth transitions (none with reduced motion).
  - Batter model switches L/R with an animation; zone and handedness-dependent features update.
  - 60 fps on a mid laptop (stats overlay in dev); scene works without WebGL2 (fallback message + 2D view).
- **Verify:** `npm --prefix web test -- --run src/features/simulador/scene`
- **Next step:** r3f `<Canvas>` with drei `CameraControls` and a placeholder ball path.

## HACK-045 · 3D simulator II: pitch flight, CDMX vs sea level ghost, controls and live Stuff+

- **Type:** feature
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C4 C3
- **Depends on:** HACK-044
- **Uses contract:** HACK-040, HACK-042, HACK-038
- **Paths:** web/src/features/simulador/flight/, web/src/features/simulador/panel/, web/src/features/simulador/index.tsx
- **Freeze-Allowed:** no
- **Acceptance:**
  - Controls: pitch family, velo, spin, axis, release, extension, count, batter side, park (20 parks by ρ̂) or a ρ slider; presets "recta de ride", "sweeper", "splitter", "lanzador del staff".
  - Throw animates the same release twice: sea-level ghost vs park ball with trails; plate dots and the movement lost in inches.
  - Panel: Stuff+ / Location+ / Pitching+ at sea level vs this park (TS model, HACK-040, scored with the published translation), ΔStuff+, the "¿por qué?" breakdown, and badge "modelo real" vs "demo".
  - Test: each shape preset at the Harp Helú preset reproduces its ΔStuff+ in `delta_by_shape.csv` within ±1.5 points.
- **Verify:** `npm --prefix web test -- --run src/features/simulador`
- **Next step:** wire `flyPitch` into a `<Trail>` and the model into the panel.

## HACK-046 · Altitude page: Mexico map of 20 parks by air density and ΔStuff+ by pitch shape

- **Type:** feature
- **Priority:** P1
- **Estimate:** 2 h
- **Rubric / Spec:** C3 C4
- **Depends on:** HACK-037
- **Uses contract:** HACK-038
- **Paths:** web/src/features/altitud/
- **Freeze-Allowed:** no
- **Acceptance:** SVG map of Mexico with the 20 inferred parks sized by ρ̂ (identity labelled "inferida"), forest plot of ΔStuff+ by shape with CIs, toggle CDMX / sea level; numbers from contract files only.
- **Verify:** `npm --prefix web test -- --run src/features/altitud`
- **Next step:** d3-geo projection of a public-domain Mexico outline (cite the source in the page).

## HACK-047 · Leaderboard, pitcher page and Savant-style card in React

- **Type:** feature
- **Priority:** P1
- **Estimate:** 2 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-037
- **Uses contract:** HACK-038
- **Paths:** web/src/features/leaderboard/, web/src/features/pitcher/
- **Freeze-Allowed:** no
- **Acceptance:** sortable/filterable leaderboard (neutral vs CDMX flavours labelled), pitcher page with arsenal table, movement plot with CDMX arrows and Stuff+ at each of the 20 parks; export card as PNG.
- **Verify:** `npm --prefix web test -- --run src/features/leaderboard src/features/pitcher`
- **Next step:** table from `leaderboard.json`.

## HACK-048 · Staff Diablos, prospect profiler (in-browser) and design lab pages

- **Type:** feature
- **Priority:** P1
- **Estimate:** 2 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-037
- **Uses contract:** HACK-038, HACK-040
- **Paths:** web/src/features/staff/, web/src/features/prospecto/, web/src/features/laboratorio/
- **Freeze-Allowed:** no
- **Acceptance:** staff page per franchise (5 and 11 never pooled, "identificación inferida"); prospect CSV upload scored in the browser with the TS model (file never leaves the device); design-lab tweaks table.
- **Verify:** `npm --prefix web test -- --run src/features/staff src/features/prospecto src/features/laboratorio`
- **Next step:** reuse `stuffplus/prospect.py` column mapping in TS.

## HACK-049 · Methodology page: validation, calibration, physics and the paper

- **Type:** feature
- **Priority:** P1
- **Estimate:** 90 min
- **Rubric / Spec:** C1 C2 C4
- **Depends on:** HACK-037
- **Uses contract:** HACK-038
- **Paths:** web/src/features/metodologia/
- **Freeze-Allowed:** no
- **Acceptance:** validation table vs the null (pitcher/season/park/20 parks), altitude-bias chart, calibration curve, leakage audit, links to the PDF and the repo; every number from `validation.json`.
- **Verify:** `npm --prefix web test -- --run src/features/metodologia`
- **Next step:** chart from `validation.json`.

## HACK-050 · Web export with real data + static deploy bundle + leak check on web/dist

- **Type:** integration
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** C4
- **Depends on:** HACK-038, HACK-040, HACK-024
- **Uses contract:** HACK-041
- **Paths:** web/public/data/real/, analysis/export_web/, deploy/web/, scripts/check_web_dist.py, tests/test_check_web_dist.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `python -m analysis.export_web.run` writes every contract file from `reports/` + bundle; the app reads `real/` when present, else `mock/` (badge says which).
  - `check_web_dist.py` runs the raw-data rules on `web/dist/`; total ≤ 25 MB; documented static deploy (Vercel/Netlify/GitHub Pages) in `deploy/web/README.md`; the human (joahan) publishes.
- **Verify:** `python -m pytest -q tests/test_check_web_dist.py`
- **Next step:** call `stuffplus.export_web.export(real=True)`.

## HACK-051 · End-to-end tests, performance and accessibility pass

- **Type:** integration
- **Priority:** P1
- **Estimate:** 90 min
- **Rubric / Spec:** C4
- **Depends on:** HACK-045, HACK-043
- **Paths:** web/e2e/
- **Freeze-Allowed:** yes
- **Acceptance:** Playwright (reduced motion) walks landing → simulator (throw a pitch, switch batter, change park) → altitud → leaderboard → pitcher; screenshots for the deck; no console errors; mobile viewport passes.
- **Verify:** `npm --prefix web run build && npx --prefix web playwright test`
- **Next step:** `web/e2e/flow.spec.ts`.

## HACK-052 · Stuff+ v2 target: count-neutral stuff value composed with the count baseline

- **Type:** feature
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C1 · PitchingBot primer (zero-mean per count); Shape+ v2 (count/location-removed target)
- **Depends on:** None
- **Paths:** stuffplus/models/stuff_v2.py, analysis/stuff_v2/, reports/stuff_v2/, tests/test_stuff_v2.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Stuff v2 predicts the stuff effect as a residual from the count expectation (xRV − mean xRV of the count, PitchingBot normalisation); Stuff+ is scaled from it; the per-pitch evaluation prediction = count baseline + stuff effect, so the rubric's null is a nested model. Report it as **incremental value of stuff over the count null**, never as "Stuff+ beats the null".
  - Before/after vs production Stuff+ on pitcher k-fold, season and park holdouts: per-pitch skill vs the null with CI, first-50/200 → rest r, split-half, year-to-year, calibration slope, league ΔStuff+ CDMX. Adoption rule written before running (as in HACK-028).
- **Verify:** `python -m pytest -q tests/test_stuff_v2.py`
- **Next step:** subclass `StuffModel` with a residual target; reuse `analysis/tuning/evaluate.py` patterns.

## HACK-053 · Probability calibration of the outcome models (temperature + isotonic, out of fold)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 2 h
- **Rubric / Spec:** C1 · Niculescu-Mizil & Caruana 2005; Guo et al. 2017
- **Depends on:** None
- **Paths:** stuffplus/calibration.py, analysis/calibration/, reports/calibration/, tests/test_calibration.py
- **Freeze-Allowed:** no
- **Acceptance:** temperature scaling and one-vs-rest isotonic fitted on OOF predictions of the Stuff+/Location+/Pitching+ outcome models (nested: never on the scored fold); multiclass ECE, log-loss and xRV calibration slope before/after; pitcher-level r must not drop; wrapper usable by any model (`Calibrated(model)`).
- **Verify:** `python -m pytest -q tests/test_calibration.py`
- **Next step:** fit temperature on OOF logits from `analysis/stuff_model/run.py`.

## HACK-054 · Leakage audit and relative features (VAA net of location, by-batter-hand primary-fastball diffs)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 2 h
- **Rubric / Spec:** C1 C2 · Driveline "Revisiting Stuff+" 2024; Shape+ v2
- **Depends on:** None
- **Paths:** stuffplus/features/relative.py, analysis/leak_audit/, reports/leak_audit/, tests/test_relative.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Audit table: whiff AUC and xRV skill with raw VAA/HAA vs location-netted VAA/HAA vs none (pitcher-grouped OOF) — quantifies how much a raw-VAA model "wins" by seeing location (the leak public competitors show).
  - `relative.py`: VAA/HAA residual on plate location + release height by family; primary-fastball diffs by batter hand; ablation rows for Stuff v2.
- **Verify:** `python -m pytest -q tests/test_relative.py`
- **Next step:** residualize `VertApprAngle` on `PlateLocHeight`, `RelHeight`, `Extension` by family.

## HACK-055 · Uncertainty: weighted conformal intervals and importance-weighted park holdout

- **Type:** feature
- **Priority:** P1
- **Estimate:** 3 h
- **Rubric / Spec:** C2 C3 · Tibshirani et al. 2019 (conformal under covariate shift); Angelopoulos & Bates 2021; Shimodaira 2000
- **Depends on:** None
- **Paths:** stuffplus/uncertainty.py, analysis/uncertainty/, reports/uncertainty/, tests/test_uncertainty.py
- **Freeze-Allowed:** no
- **Acceptance:** density-ratio classifier (train vs Extreme) with overlap diagnostics; importance-weighted park-holdout skill next to the unweighted one; split-conformal (weighted) intervals for pitcher-season ΔStuff+ CDMX and Stuff+ with empirical coverage on held-out pitchers (target 90 %).
- **Verify:** `python -m pytest -q tests/test_uncertainty.py`
- **Next step:** logistic density-ratio on release physics + ρ.

## HACK-056 · One-command pipeline: retrain, rescore, regenerate every report; roster drop-in for named finals data

- **Type:** integration
- **Priority:** P0
- **Estimate:** 2 h
- **Rubric / Spec:** C2 C4
- **Depends on:** None
- **Paths:** analysis/pipeline/, Makefile, stuffplus/roster.py, tests/test_pipeline.py, tests/test_roster.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `python -m analysis.pipeline.run [--from STEP]` runs in dependency order (targets → physics → models → validation → altitude → scores → leaderboards → staff → business → memo → web export), logs each step's time, stops on the first failure; `--dry-run` prints the order.
  - Roster drop-in: an optional `pitcher_id,name,team,role` CSV (git-ignored) maps ids to names in leaderboards, staff and web without refitting (finals data may be named).
- **Verify:** `python -m pytest -q tests/test_pipeline.py tests/test_roster.py`
- **Next step:** list the existing `analysis/*/run.py` entry points and their inputs.

## HACK-057 · Validation v2 and model adoption (applies 052/053/054 if they pass their rules)

- **Type:** integration
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C1 C2 C3
- **Depends on:** HACK-052, HACK-053, HACK-054, HACK-056, HACK-024
- **Uses contract:** HACK-055, HACK-041
- **Paths:** stuffplus/models/stuff.py, stuffplus/models/location.py, stuffplus/models/pitching.py, stuffplus/validation/, reports/validation/, reports/stuff_model/, reports/location_model/, reports/pitching_model/, reports/altitude_delta/, reports/leaderboards/, reports/staff_audit/, reports/business_value/, deploy/bundle/
- **Freeze-Allowed:** yes
- **Acceptance:** adopted upgrades wired into the production models; full pipeline re-run; `reports/validation/summary.md` v2 with a "v1 → v2" column; every downstream report regenerated by HACK-056 in one run; contract message to the paper, deck and web tasks before pushing. Integrated by the model freeze (2026-10-20 12:00); if an upgrade misses it, it ships as a documented ablation, not in production.
- **Verify:** `python -m pytest -q tests/test_validation.py tests/test_model_stuff.py`
- **Next step:** read the adoption verdicts in reports/stuff_v2, reports/calibration, reports/leak_audit.

## HACK-058 · Technical document v2 (physics v2, Stuff+ v2, calibration, uncertainty, leakage audit)

- **Type:** docs
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C1 C2 C3 C4
- **Depends on:** HACK-057, HACK-041
- **Uses contract:** HACK-055, HACK-054
- **Paths:** docs/technical/
- **Freeze-Allowed:** yes
- **Acceptance:** still 6–10 pages; new sections replace weaker ones; references for every method (Nathan, Kagan & Nathan, Tibshirani, Guo, PitchingBot, Driveline, BP StuffPro); `docs/technical/check_numbers.py` checks that every number next to a cited `reports/` file appears in that file (rounding-aware) and exits 1 on a miss. No head-to-head numbers against competitors (their target and null differ).
- **Verify:** `python docs/technical/check_numbers.py && test -s docs/technical/stuffplus2240.pdf`
- **Next step:** diff `reports/validation/summary.md` v1 vs v2.

## HACK-059 · Deck v2 and one-pager v2 with the React product and the 3D simulator

- **Type:** docs
- **Priority:** P0
- **Estimate:** 2 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-057
- **Uses contract:** HACK-051
- **Paths:** demo/deck/, demo/one-pager/
- **Freeze-Allowed:** yes
- **Acceptance:** the four strongest numbers (league −10.3 Stuff+ CDMX, 50 pitches r 0.230 vs 0.051, bias −82 %, +10 Stuff+ = 1.26 wins) updated to v2; staff "identificación inferida"; simulator screenshots from HACK-051; builds on Windows (no macOS font paths).
- **Verify:** `test -s demo/deck/deck.pdf && test -s demo/one-pager/one-pager.pdf`
- **Next step:** replace `/System/Library/Fonts` with a bundled font.
## HACK-060 · Spike: 3D simulator prototype (low-poly stadium, batter switch, same pitch in two airs)

- **Type:** spike
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C4
- **Depends on:** None
- **Uses contract:** HACK-041, HACK-039
- **Paths:** web/spikes/simulator/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Standalone page `web/spikes/simulator/index.html` (served by the existing Vite setup at `/spikes/simulator/`), react-three-fiber, following `web/DESIGN.md`: low-poly flat-shaded field, mound, plate, strike zone, stadium lights; batter figure that switches L/R with a short animation; cameras Catcher / Pitcher / Lateral / Transmisión.
  - Throw: the same release flown at sea level (grey ghost, dashed trail) and in Harp Helú air (red), RK4 port of `stuffplus/physics/flight.py` with the measured Magnus elasticity; plate dots and inches of movement lost.
  - 60 fps target, reduced motion = no camera moves and instant flights; WebGL missing → message. Screenshot in the PR. HACK-044/045 adopt the code.
- **Verify:** `npm --prefix web run build && test -s web/spikes/simulator/index.html`
- **Next step:** port `fly()` to `web/spikes/simulator/flight.ts`.

## HACK-061 · Time-based tunneling (decision point 150 ms before the plate) as a Stuff+ feature

- **Type:** feature
- **Priority:** P1
- **Estimate:** 2 h
- **Rubric / Spec:** C3 C1 · Baseball Prospectus "Pitch Tunnels" (decision point by time, not distance)
- **Depends on:** None
- **Paths:** stuffplus/features/tunnel.py, analysis/tunnel/, reports/tunnel/, tests/test_tunnel.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - From each pitch's 9-parameter fit: position 150 ms before reaching the plate (time-based, so thin air with a faster ball moves the decision point); separation vs the pitcher-season primary fastball at that point and at the plate; time-based tunnel ratio; physical traits only.
  - Before/after on pitcher-grouped OOF with a rule fixed before running (per-pitch skill CI above the base, pitcher-level r and split-half not lower than base − 0.005); altitude check: how much the tunnel ratio changes Extreme vs No within pitcher.
  - Adoption into production goes through HACK-057 (model freeze 2026-10-20 12:00).
- **Verify:** `python -m pytest -q tests/test_tunnel.py`
- **Next step:** reuse `stuffplus.features.arsenal.trajectory_at` with t instead of x.

## HACK-062 · Contrato web acepta arboles packed, Plus sign/stats y reference de location (follow-up of HACK-038)

- **Type:** follow-up
- **Priority:** P1
- **Depends on:** HACK-038
- **Follow-up of:** HACK-038
- **Paths:** docs/CONTRACT-WEB.md, web/src/contract/, web/public/data/mock/, stuffplus/export_web.py, tests/test_export_web.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Contrato web acepta arboles packed, Plus sign/stats y reference de location
- **Verify:** `python -m pytest -q tests/test_export_web.py && npm --prefix web test -- --run src/contract`

## HACK-063 · CI kit syntax check: bash -n only on shell scripts (uak-mcp is Python) (follow-up of HACK-001)

- **Type:** follow-up
- **Priority:** P1
- **Depends on:** HACK-001
- **Follow-up of:** HACK-001
- **Paths:** requirements.txt, pyproject.toml, stuffplus/__init__.py, stuffplus/io.py, stuffplus/config.py, tests/__init__.py, tests/conftest.py, tests/fixtures/, tests/test_io.py, README.md, Makefile
- **Freeze-Allowed:** no
- **Acceptance:**
  - CI kit syntax check: bash -n only on shell scripts (uak-mcp is Python)
- **Verify:** `python -m pytest -q tests/test_io.py`
