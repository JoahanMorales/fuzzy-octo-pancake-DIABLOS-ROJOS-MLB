"""Altitude effect on Stuff+: the same pitch in Harp Helú air vs sea-level air (HACK-015).

Counterfactual: every pitch is moved from the air it was thrown in to a target air with the fitted physics
(``features.shapes.ShapeModel``: per-family proportional effect of ρ on IVB/HB, HACK-004/029), then scored by
the Stuff+ component model (HACK-010) retrained with the altitude-invariant ``pitch_family`` instead of
Trackman's AutoPitchType. ΔStuff+ = Stuff+(ρ_HarpHelú) − Stuff+(ρ = 1), on the park-neutral ruler.

Observed triangulation: for the same ``pitch_key`` (pitcher × season × pitch_id), compare what happened in
Extreme-altitude games with sea-level games; the counterfactual should agree in sign.
"""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
import pandas as pd

from stuffplus.models.stuff import OUTCOMES, STUFF_FEATURES
from stuffplus.physics.translate import proportional_shift

STUFF_FEATURES_INVARIANT = [("pitch_family" if f == "AutoPitchType" else f) for f in STUFF_FEATURES]
FASTBALL_FAMILY = "Four-Seam"


def physics_translator(shape_model) -> Callable:
    """``translate(df, rho_to, rho_from)`` for ``StuffModel``: per-family proportional shift of IVB and arm-side HB.

    The fastball-relative diffs move too: the primary fastball's own movement is shifted with the four-seam ``k``.
    """
    eff = shape_model.rho_effect
    ref = shape_model.rho_ref

    def k_of(fam: pd.Series, comp: str) -> np.ndarray:
        return fam.map(lambda f: eff.get(f, eff.get(FASTBALL_FAMILY, {"ivb": 0.0, "hb": 0.0}))[comp]).to_numpy(float)

    def translate(df: pd.DataFrame, rho_to, rho_from) -> pd.DataFrame:
        out = df.copy()
        fam = out["pitch_family"].astype(str)
        rf = np.broadcast_to(np.asarray(rho_from, float), len(out))
        rt = np.broadcast_to(np.asarray(rho_to, float), len(out))
        k_i, k_h = k_of(fam, "ivb"), k_of(fam, "hb")
        fb = eff.get(FASTBALL_FAMILY, {"ivb": 0.0, "hb": 0.0})
        ivb, hb = out["InducedVertBreak"].to_numpy(float), out["hb_arm"].to_numpy(float)
        new_ivb = proportional_shift(ivb, k_i, rf, rt, ref)
        new_hb = proportional_shift(hb, k_h, rf, rt, ref)
        if "ivb_diff_fb" in out:
            fb_ivb = ivb - out["ivb_diff_fb"].to_numpy(float)
            fb_hb = hb - out["hb_diff_fb"].to_numpy(float)
            out["ivb_diff_fb"] = new_ivb - proportional_shift(fb_ivb, fb["ivb"], rf, rt, ref)
            out["hb_diff_fb"] = new_hb - proportional_shift(fb_hb, fb["hb"], rf, rt, ref)
        sign = np.where(out["PitcherThrows"].astype(str).eq("Right"), 1.0, -1.0) if "PitcherThrows" in out else 1.0
        out["InducedVertBreak"] = new_ivb
        out["hb_arm"] = new_hb
        if "HorzBreak" in out:
            out["HorzBreak"] = new_hb * sign
        out["rho"] = rt.copy()
        return out

    return translate


def counterfactual_scores(df: pd.DataFrame, model, scaler, rho_a: float, rho_b: float = 1.0,
                          rho_from: str = "rho") -> pd.DataFrame:
    """Per pitch: Stuff+ and components in air ``rho_a`` (e.g. Harp Helú) and ``rho_b`` (sea level), and deltas."""
    src = df[rho_from].to_numpy(float)
    ta, tb = model.translate(df, rho_a, src), model.translate(df, rho_b, src)
    a, b = model.predict_components(ta), model.predict_components(tb)
    groups = df[["year"]] if "year" in df else None

    def plus(xrv):
        frame = pd.DataFrame({"x": xrv}, index=df.index)
        if groups is not None and scaler.by == ("year",):
            frame["year"] = groups["year"].to_numpy()
        return scaler.transform(frame, "x").to_numpy() if groups is not None else np.array([scaler.scale_value(v) for v in xrv])

    out = pd.DataFrame(index=df.index)
    out["stuff_a"], out["stuff_b"] = plus(a["xrv"].to_numpy()), plus(b["xrv"].to_numpy())
    out["delta_stuff"] = out["stuff_a"] - out["stuff_b"]
    for o in OUTCOMES:
        out[f"delta_p_{o}"] = a[f"p_{o}"].to_numpy() - b[f"p_{o}"].to_numpy()
    out["delta_contact_rv"] = a["contact_rv"].to_numpy() - b["contact_rv"].to_numpy()
    out["ivb_a"], out["ivb_b"] = ta["InducedVertBreak"].to_numpy(), tb["InducedVertBreak"].to_numpy()
    out["hb_a"], out["hb_b"] = ta["hb_arm"].to_numpy(), tb["hb_arm"].to_numpy()
    return out


