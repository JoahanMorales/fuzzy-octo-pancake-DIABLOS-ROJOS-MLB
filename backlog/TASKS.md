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

## HACK-064 · data.ts: real/ only when manifest.json parses as JSON (static hosts answer index.html with 200) (follow-up of HACK-047)

- **Type:** follow-up
- **Priority:** P1
- **Depends on:** HACK-047
- **Follow-up of:** HACK-047
- **Paths:** web/src/features/leaderboard/, web/src/features/pitcher/
- **Freeze-Allowed:** no
- **Acceptance:**
  - data.ts: real/ only when manifest.json parses as JSON (static hosts answer index.html with 200)
- **Verify:** `npm --prefix web test -- --run src/features/leaderboard src/features/pitcher`

## HACK-065 · export real/design_lab.json from reports/design_lab (request #400) (follow-up of HACK-050)

- **Type:** follow-up
- **Priority:** P1
- **Depends on:** HACK-050
- **Follow-up of:** HACK-050
- **Paths:** web/public/data/real/, analysis/export_web/, deploy/web/, scripts/check_web_dist.py, tests/test_check_web_dist.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - export real/design_lab.json from reports/design_lab (request #400)
- **Verify:** `python -m pytest -q tests/test_check_web_dist.py`
## HACK-066 · Browser Stuff+ v2: export and evaluate the production model (count recentring, count-marginalized value, temperature)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C1 C4
- **Depends on:** HACK-057
- **Uses contract:** HACK-040, HACK-062
- **Paths:** stuffplus/export_trees.py, tests/test_export_trees.py, web/src/model/, web/src/contract/, web/public/data/models/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `export_trees.py` exports the production Stuff+ (`stuffplus.models.stuff.fit_production_stuff`): trees, count value table, count offsets, count means, family count weights, temperature T and the Plus scaler fitted on the count-neutral value; Location+ with its temperature.
  - `predict.ts` reproduces `CountNeutral.predict_xrv` and Stuff+ within 1e-6 on synthetic goldens (every count, every family, NaNs); the contract types accept the v2 fields and keep v1 files parsing (absorbs HACK-062: packed trees, Plus sign/stats, location reference).
  - Total models ≤ 15 MB; contract message to HACK-045, HACK-048 and HACK-069 before pushing.
- **Verify:** `python -m pytest -q tests/test_export_trees.py && npm --prefix web test -- --run src/model src/contract`
- **Next step:** read `CountNeutral` and `StuffV2Model.stuff_value` in stuffplus/models/.

## HACK-067 · Cuerpo técnico page: home vs road pitch mix per Diablos pitcher, bullpen PDF, and the wave-3 routes

- **Type:** feature
- **Priority:** P1
- **Estimate:** 2.5 h
- **Rubric / Spec:** C4
- **Depends on:** None
- **Uses contract:** HACK-050, HACK-057
- **Paths:** web/src/routes.tsx, web/src/features/cuerpo-tecnico/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `routes.tsx` adds `/cuerpo-tecnico`, `/reclutamiento`, `/presentacion` and `/fisica` (placeholders until each feature exists); nothing else in the file changes.
  - Per Diablos staff pitcher (franchises 5 and 11 apart, "identificación inferida"): arsenal at sea level vs Harp Helú, the pitch that loses most, a suggested home mix (usage moved from the pitches that lose most in CDMX air to the ones that resist, capped and labelled as a model suggestion, not a measured effect) and one pitch to develop from reports/design_lab.
  - "Imprimir reporte" produces a one-page bullpen PDF per pitcher (print stylesheet); numbers read from data/real or data/mock, never typed.
- **Verify:** `npm --prefix web test -- --run src/features/cuerpo-tecnico src/shell`
- **Next step:** reuse the loader in web/src/features/staff/data.tsx.

## HACK-068 · Reclutamiento page: league pitchers whose arsenal survives CDMX air

- **Type:** feature
- **Priority:** P1
- **Estimate:** 2 h
- **Rubric / Spec:** C4 C3
- **Depends on:** None
- **Uses contract:** HACK-050, HACK-067
- **Paths:** web/src/features/reclutamiento/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Ranking of pitcher-seasons (not on the Diablos) by Stuff+ in CDMX air with a small CDMX loss, filters (season, hand, minimum pitches, pitch shapes in the arsenal), both Stuff+ flavours labelled.
  - Shortlist: pick up to 10 and export CSV (aggregates only) and a PNG card; each row links to /pitcher/:id.
  - Short text conclusion beside the table; empty and loading states.
- **Verify:** `npm --prefix web test -- --run src/features/reclutamiento`
- **Next step:** filters from web/src/features/leaderboard/logic.ts.

## HACK-069 · Uncertainty visible: conformal intervals on Stuff+ in leaderboard and pitcher page

- **Type:** feature
- **Priority:** P1
- **Estimate:** 2 h
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-064, HACK-065
- **Uses contract:** HACK-055, HACK-066
- **Paths:** analysis/export_web/, web/public/data/real/, web/src/features/leaderboard/, web/src/features/pitcher/, tests/test_check_web_dist.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `real/uncertainty.json` from reports/uncertainty (aggregates): interval half-width by number of pitches and by air (weighted conformal), with its coverage.
  - Leaderboard and pitcher page show Stuff+ as value ± half-width for the row's sample size, with a one-line tooltip on what it means; absent file = no band, no error.
  - Tests: interval lookup by pitches, missing-file state.
- **Verify:** `python -m pytest -q tests/test_check_web_dist.py && npm --prefix web test -- --run src/features/leaderboard src/features/pitcher`
- **Next step:** read reports/uncertainty/README.md and its CSVs.

## HACK-070 · Visual QA of every page (design-critic, desktop and phone)

- **Type:** polish
- **Priority:** P1
- **Estimate:** 2 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-045, HACK-046, HACK-049, HACK-067, HACK-068, HACK-069
- **Uses contract:** HACK-039
- **Paths:** web/src/features/, web/src/shell/, web/src/styles/base.css, web/e2e/qa/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Screenshots of all pages at 1440 and 390 px (reduced motion) reviewed with design-critic against web/DESIGN.md; every finding fixed or listed with a reason.
  - No horizontal overflow at 390 px, visible focus rings, Spanish copy without em-dashes, one accent (red = Harp Helú air).
  - Screenshots committed under web/e2e/qa/.
- **Verify:** `npm --prefix web run build && npm --prefix web test -- --run`
- **Next step:** one Playwright script that walks every route.

## HACK-071 · Presentation mode: guided 5-minute tour for the jury interview and the video

- **Type:** feature
- **Priority:** P1
- **Estimate:** 2 h
- **Rubric / Spec:** C4
- **Depends on:** None
- **Uses contract:** HACK-067
- **Paths:** web/src/features/presentacion/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `/presentacion`: steps landing → simulador → altitud → staff → reclutamiento → metodología, each with a one-line speaker note and the number to say (read from the contract JSON); arrow keys and space advance, Esc exits; reduced motion respected.
  - A printable script (speaker notes) and a 5-minute timer.
- **Verify:** `npm --prefix web test -- --run src/features/presentacion`
- **Next step:** reuse demo/script.md from HACK-025 for the notes.

## HACK-072 · Physics explainer: why the fastball loses ride in CDMX air (interactive)

- **Type:** feature
- **Priority:** P2
- **Estimate:** 2 h
- **Rubric / Spec:** C3
- **Depends on:** None
- **Uses contract:** HACK-041, HACK-042
- **Paths:** web/src/features/fisica/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `/fisica`: a density slider from sea level to Harp Helú that recomputes drag and Magnus with web/src/physics (flyPitch) and shows the measured Magnus elasticity per family next to textbook physics (elasticity 1); numbers from physics.json.
  - Side view and catcher view of the two flights; reduced motion = static final frame; text summary for screen readers.
- **Verify:** `npm --prefix web test -- --run src/features/fisica`
- **Next step:** flyPitch from web/src/physics/flight.ts.

## HACK-073 · CI: the kit syntax check runs bash -n only on shell scripts

- **Type:** fix
- **Priority:** P1
- **Estimate:** 15 min
- **Rubric / Spec:** -
- **Depends on:** None
- **Paths:** .github/workflows/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - The "Kit syntax" step checks a file with `bash -n` only when its shebang names bash or sh, so `.uak/bin/uak-mcp` (Python) no longer fails every PR; the other gates stay as they are.
  - A PR run of the workflow is green on that step (link in the evidence). Replaces HACK-063, whose Paths include files HACK-001 owns.
- **Verify:** `for f in .uak/bin/* .uak/bin/lib/*.sh; do [ -f "$f" ] || continue; if head -n 1 "$f" | grep -qE '^#!.*(bash|/sh|[[:space:]]sh)([[:space:]]|$)'; then bash -n "$f" || exit; fi; done`
- **Next step:** edit the Kit syntax step in .github/workflows/uak.yml.

## HACK-074 · Recalibrate the Stuff+ uncertainty bands on the v2 production scores (HACK-057/066) (follow-up of HACK-069)

- **Type:** follow-up
- **Priority:** P1
- **Depends on:** HACK-069
- **Follow-up of:** HACK-069
- **Paths:** analysis/export_web/, web/public/data/real/, web/src/features/leaderboard/, web/src/features/pitcher/, tests/test_check_web_dist.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Recalibrate the Stuff+ uncertainty bands on the v2 production scores (HACK-057/066)
- **Verify:** `python -m pytest -q tests/test_check_web_dist.py && npm --prefix web test -- --run src/features/leaderboard src/features/pitcher`

## HACK-075 · Regenerate web/public/data/real with production Stuff+ v2 (real export still has v1 deltas) (follow-up of HACK-057)

- **Type:** follow-up
- **Priority:** P1
- **Depends on:** HACK-057
- **Follow-up of:** HACK-057
- **Paths:** stuffplus/models/stuff.py, stuffplus/models/location.py, stuffplus/models/pitching.py, stuffplus/validation/, reports/validation/, reports/stuff_model/, reports/location_model/, reports/pitching_model/, reports/altitude_delta/, reports/leaderboards/, reports/staff_audit/, reports/business_value/, deploy/bundle/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Regenerate web/public/data/real with production Stuff+ v2 (real export still has v1 deltas)
- **Verify:** `python -m pytest -q tests/test_validation.py tests/test_model_stuff.py`
## HACK-076 · Pitcher altitude sensitivity on production Stuff+ v2 (HACK-018 still fits the v1 StuffModel)

- **Type:** follow-up
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** C1 C2
- **Depends on:** None
- **Uses contract:** HACK-057
- **Paths:** analysis/pitcher_sensitivity/, reports/pitcher_sensitivity/, stuffplus/sensitivity.py, tests/test_sensitivity.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `analysis/pitcher_sensitivity/run.py` scores with `fit_production_stuff` (Stuff+ v2 + temperature, `physics_translator`) instead of `StuffModel`; `metadata.json` says `model_version: stuff_v2`.
  - `reports/pitcher_sensitivity/` regenerated; its `league_delta` agrees with the production league ΔStuff+ (−13.0, `reports/altitude_delta/delta_by_shape.csv`) within ±1.5 or the README explains the weighting difference with numbers.
  - `top15.csv`/`bottom15.csv` and the altitude-proof index regenerated; no per-pitch rows committed.
- **Verify:** `python -m pytest -q tests/test_sensitivity.py`
- **Next step:** swap `StuffModel(...).fit(d)` in run.py:29 for `fit_production_stuff(d, translate=physics_translator(shape))`.

## HACK-077 · Ideal profile (recruiting thresholds) on production Stuff+ v2 (HACK-017 still fits the v1 StuffModel)

- **Type:** follow-up
- **Priority:** P1
- **Estimate:** 90 min
- **Rubric / Spec:** C2 C3
- **Depends on:** None
- **Uses contract:** HACK-057
- **Paths:** stuffplus/profile.py, analysis/ideal_profile/, reports/ideal_profile/, tests/test_profile.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `analysis/ideal_profile/run.py` uses `fit_production_stuff`; `delta_by_trait.csv`, `rho_sensitivity.csv`, `best_fastballs.csv`, `best_secondaries.csv` and `profile.md` regenerated from v2.
  - The recruiting checklist (IVB range sea vs Harp Helú, extension and VAA quintiles, velocity) is restated from the new CSVs; any rule that flips sign or loses robustness is said so in `profile.md`.
- **Verify:** `python -m pytest -q tests/test_profile.py`
- **Next step:** swap `StuffModel(...).fit(d)` in run.py:50 for `fit_production_stuff`.

## HACK-078 · Business value on the Stuff+ v2 scale (HACK-035 converts with the v1 bundle scaler)

- **Type:** follow-up
- **Priority:** P1
- **Estimate:** 90 min
- **Rubric / Spec:** C3 C4
- **Depends on:** None
- **Uses contract:** HACK-057
- **Paths:** stuffplus/value.py, analysis/business_value/, reports/business_value/, tests/test_value.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Runs per Stuff+ point estimated from out-of-fold **Stuff+ v2** predictions (production model and its PlusScaler), not the v1 bundle; `stuff_scale_calibration.csv` records `model_version: stuff_v2`.
  - `runs_per_point_direct.csv`, `gm_example.csv`, `pitcher_spread_example.csv`, `conversion_table.csv` and `summary.md` regenerated; Pythagorean runs-per-win unchanged.
- **Verify:** `python -m pytest -q tests/test_value.py`
- **Next step:** replace `stuff_run.StuffModel().oof` and `bundle.scalers["stuff"]` in run.py:85-92 with the production v2 OOF and scaler.

## HACK-079 · Pitching+ in the browser: export models/pitching.json and score it in the simulator

- **Type:** feature
- **Priority:** P1
- **Estimate:** 3 h
- **Rubric / Spec:** C3 C4
- **Depends on:** HACK-045
- **Uses contract:** HACK-066
- **Paths:** stuffplus/export_trees.py, web/public/data/models/pitching.json, web/src/model/predict.ts, web/src/model/predict.test.ts, web/src/features/simulador/panel/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `python -m stuffplus.export_trees` writes `web/public/data/models/pitching.json` (component trees, combination weights, neutral batter, Plus stats), within the 25 MB data budget.
  - `predict.ts` scores Pitching+ with Python parity on a synthetic golden (same rule as HACK-040/066).
  - The simulator panel shows real Pitching+ in both airs; the 'sin modelo' fallback stays only when the file is missing.
- **Verify:** `python -m pytest -q tests/test_export_trees.py && npm --prefix web test -- --run src/model src/features/simulador`
- **Next step:** mirror `export_composite` for the Pitching+ components + weights.

## HACK-080 · SHAP explanations on production Stuff+ v2 (HACK-019 explains the v1 model)

- **Type:** follow-up
- **Priority:** P2
- **Estimate:** 60 min
- **Rubric / Spec:** C2 C3
- **Depends on:** None
- **Uses contract:** HACK-057
- **Paths:** stuffplus/explain.py, reports/explain/, tests/test_explain.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Global and per-pitch TreeSHAP regenerated on the v2 count-neutral value (or its count-averaged components), with the Spanish coach text; the README states what the SHAP target is.
- **Verify:** `python -m pytest -q tests/test_explain.py`
- **Next step:** point `stuffplus/explain.py` at the production classifier and the count-neutral value.

## HACK-081 · README for the React product and Stuff+ v2

- **Type:** docs
- **Priority:** P1
- **Estimate:** 45 min
- **Rubric / Spec:** C4
- **Depends on:** None
- **Uses contract:** HACK-050
- **Paths:** README.md
- **Freeze-Allowed:** yes
- **Acceptance:**
  - README leads with the React app (`npm --prefix web ci && npm --prefix web run dev`, deploy via `deploy/web/README.md`); Streamlit only as legacy if kept.
  - Headline numbers are v2 and each cites its `reports/` file (league ΔStuff+ −13.0, skill vs null, altitude bias); links to the paper, deck and one-pager v2 resolve.
- **Verify:** `test -s README.md && python docs/technical/check_numbers.py README.md`
- **Next step:** replace the Streamlit run block (README.md:55).

## HACK-082 · Final numbers sync after the v2 migrations (memo, web export, paper, deck, one-pager)

- **Type:** integration
- **Priority:** P0
- **Estimate:** 2 h
- **Rubric / Spec:** C1 C2 C3 C4
- **Depends on:** HACK-076, HACK-077, HACK-078
- **Uses contract:** HACK-058, HACK-059
- **Paths:** reports/recommendations/, reports/staff_audit/, web/public/data/real/, docs/technical/, demo/deck/, demo/one-pager/, demo/qa.md, demo/script.md
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Re-run `reports/recommendations/build_memo.py`, the staff audit and `analysis.export_web.run` on the migrated reports.
  - Paper and deck drop the "escala v1" caveats that no longer apply; `python docs/technical/check_numbers.py` passes; `python demo/deck/build.py && python demo/deck/verify.py` pass; PDFs rebuilt.
  - Every number that changed is listed in the PR with old → new.
- **Verify:** `python docs/technical/check_numbers.py && python demo/deck/verify.py && test -s docs/technical/stuffplus2240.pdf`
- **Next step:** wait for 076–078, then run the three generators in that order.

## HACK-083 · Regenerate reports/ideal_profile with production Stuff+ v2 (077 merged the code; the CSVs are still v1) (follow-up of HACK-077)

- **Type:** follow-up
- **Priority:** P1
- **Depends on:** HACK-077
- **Follow-up of:** HACK-077
- **Paths:** stuffplus/profile.py, analysis/ideal_profile/, reports/ideal_profile/, tests/test_profile.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Regenerate reports/ideal_profile with production Stuff+ v2 (077 merged the code; the CSVs are still v1)
- **Verify:** `python -m pytest -q tests/test_profile.py`
## HACK-084 · Final model audit report (translator calibration, physics vs learned split, leakage, scale)

- **Type:** analysis
- **Priority:** P1
- **Estimate:** 60 min
- **Rubric / Spec:** C1 C2
- **Depends on:** None
- **Uses contract:** HACK-057
- **Paths:** analysis/model_audit/, reports/model_audit/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `python -m analysis.model_audit.run` writes `reports/model_audit/` from the real data and the exported production model (no refit, no per-pitch rows): translator calibration per family (predicted vs observed within-pitcher change, Extreme → No), the league ΔStuff+ split into translated movement vs the model's learned `rho`, and pass/fail checks (export features, disjoint pitcher folds, count neutrality, Stuff+ mean/sd per season).
  - README states the decision rule fixed before running (change the model only for a leak, fold overlap, or a miscalibrated translator in a family with ≥ 5 % of pitches) and the verdict.
- **Verify:** `test -s reports/model_audit/README.md && test -s reports/model_audit/calibration.csv`
- **Next step:** move the scratch audit into analysis/model_audit/run.py with CSV outputs.

## HACK-085 · Paper: physics vs learned split of ΔStuff+ and the cutter/splitter translator limitation

- **Type:** docs
- **Priority:** P1
- **Estimate:** 30 min
- **Rubric / Spec:** C1 C2
- **Depends on:** HACK-082, HACK-084
- **Uses contract:** HACK-058
- **Paths:** docs/technical/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - §6 says how much of the league ΔStuff+ comes from lost movement and how much from the model's learned air effect (contact and carry), citing `reports/model_audit/`.
  - The limitations list the cutter (and splitter) translator miscalibration with its numbers; `python docs/technical/check_numbers.py` passes; PDF rebuilt, still 6–10 pages.
- **Verify:** `python docs/technical/check_numbers.py && test -s docs/technical/stuffplus2240.pdf`
- **Next step:** after 082 and 084 merge, add two sentences to §6 and one limitation.
## HACK-086 · Fix the six High findings of the visual QA (web/e2e/qa/INFORME.md)

- **Type:** follow-up
- **Priority:** P0
- **Estimate:** 3 h
- **Rubric / Spec:** C4
- **Depends on:** HACK-070
- **Uses contract:** HACK-039
- **Paths:** web/src/features/landing/, web/src/features/presentacion/, web/src/features/simulador/, web/src/features/altitud/, web/src/features/laboratorio/, web/src/styles/base.css, web/e2e/qa/
- **Freeze-Allowed:** yes
- **Acceptance:**
  - The six High findings of `web/e2e/qa/INFORME.md` are fixed: inicio 390 chip over the chart legend; presentación 390 fixed bar covering content; simulador 1440 presets below the fold and black band under the scene; altitud 390 tiny dots without axis or legend; laboratorio 390 table overflow; simulador 390 scene crop and cut labels.
  - Screenshots of those pages at 1440 and 390 retaken under `web/e2e/qa/shots/` and INFORME.md marks each finding fixed; no horizontal overflow at 390 on any route.
- **Verify:** `npm --prefix web run build && npm --prefix web test -- --run`
- **Next step:** start with the CSS-only ones (laboratorio table, presentación bar, inicio legend), then altitud, then the simulator layouts.
## HACK-087 · League ΔStuff+ CDMX highlights from the production model (delta_by_shape), not Stuff+ v2 (familia)

- **Type:** follow-up
- **Priority:** P0
- **Estimate:** 1 h
- **Rubric / Spec:** C1, C4
- **Depends on:** HACK-050
- **Uses contract:** HACK-038
- **Paths:** stuffplus/export_web.py, web/public/data/real/validation.json, tests/test_export_highlights.py, tests/test_export_web.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `validation.json` highlights (`league_delta_cdmx`, best and worst shape and delta, `source_model`) come from the production `reports/altitude_delta/delta_by_shape.csv` (count-neutral Stuff+ v2), not from `reports/stuff_v2/altitude.csv` "Stuff+ v2 (familia)"; the league delta rounds to −13.0.
  - `web/public/data/real/validation.json` re-exported (only that file changes under real/); landing and presentación show −13.0 and riding 4S as the most punished shape.
  - New test `tests/test_export_highlights.py` checks the highlights against the CSV and that the committed real/validation.json matches the export. No model is refit.
- **Verify:** `python -m pytest -q --tb=short -x tests/test_export_highlights.py tests/test_export_web.py && npm --prefix web run build && npm --prefix web test -- --run`
- **Next step:** change `_validation` in stuffplus/export_web.py (~line 222), re-export real/ to a scratch dir and copy only validation.json.
