# Location+ (HACK-011)

`python analysis/location_model/run.py` (run after `analysis/stuff_model/run.py`; ~4 min) validates Location+, writes
`reports/location_model/` and replaces the bundle's location model.

**Definition.** Inputs: plate location (arm-side mirrored), count, batter side, the altitude-invariant
`pitch_family` (`features.identity`, 99.3 % of pitches assigned; Trackman's AutoPitchType relabels pitches with
air density and is never used) and air density; no pitch physics. xRV_loc = Σ P(outcome | location, count, …) ·
LMB value of the outcome (+ contact value in play). Location value = xRV_loc − league mean for the same count and
pitch family, so the count is neither blamed nor credited. Location+ = 100 + 10·z(−location value).

## Results (real data, 2026-10-13, OOF by pitcher)

| Test | Result | File |
|---|---|---|
| Per-pitch RMSE skill vs mean xRV by count (rubric's null) | **+2.78 % [2.70, 2.87]** | `metrics.csv` |
| 5-outcome log-loss | 1.041 vs 1.451 count baseline vs 1.516 prior | `component_metrics.csv` |
| Split-half reliability of pitcher-season Location+ | 0.58 (observed rv_x: 0.25) | `reliability.csv` |

## Altitude × location (`altitude_by_zone.csv`, model-based, + = worse for the pitcher in Harp Helú air)
- Every zone costs more in CDMX air; **the heart of the zone costs most** (zone 5: four-seam +0.025, slider +0.019
  runs/pitch).
- **Low four-seamers lose more than high ones** (zones 7–8 +0.018/+0.021 vs zones 1–3 +0.012/+0.014). With
  AutoPitchType (first version) this gap looked twice as large: part of it was Trackman relabelling, not location.
- Changeups lose everywhere; low glove side (zone 9) holds up best (+0.006).
Caveat: ρ is game-level, so this mixes air with park; HACK-015 checks it within pitcher.

Heatmaps: `heatmap_sea_level.png`, `heatmap_harp_helu.png` (blue = better for the pitcher).
