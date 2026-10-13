"""Ideal physical profile for Diablos Rojos: what maximizes Stuff+ at 2,240 m (HACK-017).

Every function takes the fitted Stuff+ pieces as arguments (``model`` with ``translate`` + ``predict_components``,
a ``PlusScaler``), so it works with HACK-010's ``StuffModel`` and HACK-015's physics translation alike.

The air reaches a pitch through two paths, and the analysis keeps both:

1. **physics** (main): the same release thrown in thinner air moves less (Magnus ∝ ρ). Profiles are stored with
   their movement *at sea level* (``rho = 1``) and ``model.translate`` moves them to the target ρ before scoring;
2. **direct**: the model's own ``rho`` feature (secondary; SHAP interaction of a distilled booster).

Search stays inside the observed data: PDP grids span the 5–95 % quantiles and candidate profiles are observed
pitcher-season centroids filtered by kNN density (no free optimization outside the hull).
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from stuffplus.config import SEED

FASTBALL_FAMILIES = ("Four-Seam", "Sinker")
# a pitch's own movement and its difference to the pitcher's primary fastball move together
LINKED_DIFF = {"RelSpeed": "velo_diff_fb", "InducedVertBreak": "ivb_diff_fb", "hb_arm": "hb_diff_fb"}
PROFILE_FEATURES = ["RelSpeed", "InducedVertBreak", "hb_arm", "SpinRate", "spin_axis_arm", "Extension",
                    "RelHeight", "rel_side_arm", "arm_angle"]
DIFF_FEATURES = ["velo_diff_fb", "ivb_diff_fb", "hb_diff_fb"]
LABELS = {"RelSpeed": "velocidad (mph)", "InducedVertBreak": "IVB (in)", "hb_arm": "HB lado del brazo (in)",
          "SpinRate": "giro (rpm)", "spin_axis_arm": "eje de giro (°)", "Extension": "extensión (ft)",
          "RelHeight": "altura de salida (ft)", "rel_side_arm": "salida lateral (ft)", "arm_angle": "ángulo de brazo (°)"}


# ---------------------------------------------------------------- scoring
def to_sea_level(model, df: pd.DataFrame) -> pd.DataFrame:
    """Same pitches with their movement translated to sea-level air (``rho = 1``)."""
    return model.translate(df, 1.0, df["rho"].to_numpy(float))


def stuff_plus_at(model, scaler, frame: pd.DataFrame, rho: float) -> np.ndarray:
    """Stuff+ of ``frame`` (movement at sea level) thrown in air ``rho``, on the park-neutral reference scale."""
    t = model.translate(frame, rho, frame["rho"].to_numpy(float))
    x = model.predict_components(t)["xrv"].to_numpy(float)
    if scaler.by and all(c in frame for c in scaler.by):
        return scaler.transform(frame[list(scaler.by)].assign(x=x), "x").to_numpy(float)
    return np.array([scaler.scale_value(v) for v in x])


def is_fastball(frame: pd.DataFrame) -> pd.Series:
    return frame["pitch_family"].astype(str).isin(FASTBALL_FAMILIES)


# ---------------------------------------------------------------- partial dependence feature × ρ
def set_feature(frame: pd.DataFrame, feature: str, value: float) -> pd.DataFrame:
    """Set ``feature`` to ``value``; for secondaries the matching fastball diff moves by the same amount."""
    out = frame.copy()
    delta = value - out[feature].to_numpy(float)
    out[feature] = value
    diff = LINKED_DIFF.get(feature)
    if diff is not None and diff in out:
        sec = ~is_fastball(out).to_numpy()
        out.loc[sec, diff] = out.loc[sec, diff].to_numpy(float) + delta[sec]
    return out


def pdp_2d(model, scaler, base: pd.DataFrame, features: Sequence[str], rhos: Sequence[float],
           n_grid: int = 9, q: tuple[float, float] = (0.05, 0.95)) -> pd.DataFrame:
    """Mean Stuff+ over ``base`` (sea-level movement) with one feature fixed on a grid, thrown at each ρ."""
    rows = []
    for f in features:
        grid = np.linspace(*base[f].quantile(list(q)).to_numpy(float), n_grid)
        for v in grid:
            framed = set_feature(base, f, float(v))
            for rho in rhos:
                rows.append({"feature": f, "value": float(v), "rho": float(rho),
                             "stuff_plus": float(np.mean(stuff_plus_at(model, scaler, framed, rho)))})
    return pd.DataFrame(rows)


def rho_sensitivity(pdp: pd.DataFrame, rho_alt: float, rho_sea: float = 1.0, tol: float = 0.10) -> pd.DataFrame:
    """Per feature: Stuff+ slope per unit and p5→p95 swing at sea level vs altitude, and the verdict."""
    rows = []
    for f, g in pdp.groupby("feature", sort=False):
        out = {"feature": f, "label": LABELS.get(f, f)}
        for tag, rho in (("sea", rho_sea), ("alt", rho_alt)):
            s = g[np.isclose(g["rho"], rho)].sort_values("value")
            out[f"slope_{tag}"] = float(np.polyfit(s["value"], s["stuff_plus"], 1)[0]) if len(s) > 1 else np.nan
            out[f"swing_{tag}"] = float(s["stuff_plus"].iloc[-1] - s["stuff_plus"].iloc[0]) if len(s) else np.nan
        out["swing_change"] = abs(out["swing_alt"]) - abs(out["swing_sea"])
        base = max(abs(out["swing_sea"]), 1e-9)
        rel = out["swing_change"] / base
        out["swing_change_rel"] = rel
        out["verdict"] = "importa más en altitud" if rel > tol else "importa menos en altitud" if rel < -tol else "igual"
        rows.append(out)
    return pd.DataFrame(rows).sort_values("swing_change", ascending=False, key=np.abs).reset_index(drop=True)


def h_statistic(pdp: pd.DataFrame) -> pd.DataFrame:
    """Friedman's H² of feature × ρ on the PDP grid (0 = additive; share of the joint PD variance from the interaction)."""
    rows = []
    for f, g in pdp.groupby("feature", sort=False):
        t = g.pivot_table(index="value", columns="rho", values="stuff_plus")
        jk = t - t.to_numpy().mean()
        j = t.mean(axis=1) - t.to_numpy().mean()
        k = t.mean(axis=0) - t.to_numpy().mean()
        inter = jk.to_numpy() - j.to_numpy()[:, None] - k.to_numpy()[None, :]
        den = float((jk.to_numpy() ** 2).sum())
        rows.append({"feature": f, "h2_rho": float((inter ** 2).sum() / den) if den > 0 else 0.0})
    return pd.DataFrame(rows)