def cluster_bootstrap_mean(values: pd.Series, clusters: pd.Series, n_boot: int = 500, seed: int = 2240) -> tuple[float, float, float]:
    """Mean and 95 % CI resampling whole clusters (pitchers), not single pitches."""
    v = values.to_numpy(float)
    codes = pd.factorize(clusters)[0]
    k = codes.max() + 1
    sums = np.bincount(codes, weights=v, minlength=k)
    cnts = np.bincount(codes, minlength=k).astype(float)
    if k < 2:
        return float(v.mean()), np.nan, np.nan
    w = np.random.default_rng(seed).multinomial(k, np.full(k, 1 / k), size=n_boot)
    boot = (w @ sums) / (w @ cnts)
    return float(v.mean()), float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))


def delta_table(scores: pd.DataFrame, df: pd.DataFrame, by: str, n_boot: int = 500, min_n: int = 200) -> pd.DataFrame:
    """ΔStuff+ and component deltas by ``by`` (shape or pitch_family) with pitcher-cluster CIs."""
    rows = []
    for key, idx in df.groupby(by, observed=True).groups.items():
        if len(idx) < min_n:
            continue
        s, d = scores.loc[idx], df.loc[idx]
        m, lo, hi = cluster_bootstrap_mean(s["delta_stuff"], d["pitcher_anon_id"], n_boot)
        rows.append({
            by: key, "pitches": len(idx), "pitchers": d["pitcher_anon_id"].nunique(),
            "stuff_sea_level": s["stuff_b"].mean(), "stuff_harp_helu": s["stuff_a"].mean(),
            "delta_stuff": m, "delta_lo": lo, "delta_hi": hi,
            "delta_ivb_in": (s["ivb_a"] - s["ivb_b"]).mean(), "delta_hb_arm_in": (s["hb_a"] - s["hb_b"]).mean(),
            "delta_whiff_pct": 100 * s["delta_p_whiff"].mean(), "delta_called_strike_pct": 100 * s["delta_p_called_strike"].mean(),
            "delta_in_play_pct": 100 * s["delta_p_in_play"].mean(), "delta_contact_runs": s["delta_contact_rv"].mean(),
        })
    out = pd.DataFrame(rows).sort_values("delta_stuff", ascending=False).reset_index(drop=True)
    avg = float(scores["delta_stuff"].mean())
    out["relative_to_league"] = out["delta_stuff"] - avg
    out["verdict"] = np.where(out["delta_lo"] - avg > 0, "gana relativo", np.where(out["delta_hi"] - avg < 0, "pierde relativo", "neutral"))
    out["physics"] = out.apply(explain, axis=1)
    return out


def explain(row: pd.Series) -> str:
    """One Spanish sentence with the physical reason, from the component deltas."""
    move = abs(row["delta_ivb_in"]) + abs(row["delta_hb_arm_in"])
    why = "menos efecto Magnus le quita movimiento" if move >= 1.0 else "su movimiento casi no depende del aire"
    damage = "y el contacto hace más daño" if row["delta_contact_runs"] > 0.002 else "y el contacto no empeora"
    return (f"En aire de CDMX {why} (IVB {row['delta_ivb_in']:+.1f}\", HB {row['delta_hb_arm_in']:+.1f}\", "
            f"whiff {row['delta_whiff_pct']:+.1f} pp) {damage} ({row['delta_contact_runs']:+.3f} carreras por batazo).")


def within_pitcher_observed(df: pd.DataFrame, cols: Sequence[str], by: str = "pitch_family", key: str = "pitch_key",
                            min_n: int = 30, n_boot: int = 500) -> pd.DataFrame:
    """Extreme − No Altitude differences of ``cols`` within the same pitch (pitch_key), averaged by ``by``."""
    alt = df["altitude_category"].astype(str)
    d = df[alt.isin(["No Altitude", "Extreme Altitude"])]
    n = d.groupby([key, d["altitude_category"].astype(str)]).size().unstack(fill_value=0)
    keep = n.index[(n.get("No Altitude", 0) >= min_n) & (n.get("Extreme Altitude", 0) >= min_n)]
    d = d[d[key].isin(keep)]
    means = d.groupby([key, d["altitude_category"].astype(str)])[list(cols)].mean().unstack()
    rows = []
    meta = d.groupby(key).agg(group=(by, "first"), pitcher=("pitcher_anon_id", "first"))
    for c in cols:
        diff = (means[(c, "Extreme Altitude")] - means[(c, "No Altitude")]).rename("diff")
        t = meta.join(diff)
        for g, sub in t.groupby("group"):
            m, lo, hi = cluster_bootstrap_mean(sub["diff"], sub["pitcher"], n_boot)
            rows.append({by: g, "metric": c, "pitches_compared": len(sub), "extreme_minus_no": m, "lo": lo, "hi": hi})
    return pd.DataFrame(rows)


def altitude_curve(df: pd.DataFrame, model, scaler, by: str, rhos: Sequence[float] = (1.0, 0.95, 0.9, 0.85, 0.819, 0.8),
                   sample: int | None = 60_000, seed: int = 2240) -> pd.DataFrame:
    """Mean Stuff+ by ``by`` as the air thins (one row per group × ρ)."""
    d = df.sample(n=min(sample, len(df)), random_state=seed) if sample else df
    rows = []
    for r in rhos:
        sc = counterfactual_scores(d, model, scaler, rho_a=r, rho_b=1.0)
        g = sc.groupby(d[by].astype(str))
        rows.append(pd.DataFrame({by: g.size().index, "rho": r, "stuff_plus": g["stuff_a"].mean().to_numpy(),
                                  "delta_vs_sea_level": g["delta_stuff"].mean().to_numpy()}))
    return pd.concat(rows, ignore_index=True)
