# Location+ (HACK-011)

`python analysis/location_model/run.py` (run after `analysis/stuff_model/run.py`; ~4 min) validates Location+, writes
`reports/location_model/` and replaces the bundle's location model.

**Definition.** Inputs: plate location (arm-side mirrored), count, batter side, the altitude-invariant
`pitch_family` (`features.identity`) and air density; no pitch physics. Trackman's AutoPitchType (which relabels
pitches with air density) is used ONLY as a fallback label for the 0.7 % of pitches the identity mixture leaves
unassigned (`add_pitch_family`, `reliability.csv: pitch_family_assigned_share = 0.993`).
xRV_loc = Σ P(outcome | location, count, …) · LMB value of the outcome (+ contact value in play).
Location value = xRV_loc − league mean for the same count and pitch family, so the count is neither blamed nor
credited. Location+ = 100 + 10·z(−location value).

## Results (real data, 2026-10-13, OOF by pitcher)

| Test | Result | File |
|---|---|---|
| Per-pitch RMSE skill vs mean xRV by count (rubric's null) | **+2.78 % [2.70, 2.87]** | `metrics.csv` |
| 5-outcome log-loss | 1.041 vs 1.451 count baseline vs 1.516 prior | `component_metrics.csv` |
| Split-half reliability of pitcher-season Location+ | 0.58 (observed rv_x: 0.25) | `reliability.csv` |

Caveat (exploratory, transductive parts): the model and its OOF predictions are pitcher-grouped, but three inputs
are estimated once on all the data before the folds: the pitch identity (`assign_pitch_id`, physical traits only,
no outcomes), the per-game air density, and the LMB run values behind `rv_x` (run expectancy, linear weights,
expected batted-ball value). None uses a test pitcher's outcomes in his own features, but the scale of the targets
is shared; treat the skill as a slightly optimistic estimate.

## Altitude × location (`altitude_by_zone.csv`, model-based, + = worse for the pitcher in Harp Helú air)
- In and around the zone (zones 1–9 and shadow) every region costs more in CDMX air for all three families. The
  chase region barely moves (four-seam −0.0007, slider +0.003, changeup +0.002 runs/pitch).
- **The middle row costs most**: four-seam zone 4 +0.027 and zone 5 +0.025; slider zone 4 +0.025 and zone 3 +0.025;
  for changeups the largest is low arm side (zone 7, +0.027) then zone 4 (+0.024).
- **Low four-seamers lose more than high ones** (zones 7–8 +0.018/+0.021 vs zones 1–3 +0.012/+0.014). With
  AutoPitchType (first version) this gap looked twice as large: part of it was Trackman relabelling.
- The glove-side low corner (zone 9) holds up best for every family (+0.006 to +0.010).
Caveat: ρ is game-level, so this mixes air with park; HACK-015 checks it within pitcher.

Heatmaps: `heatmap_sea_level.png`, `heatmap_harp_helu.png` (blue = better for the pitcher).
