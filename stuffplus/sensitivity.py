"""Pitcher-season altitude sensitivity; descriptive, conditional on fitted models.

Input is one row per pitch, with HACK-015 stuff_a (CDMX), stuff_b (sea
level), plus model scores in the observed environment. No outcome-based
claim of causality is made. Intervals exclude model/physics fit uncertainty.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEYS = ["pitcher_anon_id", "year"]


def _mean_variance(values, games):
    """Pitch-weighted mean and game-cluster sandwich variance of the mean."""
    v = np.asarray(values, dtype=float)
    mean = float(v.mean())
    residual = pd.Series(v - mean).groupby(np.asarray(games)).sum()
    g = len(residual)
    variance = g / (g - 1) * float((residual ** 2).sum()) / len(v) ** 2 if g > 1 else np.nan
    return mean, variance


def _shrink(table, value, variance, prefix):
    """Season-specific normal EB; missing cluster variance stays unrankable."""
    out = table.copy()
    for _, idx in out.groupby("year").groups.items():
        t = out.loc[idx]
        valid = t[value].notna() & t[variance].notna()
        x, v = t.loc[valid, value], t.loc[valid, variance]
        if len(x) < 2:
            continue
        mu = float(x.mean())
        tau2 = max(0.0, float(x.var(ddof=1) - v.mean()))
        # A zero between-pitcher variance collapses to the estimated prior mean.
        weight = tau2 / (tau2 + v) if tau2 > 0 else pd.Series(0.0, index=x.index)
        posterior = mu + weight * (x - mu)
        sd = np.sqrt(weight * v)
        out.loc[x.index, f"{prefix}_eb"] = posterior
        out.loc[x.index, f"{prefix}_lo"] = posterior - 1.96 * sd
        out.loc[x.index, f"{prefix}_hi"] = posterior + 1.96 * sd
        out.loc[x.index, f"{prefix}_weight"] = weight
    for suffix in ("eb", "lo", "hi", "weight"):
        col = f"{prefix}_{suffix}"
        if col not in out:
            out[col] = np.nan
    return out


def summarize_sensitivity(frame: pd.DataFrame, min_pitches: int = 100, min_split: int = 20) -> dict:
    """Return aggregate pitchers/pitches and disjoint top/bottom 15 rankings.

    Altitude-proof index = 100 + shrunk counterfactual Δ minus pitch-weighted
    season league Δ (Stuff+ points, not a percentile). Observed splits use only
    pitch identities present in both Extreme Altitude and No Altitude, with
    identical full-season usage weights renormalized over that common support.
    """
    required = KEYS + ["pitch_key", "game_anon_id", "altitude_category", "stuff_a", "stuff_b", "observed_stuff_plus"]
    missing = set(required) - set(frame)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame.empty or frame[required].isna().any().any():
        raise ValueError("Input must contain nonmissing pitch identifiers and scores")
    if min_pitches < 1 or min_split < 1:
        raise ValueError("Minimum counts must be positive")
    d = frame.copy()
    for col in ("stuff_a", "stuff_b", "observed_stuff_plus"):
        if not np.isfinite(d[col].to_numpy(float)).all():
            raise ValueError(f"Nonfinite {col}")
    if "PitchUID" in d and d.PitchUID.duplicated().any():
        raise ValueError("Duplicate PitchUID would double-count usage")
    d["delta_stuff"] = d.stuff_a - d.stuff_b
    pitcher_rows, pitch_rows = [], []
    for key, g in d.groupby(KEYS, sort=True):
        mean, variance = _mean_variance(g.delta_stuff, g.game_anon_id)
        parts = []
        for pitch, p in g.groupby("pitch_key", sort=True):
            delta, _ = _mean_variance(p.delta_stuff, p.game_anon_id)
            row = dict(zip(KEYS, key), pitch_key=pitch, pitches=len(p), usage=len(p) / len(g), delta_stuff=delta)
            row["weighted_delta"] = row["usage"] * delta
            family = p.pitch_family.dropna().mode() if "pitch_family" in p else pd.Series(dtype=str)
            row["pitch_family"] = str(family.iloc[0]) if len(family) else "unknown"
            for col in ("delta_ivb_in", "delta_hb_arm_in"):
                row[col] = float(p[col].mean()) if col in p else np.nan
            pitch_rows.append(row)
            parts.append(row)
        arsenal = pd.DataFrame(parts)
        # The largest absolute weighted contribution identifies the driving pitch.
        driver = arsenal.loc[arsenal.weighted_delta.abs().idxmax()]
        extreme = g[g.altitude_category == "Extreme Altitude"]
        sea = g[g.altitude_category == "No Altitude"]
        common = [p for p in arsenal.pitch_key if (extreme.pitch_key == p).sum() >= min_split
                  and (sea.pitch_key == p).sum() >= min_split]
        coverage = float(arsenal.loc[arsenal.pitch_key.isin(common), "usage"].sum())
        observed, observed_var = np.nan, np.nan
        if common:
            weights = arsenal.set_index("pitch_key").loc[common, "usage"] / coverage
            estimates, influence = {}, {}
            for label, subset in (("high", extreme), ("sea", sea)):
                estimate, contributions = 0.0, []
                for pitch in common:
                    p = subset[subset.pitch_key == pitch]
                    score = float(p.observed_stuff_plus.mean())
                    estimate += weights[pitch] * score
                    contributions.append(pd.Series(weights[pitch] * (p.observed_stuff_plus.to_numpy() - score) / len(p),
                                                   index=p.game_anon_id.to_numpy()))
                residual = pd.concat(contributions).groupby(level=0).sum()
                estimates[label] = estimate
                n_games = len(residual)
                influence[label] = n_games / (n_games - 1) * float((residual ** 2).sum()) if n_games > 1 else np.nan
            observed = estimates["high"] - estimates["sea"]
            observed_var = influence["high"] + influence["sea"]
        reason = (f"Cambio de movimiento estimado: IVB {driver.delta_ivb_in:+.2f} pulgadas; "
                  f"HB lado del brazo {driver.delta_hb_arm_in:+.2f} pulgadas.") if pd.notna(driver.delta_ivb_in) and pd.notna(driver.delta_hb_arm_in) else "Física no disponible en la entrada."
        pitcher_rows.append(dict(zip(KEYS, key), pitches=len(g), games=g.game_anon_id.nunique(),
                                 stuff_harp_helu=g.stuff_a.mean(), stuff_sea_level=g.stuff_b.mean(),
                                 delta_stuff=mean, delta_variance=variance, observed_delta=observed,
                                 observed_variance=observed_var, high_pitches=len(extreme), sea_pitches=len(sea),
                                 split_usage_coverage=coverage, driver_pitch=driver.pitch_key,
                                 driver_family=driver.pitch_family, driver_contribution=driver.weighted_delta,
                                 physical_reason=reason))
    pitchers = _shrink(pd.DataFrame(pitcher_rows), "delta_stuff", "delta_variance", "delta")
    pitchers = _shrink(pitchers, "observed_delta", "observed_variance", "observed")
    league = d.groupby("year").delta_stuff.mean()
    pitchers["league_delta"] = pitchers.year.map(league)
    for source, target in (("delta_eb", "altitude_proof_index"), ("delta_lo", "index_lo"), ("delta_hi", "index_hi")):
        pitchers[target] = 100 + pitchers[source] - pitchers.league_delta
    pitchers["eligible"] = (pitchers.pitches >= min_pitches) & pitchers.altitude_proof_index.notna()
    ranked = pitchers[pitchers.eligible].sort_values(["altitude_proof_index", "pitcher_anon_id", "year"], ascending=[False, True, True])
    # Small cohorts produce fewer than 15 on each side rather than duplicate IDs.
    count = min(15, len(ranked) // 2)
    return {"pitchers": pitchers, "pitches": pd.DataFrame(pitch_rows),
            "top15": ranked.head(count), "bottom15": ranked.tail(count).sort_values("altitude_proof_index") if count else ranked.head(0)}
