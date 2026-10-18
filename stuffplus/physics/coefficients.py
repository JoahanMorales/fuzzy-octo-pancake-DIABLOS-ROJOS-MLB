"""Aerodynamic coefficients per pitch and what explains the lift gap at altitude (HACK-041).

From Trackman's 9-parameter fit (``aero.decompose``): drag and Magnus accelerations → C_D and C_L with the game's
air density; spin parameter S = Rω/v (Nathan, Hopkins, Chong & Kaczmarski 2006) and Reynolds number
Re = ρ v D / μ (Smith & Sciacchitano 2022). The per-game density ρ̂ is calibrated on fastball drag, so C_D of
fastballs is ~constant across parks BY CONSTRUCTION; the questions are:

1. Does a lower spin parameter at altitude explain the lower C_L (literature hypothesis)? ``gap_decomposition``.
2. Is ρ̂ biased because C_D itself depends on Re (drag crisis), i.e. is the true density lower than ρ̂?
   Evidence: slower pitches (lower Re) show higher C_D in thin air; the barometric density of the Harp Helú
   (``RHO_HARP_HELU_BAROMETRIC``) is below the drag-calibrated ``RHO_HARP_HELU``.
3. How strongly does Magnus acceleration scale with air density within the same pitch? ``magnus_elasticity``
   (physics with constant C_L predicts 1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .aero import decompose
from .constants import BALL_RADIUS_M, FT_TO_M, RHO_SI_SEA_LEVEL, RPM_TO_RADS

AIR_VISCOSITY = 1.81e-5  # Pa·s, ~15-25 °C (temperature is not in the data)
VALID = {"cd": (0.05, 1.0), "cl": (0.0, 0.8), "S": (0.05, 0.6)}


def coefficients(df: pd.DataFrame, rho_col: str = "rho") -> pd.DataFrame:
    """Per pitch: C_D, C_L (with the game's ρ̂), spin parameter S, Reynolds number, accelerations; invalid rows NaN."""
    rho = df[rho_col].to_numpy(float)
    a = decompose(df, rho=rho)
    v_ms = a["speed_fps"].to_numpy(float) * FT_TO_M
    out = a[["speed_fps", "drag_acc", "magnus_acc", "cd", "cl"] + (["spin_eff"] if "spin_eff" in a else [])].copy()
    out["S"] = BALL_RADIUS_M * df["SpinRate"].to_numpy(float) * RPM_TO_RADS / v_ms
    out["Re"] = RHO_SI_SEA_LEVEL * rho * v_ms * 2 * BALL_RADIUS_M / AIR_VISCOSITY
    for col, (lo, hi) in VALID.items():
        out.loc[~out[col].between(lo, hi), col] = np.nan
    return out


def _boot(values: pd.Series, groups: pd.Series, stat, n_boot: int = 300, seed: int = 2240):
    codes = pd.factorize(groups)[0]
    rng = np.random.default_rng(seed)
    n = codes.max() + 1
    idx_by = pd.Series(np.arange(len(codes))).groupby(codes).apply(np.array).to_list()
    vals = []
    for _ in range(n_boot):
        pick = np.concatenate([idx_by[i] for i in rng.integers(0, n, n)])
        vals.append(stat(values.iloc[pick]))
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def bucket_table(d: pd.DataFrame, n_boot: int = 200) -> pd.DataFrame:
    """Median C_D, C_L, S, Re by pitch family × altitude bucket, with pitcher-cluster CIs on C_L and C_D."""
    rows = []
    for (fam, b), g in d.groupby([d.pitch_family.astype(str), d.altitude_category.astype(str)], observed=True):
        g = g.dropna(subset=["cd", "cl", "S"])
        if len(g) < 200:
            continue
        lo, hi = _boot(g.cl, g.pitcher_anon_id, np.median, n_boot)
        cd_lo, cd_hi = _boot(g.cd, g.pitcher_anon_id, np.median, n_boot)
        rows.append(dict(pitch_family=fam, bucket=b, pitches=len(g), rho=g.rho.median(), cd=g.cd.median(),
                         cd_lo=cd_lo, cd_hi=cd_hi,
                         cl=g.cl.median(), cl_lo=lo, cl_hi=hi, S=g.S.median(), Re=g.Re.median(),
                         spin=g.SpinRate.median(), velo=g.RelSpeed.median()))
    return pd.DataFrame(rows)


def gap_decomposition(t: pd.DataFrame, cl_slope_s: float, rho_true_over_hat: float,
                      a: str = "No Altitude", b: str = "Extreme Altitude") -> pd.DataFrame:
    """C_L ratio (b vs a) per family split into: the spin-parameter shift (slope × ΔS), the density bias
    (C_L computed with ρ̂ is low by ρ_true/ρ̂ when the true density is lower), and the unexplained residual."""
    rows = []
    for fam, g in t.groupby("pitch_family"):
        g = g.set_index("bucket")
        if a not in g.index or b not in g.index:
            continue
        ra, rb = g.loc[a], g.loc[b]
        ratio = rb.cl / ra.cl
        s_part = 1 + cl_slope_s * (rb.S - ra.S) / ra.cl
        rho_part = rho_true_over_hat  # cl_hat = cl_true × ρ_true/ρ̂
        rows.append(dict(pitch_family=fam, cl_ratio=ratio, gap_pct=100 * (ratio - 1),
                         explained_by_spin_param_pct=100 * (s_part - 1), explained_by_density_bias_pct=100 * (rho_part - 1),
                         residual_pct=100 * (ratio / (s_part * rho_part) - 1)))
    return pd.DataFrame(rows)


SHS_SPLIT = 0.1  # Sawicki, Hubbard & Stronge (2003): C_L = 1.5 S below S = 0.1, a + b S above
SHS_LITERATURE = (0.09, 0.6)


def cl_vs_s(d: pd.DataFrame, family: str = "Four-Seam", bucket: str = "No Altitude", n_boot: int = 200) -> dict:
    """C_L(S) in the SHS form: fixed 1.5 S below S = 0.1 and a least-squares line a + b S above, fitted on one
    family/bucket, with a pitcher-cluster CI on b. S uses total spin, so gyro spin dilutes the slope."""
    g = d[(d.pitch_family.astype(str) == family) & (d.altitude_category.astype(str) == bucket)].dropna(subset=["cl", "S"])
    hi = g[g.S >= SHS_SPLIT]
    line = lambda x: np.polyfit(x.S.to_numpy(float), x.cl.to_numpy(float), 1)
    b, a = line(hi)
    lo_b, hi_b = _boot(hi, hi.pitcher_anon_id, lambda x: float(line(x)[0]), n_boot)
    return dict(family=family, bucket=bucket, a=float(a), b=float(b), b_lo=lo_b, b_hi=hi_b, n_above=len(hi),
                n_below=int((g.S < SHS_SPLIT).sum()), a_literature=SHS_LITERATURE[0], b_literature=SHS_LITERATURE[1])


def shs_cl(S, a: float, b: float) -> np.ndarray:
    S = np.asarray(S, float)
    return np.where(S < SHS_SPLIT, 1.5 * S, a + b * S)


def cd_vs_re(d: pd.DataFrame, n_boot: int = 200, min_n: int = 500) -> pd.DataFrame:
    """C_D(Re) by family x altitude bucket: least-squares slope of C_D on Re (per 10^5) with a pitcher-cluster CI.
    A negative slope inside a bucket is the drag-crisis signature (C_D falls as Re grows)."""
    rows = []
    for (fam, b), g in d.dropna(subset=["cd", "Re"]).groupby([d.pitch_family.astype(str), d.altitude_category.astype(str)],
                                                             observed=True):
        if len(g) < min_n:
            continue
        fit = lambda x: np.polyfit(x.Re.to_numpy(float) / 1e5, x.cd.to_numpy(float), 1)
        slope, icpt = fit(g)
        lo, hi = _boot(g, g.pitcher_anon_id, lambda x: float(fit(x)[0]), n_boot)
        rows.append(dict(pitch_family=fam, bucket=b, pitches=len(g), slope_per_1e5=float(slope), slope_lo=lo, slope_hi=hi,
                         intercept=float(icpt), re_p10=float(g.Re.quantile(0.1)), re_p90=float(g.Re.quantile(0.9)),
                         cd_median=float(g.cd.median())))
    return pd.DataFrame(rows)


def efficient_pitches(d: pd.DataFrame, key: str = "pitch_key", bucket: str = "No Altitude", min_eff: float | None = 0.95,
                      min_pitches: int = 30, top_share: float = 0.10) -> tuple[set, pd.Series, float]:
    """Pitch identities whose median spin efficiency is >= ``min_eff`` in ``bucket`` games (or, with
    ``min_eff=None``, the most efficient ``top_share`` of identities), measured on the selection half only
    (odd-numbered games of that identity), so the other half can test them without selecting on the same noise.
    Returns (identities, mask of the held-out rows: every non-selection game of those pitches, threshold used)."""
    g = d[d.altitude_category.astype(str) == bucket].dropna(subset=["spin_eff"])
    order = g.groupby(key, observed=True)["game_anon_id"].transform(lambda s: pd.factorize(s)[0])
    sel = g[order % 2 == 1]
    med = sel.groupby(key, observed=True).spin_eff.agg(["median", "size"])
    med = med[med["size"] >= min_pitches]
    thr = float(med["median"].quantile(1 - top_share)) if min_eff is None else float(min_eff)
    keep = set(med[med["median"] >= thr].index)
    sel_games = set(zip(sel[key], sel.game_anon_id))
    in_keep = d[key].isin(keep)
    held_out = in_keep & ~pd.Series(list(zip(d[key], d.game_anon_id)), index=d.index).isin(sel_games)
    return keep, held_out, thr


def magnus_elasticity(d: pd.DataFrame, key: str = "pitch_key", min_games: int = 3, n_boot: int = 300) -> pd.DataFrame:
    """Within the same pitch (pitcher × season × pitch identity), slope of log Magnus acceleration on log ρ̂ across
    games, by family, with pitcher-cluster CIs. Constant C_L ⇒ 1; > 1 ⇒ lift falls faster than the density."""
    g = d.dropna(subset=["magnus_acc"]).copy()
    g = g[g.magnus_acc > 0]
    g["lm"], g["lr"] = np.log(g.magnus_acc), np.log(g.rho)
    gm = g.groupby([key, "game_anon_id"], observed=True).agg(lm=("lm", "mean"), lr=("lr", "first"),
                                                           fam=("pitch_family", "first"), pit=("pitcher_anon_id", "first"))
    gm = gm.reset_index()
    n_games = gm.groupby(key)["game_anon_id"].transform("size")
    gm = gm[n_games >= min_games].copy()
    gm["lm_c"] = gm.lm - gm.groupby(key).lm.transform("mean")
    gm["lr_c"] = gm.lr - gm.groupby(key).lr.transform("mean")
    rows = []
    for fam, f in gm.groupby(gm.fam.astype(str)):
        if f.lr_c.var() == 0 or len(f) < 50:
            continue
        slope = lambda x: float((x.lm_c * x.lr_c).sum() / (x.lr_c ** 2).sum())
        lo, hi = _boot(f, f.pit, slope, n_boot)
        rows.append(dict(pitch_family=fam, elasticity=slope(f), lo=lo, hi=hi, pitch_games=len(f), pitches=f[key].nunique()))
    return pd.DataFrame(rows)
