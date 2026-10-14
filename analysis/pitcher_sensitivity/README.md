# Pitcher altitude sensitivity · HACK-018

Run `python analysis/pitcher_sensitivity/run.py --fast` for an exploratory fit
on official local data; omit `--fast` for the default HACK-015 training rounds.
Only anonymized aggregates are exported into `reports/pitcher_sensitivity/`.
The reusable API is `stuffplus.sensitivity.summarize_sensitivity(frame)`;
see its docstring for the input contract. Game identifier: `game_anon_id`.

Counterfactual arsenal Δ is the full-season usage-weighted mean CDMX minus
sea-level Stuff+. The driver is the pitch with largest absolute weighted
contribution; its IVB/HB changes describe the modeled physical mechanism.
Observed split is **model-scored quality in observed air**, not actual run
prevention: Extreme Altitude minus No Altitude, using identical usage weights
on pitch identities represented by at least 20 pitches in each bucket.
`split_usage_coverage` reports how much of the arsenal that comparison covers.

Variance clusters pitches by game. Normal empirical Bayes estimates a prior
per season using between-pitcher variance minus mean sampling variance.
Sparse/noisy pitchers shrink more; single-game pitchers lack a valid variance
and cannot be ranked. Posterior 95% intervals condition on the estimated prior,
physics, identities, fitted model, estimated league baseline and usage weights:
they exclude fitting, prior, baseline and usage uncertainty and do not quantify
certainty of rank order.
The index is `100 + posterior delta - pitch-weighted season league delta`,
in Stuff+ points, not a percentage or percentile. It ranks resistance relative
to the league, and does not imply a positive absolute gain.

Top/bottom tables contain up to 15 **pitcher-season entries** each, disjoint;
small cohorts return fewer entries. Minimum eligibility is 100 pitches and a
valid EB estimate; absent observed splits stay missing and do not get invented.
All fits use global preparation and in-sample scoring: exploratory descriptions,
not causal effects, predictive validation, or deployment-ready recruiting advice.
Raw records and pitch-level predictions must never enter git.