def shap_rho_interaction(booster, X: pd.DataFrame, points_per_xrv: float) -> pd.DataFrame:
    """Mean |SHAP interaction| of each feature with ``rho`` (direct path only), in Stuff+ points."""
    import shap

    iv = shap.TreeExplainer(booster).shap_interaction_values(X)
    cols = list(X.columns)
    r = cols.index("rho")
    main = np.abs(np.einsum("nii->ni", iv)).mean(axis=0)
    with_rho = 2 * np.abs(iv[:, :, r]).mean(axis=0)
    out = pd.DataFrame({"feature": cols, "main_pts": main * points_per_xrv, "rho_interaction_pts": with_rho * points_per_xrv})
    return out[out.feature != "rho"].sort_values("rho_interaction_pts", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- binned counterfactual (traits outside the model)
def cluster_bootstrap_ci(values: np.ndarray, clusters: np.ndarray, n_boot: int = 300, seed: int = SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    ids, inv = np.unique(clusters, return_inverse=True)
    sums = np.bincount(inv, weights=values)
    counts = np.bincount(inv)
    draws = rng.integers(0, len(ids), size=(n_boot, len(ids)))
    means = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def delta_by_bins(delta: pd.Series, trait: pd.Series, clusters: pd.Series, n_bins: int = 5,
                  n_boot: int = 300, name: str | None = None) -> pd.DataFrame:
    """Mean counterfactual ΔStuff+ by quantile bin of a trait, with a pitcher-cluster bootstrap CI."""
    ok = delta.notna() & trait.notna()
    bins = pd.qcut(trait[ok], n_bins, duplicates="drop")
    rows = []
    for b, idx in delta[ok].groupby(bins, observed=True).groups.items():
        v, c = delta.loc[idx].to_numpy(float), clusters.loc[idx].astype(str).to_numpy()
        lo, hi = cluster_bootstrap_ci(v, c, n_boot)
        rows.append({"trait": name or trait.name, "bin_lo": float(b.left), "bin_hi": float(b.right), "pitches": len(v),
                     "pitchers": len(np.unique(c)), "delta_stuff": float(v.mean()), "delta_lo": lo, "delta_hi": hi})
    return pd.DataFrame(rows)


def vaa_adjusted(frame: pd.DataFrame) -> pd.Series:
    """Vertical approach angle net of plate height (VAA depends on where the pitch ends; residual within family)."""
    out = pd.Series(np.nan, index=frame.index, name="vaa_adj")
    for _, g in frame.groupby(frame["pitch_family"].astype(str)):
        g = g[["VertApprAngle", "PlateLocHeight"]].dropna()
        if len(g) < 10:
            continue
        b, a = np.polyfit(g["PlateLocHeight"], g["VertApprAngle"], 1)
        out.loc[g.index] = g["VertApprAngle"] - (a + b * g["PlateLocHeight"])
    return out


# ---------------------------------------------------------------- candidates inside the data hull
def centroids(frame: pd.DataFrame, keys: Sequence[str] = ("pitcher_anon_id", "year", "pitch_family"),
              min_n: int = 50) -> pd.DataFrame:
    """Observed profiles: mean physical traits per pitcher-season-pitch (sea-level movement), with usage."""
    num = [c for c in PROFILE_FEATURES + DIFF_FEATURES + ["is_rhp"] if c in frame]
    g = frame.groupby(list(keys), observed=True)
    out = g[num].mean()
    out["n"] = g.size()
    out = out[out["n"] >= min_n].reset_index().dropna(subset=[c for c in PROFILE_FEATURES if c in out])
    out["usage"] = out["n"] / out.groupby(["pitcher_anon_id", "year"])["n"].transform("sum")
    out["is_rhp"] = out["is_rhp"].round().astype(int)
    out["rho"] = 1.0
    return out


def knn_in_hull(X: np.ndarray, ref: np.ndarray | None = None, k: int = 10, keep: float = 0.9) -> np.ndarray:
    """True where a profile lies in the dense part of the reference cloud (mean distance to k neighbours ≤ quantile)."""
    from sklearn.neighbors import NearestNeighbors

    ref = X if ref is None else ref
    mu, sd = ref.mean(axis=0), ref.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    R, Q = (ref - mu) / sd, (X - mu) / sd
    k = max(1, min(k, len(R) - 1))
    nn = NearestNeighbors(n_neighbors=k + 1).fit(R)
    ref_d = nn.kneighbors(R)[0][:, 1:].mean(axis=1)  # skip self
    q_d = nn.kneighbors(Q, n_neighbors=k)[0].mean(axis=1)
    return q_d <= np.quantile(ref_d, keep)


def score_profiles(model, scaler, profiles: pd.DataFrame, rho_alt: float) -> pd.DataFrame:
    out = profiles.copy()
    out["stuff_sea"] = stuff_plus_at(model, scaler, out, 1.0)
    out["stuff_alt"] = stuff_plus_at(model, scaler, out, rho_alt)
    out["delta"] = out["stuff_alt"] - out["stuff_sea"]
    return out


def best_fastballs(model, scaler, cents: pd.DataFrame, rho_alt: float, top: int = 10) -> tuple[pd.DataFrame, dict]:
    """Observed primary-fastball profiles inside the hull, ranked by Stuff+ in thin air; agreement with sea level."""
    fb = cents[cents["pitch_family"].astype(str).isin(FASTBALL_FAMILIES)].copy()
    feats = [c for c in PROFILE_FEATURES if c in fb]
    fb = fb[knn_in_hull(fb[feats].to_numpy(float))]
    fb = score_profiles(model, scaler, fb, rho_alt)
    fb["rank_alt"] = fb["stuff_alt"].rank(ascending=False)
    fb["rank_sea"] = fb["stuff_sea"].rank(ascending=False)
    top_alt = set(fb.nsmallest(top, "rank_alt").index)
    top_sea = set(fb.nsmallest(top, "rank_sea").index)
    stats = {"candidates": int(len(fb)), "spearman_alt_vs_sea": float(fb["stuff_alt"].corr(fb["stuff_sea"], method="spearman")),
             "top_overlap": len(top_alt & top_sea), "top": top}
    return fb.sort_values("stuff_alt", ascending=False), stats


def secondaries_given_fastball(model, scaler, cents: pd.DataFrame, fastball: pd.Series, rho_alt: float) -> pd.DataFrame:
    """Each observed secondary profile re-anchored on ``fastball``; kept only if (traits + diffs) stay in the hull."""
    sec = cents[~cents["pitch_family"].astype(str).isin(FASTBALL_FAMILIES)].copy()
    ref = sec[PROFILE_FEATURES + DIFF_FEATURES].dropna().to_numpy(float)  # pitchers without a primary fastball have no diffs
    sec["velo_diff_fb"] = sec["RelSpeed"] - fastball["RelSpeed"]
    sec["ivb_diff_fb"] = sec["InducedVertBreak"] - fastball["InducedVertBreak"]
    sec["hb_diff_fb"] = sec["hb_arm"] - fastball["hb_arm"]
    sec = sec[(sec["is_rhp"] == int(fastball["is_rhp"])) & knn_in_hull(sec[PROFILE_FEATURES + DIFF_FEATURES].to_numpy(float), ref)]
    return score_profiles(model, scaler, sec, rho_alt).sort_values("stuff_alt", ascending=False)


def best_arsenals(scored: pd.DataFrame, n_pitches: int = 3) -> pd.DataFrame:
    """Observed arsenals: the pitcher-season's ``n_pitches`` most used families, usage-weighted Stuff+ at each air."""
    rows = []
    for (pid, year), g in scored.groupby(["pitcher_anon_id", "year"], observed=True):
        g = g.nlargest(n_pitches, "usage")
        if len(g) < n_pitches or not g["pitch_family"].astype(str).isin(FASTBALL_FAMILIES).any():
            continue
        w = g["usage"] / g["usage"].sum()
        rows.append({"pitcher_anon_id": pid, "year": year,
                     "arsenal": " + ".join(sorted(g["pitch_family"].astype(str))),
                     "stuff_sea": float((w * g["stuff_sea"]).sum()), "stuff_alt": float((w * g["stuff_alt"]).sum())})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["delta"] = out["stuff_alt"] - out["stuff_sea"]
    out["rank_alt"] = out["stuff_alt"].rank(ascending=False)
    out["rank_sea"] = out["stuff_sea"].rank(ascending=False)
    return out.sort_values("stuff_alt", ascending=False).reset_index(drop=True)
