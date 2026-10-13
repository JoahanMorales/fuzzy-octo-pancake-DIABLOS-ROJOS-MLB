# Scores and leaderboards (HACK-016) · challenge deliverable 1

`python -m stuffplus.score` (~40 min) scores all 623,231 pitches with an identified pitch family **out of fold** (folds grouped by
pitcher: the model that scores a pitcher never saw him) and writes:

- `artifacts/scores/pitch_scores.parquet` (git-ignored, ~60 MB): per pitch `PitchUID`, Stuff+ (park-neutral, sea
  level), Stuff+ in Harp Helú air, Stuff+ in the air it was thrown in, Location+, Pitching+ (league-average batter).
  **This is the per-pitch deliverable: it goes in the submission email, never in git.**
- `reports/leaderboards/` (aggregates, anonymized ids, shrunk toward 100 with empirical Bayes):

| File | Rows | Content |
|---|---|---|
| `pitcher_season.csv` | 818 | pitcher-seasons with ≥ 300 pitches: all scores, ΔCDMX, arsenal signature, Stuff+ percentile |
| `pitcher_pitch.csv` | 3,546 | pitcher × pitch (≥ 50 pitches): family, shape, usage, velo/IVB/HB/spin, all scores |
| `best_arsenals_harp_helu.csv` | 25 | answer to "¿qué arsenal produce el Stuff+ más alto en Harp Helú?" |
| `arsenal_archetypes.csv` | 30 | pitchers grouped by their two most used shapes (≥ 5 pitcher-seasons each) |
| `by_park.csv` | 20 | every LMB home park (HACK-003 franchises): air density, neutral Stuff+, Stuff+ in its own air |
| `by_altitude.csv` | 3 | the same by altitude bucket |

## What the tables say (real data, 2026-10-13)

**Air, park by park (`by_park.csv`).** Neutral Stuff+ is ≈ 100 in every park (97.9–101.6): the pitchers are
comparable; what changes is the air. Stuff+ in each park's own air falls with its density almost monotonically
(r = 0.996 with ρ, Spearman 0.989), from
**+4.3 at the densest sea-level park (ρ = 1.06)** to **−10.3 and −10.7 at the two Harp Helú candidates
(ρ = 0.82 and 0.81, franchises 5 and 11)**. Parks at ρ 0.86–0.89 sit at −6.9 to −9.1; one Medium-bucket park at
ρ 0.94 is at −3.5.

**By bucket (`by_altitude.csv`).** Stuff+ in own air: sea level 100.7, Medium 92.8, Extreme 91.2; Pitching+ 101.4 /
99.2 / 98.5 (Pitching+ falls less because location and count do not depend on the air).

**Best arsenals in Harp Helú air (`best_arsenals_harp_helu.csv`).** The top pitcher-season keeps 104.8 in CDMX air
(ΔCDMX −2.6) with *four-seam 43 % · sweeper 24 % · slider 16 %*; arsenals built on sweepers and sinkers keep the most
value, ride-heavy ones lose the most (consistent with HACK-015).

**Archetypes (`arsenal_archetypes.csv`, small samples: 5–44 pitcher-seasons each).** Among archetypes with ≥ 15
pitcher-seasons, *sinking two-seam + sweeper* (n = 20) has the highest Stuff+ in Harp Helú air (93.5, Δ −7.6) and
*four-seam + sweeper* (n = 19) loses the least (Δ −6.7). Ride-heavy archetypes lose the most: *11-5 curve + riding
four-seam* −12.6 (n = 15), *gyro slider + riding four-seam* −12.0 (n = 62), *changeup + riding four-seam* −11.9
(n = 42); overall the largest loss is *power changeup + riding four-seam* (−14.0, n = 6).

## Limits
- ΔCDMX for a pitch type comes from the physics translation + Stuff+ model (HACK-015); the observed check is there.
- Harp Helú is one of franchises 5 and 11 (P = 0.83 for the separation, HACK-003): both are reported.
- Exploratory/transductive parts as in HACK-012/015 (identity, density, run values estimated once on all data).
