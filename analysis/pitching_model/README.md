# Pitching+ (HACK-012)

`python analysis/pitching_model/run.py` (~25 min; run after `analysis/stuff_model/run.py` and
`analysis/location_model/run.py`) trains Pitching+, writes `reports/pitching_model/` and replaces the bundle's
`pitching_xrv` model and scaler.

**Inputs:** release physics with the altitude-invariant `pitch_family` (AutoPitchType is not a feature; it is the
fallback label for the 0.7 % of pitches the identity leaves unassigned), arsenal and tunneling vs the primary
fastball (HACK-006), plate location, count, outs, inning, batter side, times through the order, pitch number in the
PA, the previous pitch (velocity and location difference), air density, and **batter quality** (shrunk run value
and whiff rate of that batter-season, computed from training folds only).
**Opponent-neutral:** reported Pitching+ uses league-average batter quality, so a pitcher is not credited for the
hitters he happened to face (`xrv_neutral`).

**Two xRV estimates:** the 5-outcome component composite (as Stuff+), and the HACK-012 combination: 8 outcome
probabilities turned into per-pitch rates and combined with a sign-constrained ridge regression on `rv_x`
(weights fitted on the other folds' OOF predictions, so each fold's combined xRV never saw its own outcomes).

## Results (real data, 2026-10-13; out of fold, folds grouped by pitcher)

| Test | Result | File |
|---|---|---|
| Per-pitch RMSE skill vs mean xRV by count (rubric's null), target `rv_x` | **combined +3.88 % [3.78, 4.00]**; components +3.35 % | `metrics.csv` |
| Same, target raw `rv` | combined +2.17 % [2.11, 2.24] | `metrics.csv` |
| Per-pitch R² on `rv_x` | combined 0.078 vs count baseline 0.002 | `metrics.csv` |
| Outcome probabilities, AUC (count baseline) | called strike 0.974 (0.685) · swing 0.872 (0.649) · chase 0.859 (0.639) · whiff 0.773 (0.530) · weak contact 0.685 (0.544) · hard contact 0.669 (0.560) · groundball 0.665 (0.526) · out in PA 0.626 (0.603) | `target_metrics.csv` |
| Calibration (ECE) | 0.003–0.017 for the 8 targets; hard contact over-predicts in its top decile (0.30 predicted vs 0.23 observed) | `calibration.png` |
| First N pitches → rest-of-season run value (neutral batter) | N=50: 0.238 vs own results 0.051 · N=200: **0.333 vs 0.110** · N=400: 0.332 vs 0.230 | `predictiveness.csv` |
| Next-season run value (min 300 pitches) | 0.283 vs 0.202 for this season's results | `reliability.csv` |
| Split-half reliability (odd/even games) | 0.742 vs 0.177 for observed run value | `reliability.csv` |
| Serving model fidelity (distilled, dashboard inputs only) | R² 0.942 | bundle manifest |

## Combination weights (`weights.csv`, runs per 1 sd of each rate)
The sign-constrained fit keeps the component composite (+0.047) and P(out within PA) (−0.020), gives small weights
to called strikes (−0.00045) and chases (−0.0007), and sets whiff, weak contact, groundball and hard-contact rates to
0: their information is already inside the composite, and their unconstrained coefficients would take the "wrong"
sign. Weights are stable across folds (fold sd ≤ 0.0004).

## Limits
- Exploratory/transductive parts: pitch identity, arsenal references, per-game air density and the LMB run values
  behind `rv_x` are estimated once on all data before the folds (none uses a pitch's own outcome as a feature).
- The dashboard model is a distillation on the inputs a coach can type (physics, three fastball diffs, location,
  count, batter side); outs, inning and sequence are averaged out in the simulator.
