# Stuff+ v1 (HACK-010): what it shows and how to read it

`python analysis/stuff_model/run.py` (~3 min) trains on the real data, writes `reports/stuff_model/*.csv` and the
dashboard bundle (`artifacts/bundle`, version `v1`). All validation is out of fold with pitcher-grouped folds.

## Model
Physics at release (velo, spin, arm-side axis, IVB/HB in the pitch's air, release point, extension, arm angle),
three differences vs the pitcher's primary fastball, handedness, pitch type and air density ρ →
1. P(ball / called strike / whiff / foul / in play) — LightGBM multiclass;
2. contact value given in play (`rv_x`, batted balls valued by EV/LA/altitude);
3. xRV = Σ P(outcome) · LMB value of the outcome (in play: model 2). Stuff+ = 100 + 10·z(−xRV), sea-level reference.

## Results (real data, 2026-10-13)

| Test | Stuff+ v1 | Comparison | File |
|---|---|---|---|
| First 50 pitches → rest-of-season run value | **r = 0.230** | the pitcher's own results over those 50 pitches: 0.051 | `predictiveness.csv` |
| First 200 pitches → rest of season | **r = 0.270** | own results: 0.110 | `predictiveness.csv` |
| Split-half reliability (odd vs even games) | **0.80** | observed run value: 0.18 | `reliability.csv` |
| Per-pitch RMSE skill vs mean xRV by pitch type | +0.07 % [0.05, 0.09] | | `metrics.csv` |
| Per-pitch RMSE skill vs mean xRV by count (rubric's null) | −0.03 % [−0.06, −0.01] | pure Stuff+ excludes count by design; Pitching+ (HACK-012) adds it | `metrics.csv` |
| Serving model fidelity (distilled composite) | R² 0.92 | | bundle manifest |

How to say it: per-pitch run value is mostly noise, so per-pitch RMSE gains are always tiny for any Stuff+.
What matters for a front office is that **50 bullpen-quality pitches tell more about a pitcher than 400 pitches
of results**: Stuff+ stabilizes ~4× faster than results.

## Altitude by pitch type (environment − neutral, `stuff_by_pitch_type.csv`)
Every type loses in Harp Helú air (≈ −9 points on average: thin air costs pitchers through less break and more
damage on contact). Relative to that average, **cutters (−5.0) and sliders (−6.7) hold up best; changeups
(−14.9), splitters (−10.7) and sinkers (−9.6) lose most**. This contradicts H2 (changeups gaining): the changeup's
fade is Magnus-driven. Caveat for HACK-015: ρ is a game-level drag measure, so part of this can be park effects
that travel with altitude (dimensions, hitters); HACK-015 triangulates with within-pitcher observed splits.

## Known limits / next
- Movement translation between airs is Magnus ∝ ρ until HACK-004's fitted (per-movement) translation lands.
- Arsenal features are three fastball diffs; HACK-006 adds tunneling and usage.
- Spin efficiency waits for HACK-004's fix (it currently confounds air with spin).
