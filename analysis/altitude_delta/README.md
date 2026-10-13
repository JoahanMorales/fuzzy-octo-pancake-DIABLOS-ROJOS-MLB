# Altitude effect by pitch shape (HACK-015)

`python analysis/altitude_delta/run.py` (~10 min). Every LMB pitch is moved from the air it was thrown in to
sea-level air (ρ = 1) and to Harp Helú air (ρ = 0.819, `physics.constants.RHO_HARP_HELU`) with the fitted
per-family proportional physics (`features.shapes`), then scored by the component Stuff+ model retrained with the
altitude-invariant `pitch_family` (Trackman's AutoPitchType is never used). Both scores use the same park-neutral
ruler, so ΔStuff+ = Stuff+(Harp Helú air) − Stuff+(sea level). CIs resample whole pitchers.

## Results (real data, 2026-10-13) · `delta_by_shape.csv`, `forest_by_shape.png`

League average: **−10.3 Stuff+** in Harp Helú air (less break, and a ball in play is worth +0.032 to +0.065 more
runs to the hitter depending on the shape: `delta_contact_runs`).

| Holds up best (relative to league) | ΔStuff+ [95 % CI] | Loses most | ΔStuff+ [95 % CI] |
|---|---|---|---|
| **Sweeper** | −4.6 [−5.4, −3.9] | **Riding four-seam (IVB ≥ 17")** | **−16.0 [−16.3, −15.6]** |
| 12-6 curveball | −6.1 [−6.9, −5.4] | Power changeup (≥ 86 mph) | −12.7 [−13.6, −11.7] |
| Slider | −7.2 [−7.7, −6.8] | Changeup | −11.4 [−12.1, −10.7] |
| Splitter | −7.6 [−9.8, −5.9] | | |

Physics (`physics` column): the riding four-seam loses 5.3" of ride and 3.1 pp of whiffs, the most of any shape;
its value IS spin-driven ride. Changeups lose 4–6" of fade (H2 rejected: they do not gain in altitude). Sweepers
and 12-6 curves lose the least relative value.

## Triangulation · `triangulation.csv`
For the same pitch (pitcher × season × pitch_id) thrown in Extreme-altitude games vs sea-level games, the model's
Stuff+ and the pitcher's actual results (rv_x, in Stuff+ points) both drop, with the **same sign as the counterfactual
for all 7 families** (counterfactual −5.8 to −10.0 at the Extreme bucket's ρ = 0.838; observed results −7.2 to −14.7).

## Altitude curves · `altitude_curves.csv`, `altitude_curves.png`
Mean ΔStuff+ by shape for ρ = 1.0 → 0.80, which covers every LMB park (Medium ≈ 0.89, Extreme ≈ 0.84, Harp Helú 0.819).

## Limits
- ρ_HarpHelú = 0.819 is the pooled density of the two lowest-density Extreme parks (CDMX vs Puebla not separable,
  P = 0.83; `reports/park_id/harp_helu.md`).
- The counterfactual is model-based and in-sample for scoring; validation of the model itself is in
  `reports/stuff_model/` (pitcher-grouped OOF) and HACK-014.
- ρ is game-level, so the model's ρ effect can absorb park traits that travel with altitude; the within-pitcher
  observed check bounds that.
- Exploratory/transductive parts: the pitch identity, the per-family physics (`fit_shapes`), the per-game air density
  and the LMB run values behind `rv_x` are estimated once on all the data; no step uses a pitch's own outcome as a
  feature, but treat CIs as conditional on those fitted inputs.
