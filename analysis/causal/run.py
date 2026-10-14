"""Exploratory BB-vs-offspeed DML contrasts; no causal identification or policy promotion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import GroupKFold

from stuffplus import config, schema, targets
from stuffplus.physics import aero

SEED = 2240
BREAKING = {"Slider", "Curveball"}
OFFSPEED = {"Changeup", "Splitter"}
X_COLS = ["Balls", "Strikes", "same_side", "rho"]
W_COLS = ["is_rhp", "Outs", "inning_capped", "prior_fb_velo", "prior_fb_missing",
          "prev_velo", "prev_missing", "prev_breaking", "prev_offspeed"]
LIMITATION = (
    "Exploratory observational contrast, not an identified causal effect or pitch-selection policy. "
    "Coach intent, hitter quality, health and other unmeasured confounders remain. Global target, "
    "identity and density preparation is transductive. Density is reconstructed from whole-game "
    "observations and is not a verified prospectively available pre-pitch measurement. "
    "Bootstrap intervals describe held-out "
    "pitcher composition conditional on one fitted forest, not model/causal uncertainty. "
    "Current-pitch movement, location, outcome and derived scores are excluded from covariates."
)


def sample_games(frame, max_rows=None):
    """Outcome-independent seeded sample of WHOLE games; preserve source chronology."""
    if max_rows is None or len(frame) <= max_rows:
        return frame.copy()
    if max_rows < 100:
        raise ValueError("max_rows must be >=100")
    sizes = frame.groupby("game_anon_id", sort=False).size()
    order = np.random.default_rng(SEED).permutation(sizes.index.to_numpy())
    total, selected = 0, []
    for game in order:
        selected.append(game)
        total += int(sizes[game])
        if total >= max_rows:
            break
    return frame[frame.game_anon_id.isin(selected)].copy()


def pre_pitch_covariates(frame):
    """Past fastballs and the preceding pitch only; no current-treatment physics."""
    d = frame.copy()
    keys = [d.pitcher_anon_id, d.year]
    fast = d.AutoPitchType.astype(str).isin(["Four-Seam", "Sinker", "Cutter"])
    speed_sum = d.RelSpeed.where(fast, 0.0).groupby(keys, sort=False).cumsum()
    count = fast.astype(int).groupby(keys, sort=False).cumsum()
    prior_sum = speed_sum.groupby(keys, sort=False).shift(1)
    prior_count = count.groupby(keys, sort=False).shift(1)
    profile = prior_sum / prior_count.where(prior_count > 0)
    d["prior_fb_velo"] = profile.fillna(0.0)
    d["prior_fb_missing"] = profile.isna().astype(int)
    pa = d.groupby("pa_id", sort=False)
    prev = pa.RelSpeed.shift(1)
    typ = pa.AutoPitchType.shift(1).astype(str)
    d["prev_velo"] = prev.fillna(0.0)
    d["prev_missing"] = prev.isna().astype(int)
    d["prev_breaking"] = typ.isin(BREAKING).astype(int)
    d["prev_offspeed"] = typ.isin(OFFSPEED).astype(int)
    d["inning_capped"] = d.Inning.clip(upper=10)
    return d


def prepare(raw, *, fast=False, max_rows=None):
    from stuffplus.models.location import add_pitch_family

    clean = schema.clean(raw)
    sampled = sample_games(clean, max_rows)
    # Preserve the assigned/fallback flags: call identity preparation only once.
    d = add_pitch_family(sampled)
    drag = aero.decompose(d).cd_proxy
    ref = drag[d.is_fastball.eq(1) & d.altitude_category.astype(str).eq("No Altitude")].median()
    if not np.isfinite(ref) or ref <= 0:
        raise ValueError("no valid sea-level fastballs for density reference")
    density = aero.game_density_index(d, game_col="game_anon_id", ref_cd=float(ref))
    d["rho"] = d.game_anon_id.map(density).fillna(float(density.mean()))
    re = targets.fit_run_expectancy(d)
    lw = targets.fit_linear_weights(d, re)
    d = targets.add_expected_run_value(targets.add_run_value(d, re, lw), lw, rounds=40 if fast else 300)
    return pre_pitch_covariates(d)


def treatment_frame(frame, outcome="rv_x"):
    required = {*X_COLS, *W_COLS, outcome, "pitch_family", "pitcher_anon_id", "year", "altitude_category"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"missing causal columns: {sorted(missing)}")
    fam = frame.pitch_family.astype(str)
    eligible = fam.isin(BREAKING | OFFSPEED)
    finite = np.isfinite(frame[[outcome, *X_COLS, *W_COLS]].to_numpy(float)).all(axis=1)
    d = frame[eligible & finite & frame.pitcher_anon_id.notna()].copy().reset_index(drop=True)
    d["treatment"] = d.pitch_family.astype(str).isin(BREAKING).astype(int)
    d["count_bucket"] = np.where(d.Strikes > d.Balls, "ahead", np.where(d.Strikes < d.Balls, "behind", "even"))
    return d


def grouped_folds(train, k=3):
    if train.pitcher_anon_id.nunique() < k:
        raise ValueError(f"need >={k} training pitchers")
    folds = list(GroupKFold(k).split(train, train.treatment, groups=train.pitcher_anon_id))
    for tr, te in folds:
        if set(train.iloc[tr].pitcher_anon_id) & set(train.iloc[te].pitcher_anon_id):
            raise ValueError("pitcher leakage in nuisance folds")
        if train.iloc[tr].treatment.nunique() != 2 or train.iloc[te].treatment.nunique() != 2:
            raise ValueError("each nuisance fold needs both treatment families")
    return folds


def bootstrap_contrast(values, groups, n_boot=300):
    """Resample complete pitchers, conditional on the fitted test predictions."""
    d = pd.DataFrame({"effect": values, "group": groups}).groupby("group").effect.agg(["sum", "count"])
    if len(d) < 3:
        return np.nan, np.nan
    rng = np.random.default_rng(SEED)
    weights = rng.multinomial(len(d), np.full(len(d), 1 / len(d)), size=n_boot)
    means = (weights @ d["sum"].to_numpy()) / (weights @ d["count"].to_numpy())
    return tuple(np.quantile(means, [.025, .975]))


def fit_analysis(frame, out_dir, *, demo_data, outcome="rv_x", fast=False,
                 overlap=(.1, .9), min_cell=30, min_pitchers=5):
    try:
        from econml.dml import CausalForestDML
    except ImportError as e:
        raise ImportError("Install optional analysis/causal/requirements.txt in an isolated environment") from e
    lo, hi = overlap
    if not 0 < lo < hi < 1 or min_cell < 1 or min_pitchers < 3:
        raise ValueError("invalid overlap or cell support settings")
    d = treatment_frame(frame, outcome)
    train = d[d.year.isin([2024, 2025])].reset_index(drop=True)
    test = d[d.year.eq(2026)].reset_index(drop=True)
    if train.empty or test.empty:
        raise ValueError("need training years2024/2025 and held-out year2026")
    folds = grouped_folds(train)
    C = train[X_COLS + W_COLS].to_numpy(float)
    classifier = RandomForestClassifier(n_estimators=40 if fast else 150, max_depth=6,
                                         min_samples_leaf=20, random_state=SEED, n_jobs=1)
    propensity_oof = np.full(len(train), np.nan)
    for tr, te in folds:
        m = clone(classifier).fit(C[tr], train.treatment.to_numpy()[tr])
        propensity_oof[te] = m.predict_proba(C[te])[:, 1]
    # Support is diagnosed with group-OOF propensities, not training fitted probabilities.
    support = (propensity_oof >= lo) & (propensity_oof <= hi)
    fitted = train[support].copy().reset_index(drop=True)
    grouped_folds(fitted)  # Fail before EconML if trimming destroys identifiability.
    forest = CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=40 if fast else 150, max_depth=6,
                                      min_samples_leaf=20, random_state=SEED, n_jobs=1),
        model_t=clone(classifier), discrete_treatment=True, cv=GroupKFold(3),
        n_estimators=64 if fast else 400, max_depth=6, min_samples_leaf=15,
        max_samples=.45, honest=True, inference=False, n_jobs=2, random_state=SEED)
    forest.fit(fitted[outcome].to_numpy(float), fitted.treatment.to_numpy(),
               X=fitted[X_COLS].to_numpy(float), W=fitted[W_COLS].to_numpy(float),
               groups=fitted.pitcher_anon_id.to_numpy())
    full_propensity = clone(classifier).fit(C, train.treatment.to_numpy())
    probability = full_propensity.predict_proba(test[X_COLS + W_COLS].to_numpy(float))[:, 1]
    test["supported"] = (probability >= lo) & (probability <= hi)
    test["effect"] = forest.effect(test[X_COLS].to_numpy(float), T0=0, T1=1)
    if not np.isfinite(test.effect).all():
        raise ValueError("forest returned nonfinite test contrasts")
    rows = []
    for altitude in schema.ALTITUDE_LEVELS:
        for bucket in ("ahead", "even", "behind"):
            cell = test[(test.altitude_category.astype(str) == altitude) & (test.count_bucket == bucket)]
            keep = cell[cell.supported]
            n0, n1 = int(keep.treatment.eq(0).sum()), int(keep.treatment.eq(1).sum())
            groups = int(keep.pitcher_anon_id.nunique())
            enough = min(n0, n1) >= min_cell and groups >= min_pitchers
            low, high = bootstrap_contrast(keep.effect, keep.pitcher_anon_id, 100 if fast else 300) if enough else (np.nan, np.nan)
            rows.append(dict(altitude=altitude, count_bucket=bucket, n_total=len(cell),
                             n_supported=len(keep), n_offspeed=n0, n_breaking=n1, pitchers=groups,
                             contrast_bb_minus_offspeed=float(keep.effect.mean()) if enough else np.nan,
                             composition_ci_lo=low, composition_ci_hi=high,
                             status="exploratory" if enough else "insufficient_support"))
    table = pd.DataFrame(rows)
    table["demo_data"] = bool(demo_data)
    table["evidence"] = "observational_transductive"
    meta = dict(demo_data=bool(demo_data), evidence="observational_transductive", promotion_allowed=False,
                limitation=LIMITATION, outcome=outcome, fast=fast, seed=SEED,
                treatment="1=Slider/Curveball, 0=Changeup/Splitter (pitch_family)",
                effect_direction="negative means lower modelled xRV for breaking balls",
                train_years=[2024,2025], test_year=2026, nuisance_cv="3-fold grouped by pitcher",
                eligible_rows=len(d), train_rows=len(train), train_supported_rows=len(fitted),
                test_rows=len(test), test_supported_rows=int(test.supported.sum()),
                overlap_bounds=list(overlap), min_cell_per_treatment=min_cell, min_pitchers=min_pitchers,
                x_columns=X_COLS, w_columns=W_COLS,
                identity_fallback_fraction=(float((~frame.pitch_family_assigned).mean())
                    if "pitch_family_assigned" in frame else None))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out/"contrasts.csv", index=False)
    (out/"provenance.json").write_text(json.dumps(meta, indent=2)+"\n")
    (out/"analysis.md").write_text(
        f"# Contrastes exploratorios por conteo y altitud\n\ndemo_data: {str(demo_data).lower()}\n\n"
        f"{LIMITATION}\n\nTratamiento: bola rompiente menos cambio/splitter; menor xRV es mejor para el pitcher. "
        "Los intervalos describen composición de pitchers del holdout con el bosque fijo. "
        "No son intervalos de identificación causal ni una recomendación de selección.\n\n"
        f"```csv\n{table.to_csv(index=False)}```\n")
    return table, meta


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--demo", action="store_true")
    p.add_argument("--fast", action="store_true")
    p.add_argument("--max-rows", type=int)
    p.add_argument("--prepared", type=Path, help="local prepared parquet, e.g. true OOF xRV plus pre-pitch controls")
    p.add_argument("--outcome", default="rv_x")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if args.max_rows is not None and args.max_rows < 100:
        p.error("--max-rows must be >=100")
    if args.prepared and args.max_rows is not None:
        p.error("--max-rows applies to raw-game sampling, not --prepared inputs")
    if args.prepared:
        frame = pd.read_parquet(args.prepared)
    else:
        if args.demo:
            from tests.fixtures.synthetic import make_synthetic_pitches
            raw = make_synthetic_pitches()
        else:
            from stuffplus.io import load_raw
            raw = load_raw()
        print("Preparing sampled whole games, identities, targets and prior-pitch controls...", flush=True)
        frame = prepare(raw, fast=args.fast, max_rows=args.max_rows or (12000 if args.fast else None))
    out = args.out or config.REPORTS_DIR/"causal"/("demo" if args.demo else "official_fast" if args.fast else "official")
    print("Fitting grouped nuisances and forest; scoring held-out year2026...", flush=True)
    table, meta = fit_analysis(frame, out, demo_data=args.demo, outcome=args.outcome, fast=args.fast)
    meta["preparation"] = "supplied prepared frame; origin must be independently verified" if args.prepared else "global target/identity/density on selected whole games"
    meta["game_sample_limit"] = None if args.prepared else args.max_rows or (12000 if args.fast else None)
    (out/"provenance.json").write_text(json.dumps(meta, indent=2)+"\n")
    print(table[["altitude", "count_bucket", "n_supported", "contrast_bb_minus_offspeed", "status"]].to_string(index=False))
    print(f"Aggregates -> {out}; demo_data={args.demo}; no causal-policy promotion", flush=True)


if __name__ == "__main__":
    main()
