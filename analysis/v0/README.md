# v0 walking skeleton: what it proves and what it does NOT

`python analysis/v0/run.py` trains on the real data and writes the bundle to `artifacts/bundle/` (~3 min).
v0 exists to prove the plumbing: data → targets → LightGBM OOF → bundle → `serving` → `api.predict_pitch`.
**Do not demo or quote v0 Stuff+ numbers.**

## Findings (real data, 2026-10-13)

| Check | Result | Reading |
|---|---|---|
| Stuff+ on observed `rv`, RMSE skill vs count baseline (pitcher 5-fold) | +0.02 % (95 % CI 0.003–0.031 %) | positive but tiny: per-pitch run value is mostly noise (count baseline R² = 0.0009) |
| LightGBM best iterations on `rv` | 25–66 | signature of a noise-dominated target |
| Pitcher-season mean xRV → next-season observed RV (min 300 pitches) | r = 0.169 vs 0.202 for observed RV | not the right test for pure Stuff+ (observed RV includes command); see HACK-014 |
| OOF AUC, physics-only features, `t_whiff` | 0.634 (count × family baseline 0.605) | physics signal is there |
| OOF AUC, physics-only features, `t_groundball` | 0.615 (baseline 0.527) | strong physics signal |
| OOF AUC, physics-only features, `t_chase` | 0.543 (baseline 0.640) | chase depends on count/location, excluded from pure Stuff+ |
| Canonical pitches (sea level) | riding 96 mph FF 125 > flat 91 mph FF 84; sweeper 109 | right direction |
| ΔStuff+ sea → Extreme | riding FF −30, CH −18, SI −3, SL −3 | right direction, magnitude exaggerated: z-scaling a near-constant prediction |

## Next (owners)
1. HACK-030: add `rv_x` = expected run value of batted balls from exit velocity, launch angle and ρ (removes BABIP luck; it is the "xRunValue" the challenge asks for). Train Stuff+ on `rv_x`.
2. HACK-010: component targets (whiff, called strike, contact quality, GB) combined into xRV; regularized settings for noisy targets (`min_data_in_leaf` 1000–2000, `num_leaves` 15–31).
3. HACK-014: predictiveness at matched sample sizes (first N pitches → rest / next season).
4. HACK-004: replace the Magnus ∝ ρ translation and the drag-based ρ with the fitted physics module.
