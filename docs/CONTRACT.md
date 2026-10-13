# Contract · Stuff+ 2240 (HACK-002)

Everything downstream builds on this page. Changing anything here needs `uak msg related:HACK-002 --kind contract` BEFORE pushing.

## 1. From raw rows to modelling rows

```python
from stuffplus.io import load_raw
from stuffplus.schema import clean
df = clean(load_raw())          # 635,002 → 627,602 rows, ~3 s
df.attrs["clean_report"]        # every drop, counted
```

| Step (in this order) | Real-data effect |
|---|---|
| Sequence columns on the RAW order: `pa_id`, `pitch_number_in_pa`, `pitch_idx_in_game`, `pa_ends` | 166k PAs, 3.78 pitches/PA, 98 % start 0-0 (the rest are Trackman gaps) |
| `Sweeper → Slider`; `Switch` batter → side opposite the pitcher | 588 / 54 rows |
| Drop unknown altitude | 3,020 |
| Drop missing `pitcher_anon_id` | 2,956 |
| Drop `Undefined` pitcher hand / batter side | 131 / 238 |
| Drop `PitchCall == Undefined` | 551 |
| Drop `Other`, `OneSeamFastBall`, `TwoSeamFastBall`, `Knuckleball` | 64 |
| Drop rows without `RelSpeed`, `InducedVertBreak` or `HorzBreak` (`drop_missing_physics=True`) | 440 |

Added columns: `is_rhp`, `batter_is_right`, `same_side`, `home_batting` (Bottom half; the home team pitches the Top), `is_fastball`. `EffectiveVelo` is cast to float. `AutoPitchType` and `altitude_category` become categoricals with fixed levels (`schema.PITCH_TYPES`, `schema.ALTITUDE_LEVELS`).

Gotchas:
- Use `df["count"]`, never `df.count` (that is the pandas method).
- `PitchTrajectory{X,Y,Z}c*` use Trackman's frame: **X = toward the plate, Y = height, Z = side** (`Zc0 ≈ -RelSide`); `c2` = half the acceleration. `x0/y0/z0` use x = side, y = distance (always 50 ft), z = height.
- `AutoPitchType` shifts with altitude (same pitchers in Extreme vs No: Sinker −2.8 pp, Changeup −2.8 pp, Cutter +2.5 pp, Slider +2.5 pp). See §4.

## 2. Feature roles and the leak guard

| List | Use |
|---|---|
| `schema.PHYSICAL_FEATURES` | release-point physics: the only raw inputs of pure Stuff+ |
| `schema.FLIGHT_FEATURES` | whole-flight values (approach angles, trajectory); Stuff+ only with a written reason |
| `schema.LOCATION_FEATURES` | Location+ / Pitching+ only |
| `schema.CONTEXT_FEATURES` | count, outs, handedness, sequence: Location+ / Pitching+ |
| `schema.TARGET_COLUMNS`, `schema.ID_COLUMNS` | never features |

```python
schema.assert_no_target_leak(features, allow_location=False)   # pure Stuff+
X = schema.feature_frame(df, features, allow_location=True)      # Location+ / Pitching+
```

Targets and the LMB run value come from `stuffplus.targets` (HACK-030). Target columns are named `t_*` and run values `rv` / `rv_*`; the leak guard rejects those prefixes automatically.

## 3. Validation splits (`stuffplus.splits`)

All return positional indices for `df.iloc` and are deterministic (seed 2240).

| Split | Call | Real-data size |
|---|---|---|
| Pitcher 5-fold (main CV, out-of-fold predictions) | `pitcher_group_kfold(df)` · `pitcher_folds(df)` | 5 × ~125.5k, no pitcher in two folds |
| Season holdout | `season_holdout(df)` | train 498,032 (2024–25) · test 129,570 (2026) |
| Park holdout | `park_holdout(df)` | train 446,570 (No + Medium) · test 181,032 (Extreme) |
| Leave-one-park-out | `park_holdout(df, train=…, test=…, col="park_id")` | after HACK-003 |

Every model reports against `stuffplus.baseline.CountBaseline` (HACK-005) on these splits.

## 4. Pitch identity (until HACK-029 ships `stuffplus.features.identity`)

