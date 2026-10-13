# Location+ (HACK-011)

`python analysis/location_model/run.py` (run after `analysis/stuff_model/run.py`; ~4 min) validates Location+, writes
`reports/location_model/` and replaces the bundle's location model.

**Definition.** Inputs: plate location (arm-side mirrored), count, batter side, pitch type and air density; no pitch
physics. xRV_loc = Σ P(outcome | location, count, …) · LMB value of the outcome (+ contact value in play).
Location value = xRV_loc − league mean for the same count and pitch type, so the count is neither blamed nor
credited. Location+ = 100 + 10·z(−location value).

## Results (real data, 2026-10-13, OOF by pitcher)

| Test | Result | File |
|---|---|---|
| Per-pitch RMSE skill vs mean xRV by count (rubric's null) | **+2.9 % [2.82, 2.98]** | `metrics.csv` |
| 5-outcome log-loss | 1.028 vs 1.451 count baseline vs 1.516 prior | `component_metrics.csv` |
| Split-half reliability of pitcher-season Location+ | 0.57 (observed rv_x: 0.25) | `reliability.csv` |

## Altitude × location (`altitude_by_zone.csv`, model-based, + = worse for the pitcher in Harp Helú air)
- The heart of the zone (zone 5) costs more in CDMX for every pitch type (four-seam +0.011, slider +0.011,
  changeup +0.037 runs/pitch).
- **Low four-seamers lose more than high ones** (zones 7–8 ≈ +0.018–0.020 vs zones 1–3 ≈ 0): the "don't elevate in
  altitude" intuition is not what the data says; elevated fastballs keep their value, low ones get punished.
- Changeups get worse almost everywhere; only low glove side (zone 9) holds up.
Caveat: ρ is game-level, so this mixes air with park; HACK-015 checks it within pitcher.

Heatmaps: `heatmap_sea_level.png`, `heatmap_harp_helu.png` (blue = better for the pitcher).
