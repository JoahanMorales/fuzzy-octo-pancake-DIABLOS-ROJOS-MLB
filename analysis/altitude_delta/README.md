# Altitude effect by pitch shape (HACK-015)

`python analysis/altitude_delta/run.py` (~10 min). Every LMB pitch is moved from the air it was thrown in to
sea-level air (ρ = 1) and to Harp Helú air (ρ = 0.819, `physics.constants.RHO_HARP_HELU`) with the fitted
per-family proportional physics (`features.shapes`), then scored by the component Stuff+ model retrained with the
altitude-invariant `pitch_family`; the 0.7 % of pitches the identity leaves unassigned are excluded, so Trackman's
AutoPitchType never enters (it relabels pitches with air density). Both scores use the same park-neutral
ruler, so ΔStuff+ = Stuff+(Harp Helú air) − Stuff+(sea level). CIs resample whole pitchers.

## Results (real data, 2026-10-13) · `delta_by_shape.csv`, `forest_by_shape.png`

League average: **−10.3 Stuff+** in Harp Helú air. **In absolute terms every shape loses**; "gana relativo" /
"pierde relativo" in the `verdict` column means its CI sits above / below the league average.

| Holds up best (relative to league) | ΔStuff+ [95 % CI] | Loses most | ΔStuff+ [95 % CI] |
|---|---|---|---|
| **Sweeper** | −4.6 [−5.4, −3.9] | **Riding four-seam (IVB ≥ 17")** | **−16.0 [−16.3, −15.6]** |
| 12-6 curveball | −6.1 [−6.9, −5.4] | Power changeup (≥ 86 mph) | −12.7 [−13.6, −11.7] |
| Slider | −7.2 [−7.7, −6.8] | Changeup | −11.4 [−12.1, −10.7] |
| Splitter | −7.6 [−9.8, −5.9] | | |

Damage on contact (model-based, physics + air, `delta_hard_contact_pct`, `delta_hr_per_fb_pct`): HR per fly ball
rises in Harp Helú air for every shape, from **+1.0 pp (sweeper)** and +1.8 pp (power changeup) to +5.1 pp (sinkers,
cutters) and **+6.2 pp (splitter)**; hard contact on balls in play moves −0.2 to +1.9 pp. A ball in play is worth
+0.032 to +0.065 more runs to the hitter (`delta_contact_runs`).

Physics (`physics` column): the riding four-seam loses 5.3" of ride and 3.1 pp of whiffs, the largest whiff loss of
any shape; its value is spin-driven ride. Changeups lose 4.3–6.0" of fade (H2 is not supported: they do not hold up
better than breaking balls).

## Triangulation · `triangulation.csv` (all with pitcher-cluster 95 % CIs)
Same pitch (pitcher × season × pitch_id) in Extreme-altitude games vs sea-level games, compared with the
counterfactual at the Extreme bucket's air (ρ = 0.838):
- Counterfactual ΔStuff+ −5.8 to −10.0 by family; the model's Stuff+ measured on the pitches actually thrown in
  Extreme games moves the same way in 7/7 families (−5.0 to −12.0).
- The pitchers' **actual results** (rv_x in Stuff+ points) drop more on average: −7.2 to −14.7. The observed CI
  contains the counterfactual in 6/7 families; curveballs are the exception (observed −14.7 [−21.5, −8.1] vs
  counterfactual −7.8 [−8.4, −7.2]), so the model is, if anything, conservative about the altitude penalty.
- Observed whiff change within pitcher is negative and significant for changeups (−1.5 pp [−2.7, −0.35]) and
  four-seamers (−0.8 pp [−1.3, −0.3]); for cutters (+1.2 pp) and splitters (+3.0 pp) the point estimates are
  positive but the CIs include 0 (small samples).

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