Within-pitcher comparisons by pitch type must not use `AutoPitchType` alone (it relabels with altitude). Fallback:
1. Per pitcher-season, KMeans on standardized (`RelSpeed`, `SpinRate`, `RelHeight`, `RelSide`, `Extension`); these do not depend on air density.
2. k = number of `AutoPitchType` labels with ≥ 5 % usage for that pitcher-season.
3. Cluster label = majority `AutoPitchType` among that cluster's pitches in **No Altitude** games (fallback: all games).

## 5. Prediction API (`stuffplus.api`)

```python
from stuffplus.api import PitchInput, predict_pitch, compare_environments
p = PitchInput(pitch_type="Four-Seam", throws="Right", velo=95, spin_rate=2400, spin_axis=210,
               ivb=18, hb=9, extension=6.4, rho_measured=1.0, plate_x=0.6, plate_z=3.2, balls=0, strikes=2)
predict_pitch(p, rho="harp_helu")                  # environment Stuff+ in CDMX air
predict_pitch(p, rho="harp_helu", flavour="neutral")  # park-neutral (sea level) Stuff+
compare_environments(p, "harp_helu", "sea_level")  # simulator side-by-side + deltas
```

- `rho`: float relative to sea level (0.6–1.2) or a preset: `sea_level`, `harp_helu`, `extreme_altitude`, `medium_altitude`, `coors`. Measured values from `stuffplus.physics.constants` (HACK-004) override the provisional ones.
- `rho_measured`: the air in which `ivb`/`hb` were measured. A coach can type the movement seen in CDMX (`rho_measured=api.resolve_rho("harp_helu")`).
- Output keys (`api.PREDICTION_KEYS`): `stuff_plus`, `stuff_plus_neutral`, `location_plus` (None without plate location), `pitching_plus`, `xrv` (runs per pitch, batter's view: lower is better for the pitcher), `probs` (`api.PROB_KEYS`: whiff, chase, called_strike, weak_contact, groundball, hard_contact, out_in_pa), `movement_expected` ({ivb, hb} in the target air), `rho`, `flavour`, `model_version`, `demo_data`.
- Until `stuffplus.serving.available()` is True, a deterministic mock answers with `demo_data: True` (`model_version: "mock-0"`). The UI must show a "datos de demostración" badge whenever `demo_data` is True.

**Serving contract (HACK-031):** `stuffplus/serving.py` exposes `available() -> bool` and `predict_pitch(p: PitchInput, rho: float, flavour: str) -> dict` returning exactly the keys above.

## 6. Stuff+ scale (HACK-013)

`Stuff+ = 100 + 10 · z`, with `z = −(xRV − μ_season) / σ_season` and μ, σ taken over all LMB pitches of that season **scored at sea-level air**. One ruler, two flavours:
- **neutral**: the pitch scored at ρ = 1.0;
- **environment**: the same pitch scored at the park's ρ (e.g. Harp Helú).

ΔStuff+ in CDMX = environment(ρ_HH) − neutral. 100 = league average; 110 = one SD better; 120 ≈ 97.7th percentile.

## 7. Artifact bundle (`artifacts/bundle/`, git-ignored)

```
artifacts/bundle/
  manifest.json        # see below
  models/<name>.txt    # LightGBM boosters (stuff_xrv, stuff_whiff, location_xrv, pitching_<target>, ...)
  tables/<name>.csv    # aggregates only (leaderboards, delta_by_shape, park table); never pitch-level rows
```

```json
{
  "version": "v0", "created_at": "2026-10-13T00:00:00-06:00", "git_sha": "<sha>",
  "models": {"stuff_xrv": {"file": "models/stuff_xrv.txt", "features": ["RelSpeed", "..."],
             "target": "rv", "objective": "regression", "categorical": ["AutoPitchType"]}},
  "rho": {"sea_level": 1.0, "harp_helu": 0.81},
  "scaler": {"by": ["year"], "sign": -1, "stats": {"2024": {"mean": 0.0, "sd": 0.01}}},
  "metrics": {"pitcher_kfold": {"rmse": 0.0, "rmse_baseline": 0.0}}
}
```

The deployed dashboard (HACK-024) ships only `manifest.json`, `models/` and `tables/`.
