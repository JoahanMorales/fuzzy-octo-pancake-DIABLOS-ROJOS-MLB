"""Rasgos de arsenal: diferencias contra la recta principal, uso, tamaño/dispersión del arsenal y tunneling.

Convención de ejes de las columnas `PitchTrajectory*` (verificada contra y0/vy0/ay0 y PlateLoc*):
**X = hacia el plato** (Xc0 ≈ 54 ft, Xc1 ≈ −128 ft/s), **Y = vertical**, **Z = lateral**; pos(t)=c0+c1·t+c2·t² (c2 = a/2).
Mano: HorzBreak, RelSide y SpinAxis se espejan para zurdos (positivo = lado del brazo) para poder comparar manos.

Sin fuga: `fit_arsenal(train)` aprende solo de lanzamientos propios (uso, recta principal); `transform` usa la
recta principal *del mismo juego* para comparar bajo el mismo aire (rasgos físicos, nunca resultados).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

KEYS = ["pitcher_anon_id", "year"]
FASTBALL_FAMILIES = ("Four-Seam", "Sinker", "Cutter")
DECISION_Y_FT = 23.8  # distancia al plato del punto de decisión del bateador
MIN_GAME_FB = 3  # recta principal en el juego: mínimo para usar el promedio del juego
ARSENAL_MIN_USAGE = 0.05
TRAJ = ["PitchTrajectoryXc0", "PitchTrajectoryXc1", "PitchTrajectoryXc2", "PitchTrajectoryYc0", "PitchTrajectoryYc1",
        "PitchTrajectoryYc2", "PitchTrajectoryZc0", "PitchTrajectoryZc1", "PitchTrajectoryZc2"]
REF_COLS = ["RelSpeed", "ivb", "hb", "SpinRate", "axis"] + TRAJ


def _sign(df: pd.DataFrame) -> np.ndarray:
    return np.where(df["PitcherThrows"].astype(str).str.startswith("L"), -1.0, 1.0)


def with_arm_side(df: pd.DataFrame) -> pd.DataFrame:
    """Añade `ivb`, `hb` y `axis` espejados por mano (hb>0 = lado del brazo; eje de giro de zurdos → 360−eje)."""
    out = df.copy()
    s = _sign(df)
    out["ivb"] = df["InducedVertBreak"].astype(float)
    out["hb"] = df["HorzBreak"].astype(float) * s
    ax = df["SpinAxis"].astype(float)
    out["axis"] = np.where(s < 0, 360.0 - ax, ax) % 360.0
    return out


def primary_fastball(df: pd.DataFrame) -> pd.Series:
    """`pitch_id` de la recta más usada por (pitcher, temporada); índice = (pitcher, year). Sin rectas → ausente."""
    fb = df[df["pitch_family"].isin(FASTBALL_FAMILIES) & (df["pitch_id"] >= 0)]
    cnt = fb.groupby(KEYS + ["pitch_id"]).size().rename("n").reset_index()
    best = cnt.sort_values("n", ascending=False).drop_duplicates(KEYS).set_index(KEYS)["pitch_id"]
    return best.rename("primary_fb_id")


def _circ_diff(a, b):
    return (np.asarray(a, float) - np.asarray(b, float) + 180.0) % 360.0 - 180.0


def trajectory_at(d: pd.DataFrame, x_ft: float, prefix: str = "") -> pd.DataFrame:
    """Posición lateral/vertical (ft) cuando la pelota está a `x_ft` del plato, desde los polinomios."""
    c0, c1, c2 = (d[prefix + f"PitchTrajectoryXc{i}"].to_numpy(float) for i in range(3))
    disc = np.sqrt(np.maximum(c1**2 - 4 * c2 * (c0 - x_ft), 0.0))
    t = 2 * (c0 - x_ft) / (-c1 + disc)  # raíz positiva menor; estable si c2→0
    pos = lambda a: d[prefix + f"PitchTrajectory{a}c0"].to_numpy(float) + d[prefix + f"PitchTrajectory{a}c1"].to_numpy(float) * t + d[prefix + f"PitchTrajectory{a}c2"].to_numpy(float) * t**2
    return pd.DataFrame({"lat": pos("Z"), "vert": pos("Y")}, index=d.index)


@dataclass
class ArsenalModel:
    primary: pd.Series  # (pitcher, year) -> pitch_id
    ref: pd.DataFrame  # (pitcher, year) -> medias de la recta principal (temporada)
    usage: pd.Series  # (pitcher, year, pitch_id) -> % de uso
    size: pd.Series  # (pitcher, year) -> nº de pitch_id con ≥5 % de uso
    spread: pd.DataFrame  # (pitcher, year) -> sd de ivb/hb entre pitch_id (promedios)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        d = with_arm_side(df)
        idx = pd.MultiIndex.from_frame(d[KEYS])
        d["primary_fb_id"] = self.primary.reindex(idx).to_numpy()
        is_prim = d["pitch_id"].to_numpy() == d["primary_fb_id"].to_numpy()
        # referencia del juego: medias de la recta principal de ese pitcher en ese juego
        gk = KEYS + ["game_anon_id"]
        gref = d[is_prim].groupby(gk)[REF_COLS].agg("mean")
        gn = d[is_prim].groupby(gk).size().rename("_n")
        gref = gref.join(gn)
        gref.loc[gref["_n"] < MIN_GAME_FB, REF_COLS] = np.nan
        ref = gref[REF_COLS].reindex(pd.MultiIndex.from_frame(d[gk])).set_axis(d.index)
        ref_season = self.ref.reindex(idx).set_axis(d.index)
        same_game = ref["RelSpeed"].notna()
        ref = ref.fillna(ref_season)
        d["fb_ref_same_game"] = same_game.astype(int)
        d["velo_diff_vs_fb"] = d["RelSpeed"] - ref["RelSpeed"]
        d["ivb_diff_vs_fb"] = d["ivb"] - ref["ivb"]
        d["hb_diff_vs_fb"] = d["hb"] - ref["hb"]
        d["spin_diff_vs_fb"] = d["SpinRate"] - ref["SpinRate"]
        d["axis_diff_vs_fb"] = _circ_diff(d["axis"], ref["axis"])
        key = pd.MultiIndex.from_frame(d[KEYS + ["pitch_id"]])
        d["pitch_usage_pct"] = self.usage.reindex(key).to_numpy()
        d["arsenal_size"] = self.size.reindex(idx).to_numpy()
        sp = self.spread.reindex(idx)
        d["arsenal_ivb_spread"], d["arsenal_hb_spread"] = sp["ivb"].to_numpy(), sp["hb"].to_numpy()
        # tunneling: separación en el punto de decisión vs en el plato frente a la recta principal
        rf = ref[TRAJ].add_prefix("ref_")
        ok = rf.notna().all(axis=1)
        tun = pd.DataFrame(np.nan, index=d.index, columns=["release_dist_vs_fb", "decision_sep_vs_fb", "plate_sep_vs_fb"])
        if ok.any():
            a, r = d[ok], rf[ok]
            sep = lambda x: np.hypot(*(trajectory_at(a, x).to_numpy() - trajectory_at(pd.concat([a[[]], r], axis=1), x, "ref_").to_numpy()).T)
            tun.loc[ok, "release_dist_vs_fb"] = np.hypot(
                a["PitchTrajectoryZc0"] - r["ref_PitchTrajectoryZc0"], a["PitchTrajectoryYc0"] - r["ref_PitchTrajectoryYc0"])
            tun.loc[ok, "decision_sep_vs_fb"] = sep(DECISION_Y_FT)
            tun.loc[ok, "plate_sep_vs_fb"] = sep(0.0)
        d = d.join(tun)
        d["tunnel_ratio"] = d["plate_sep_vs_fb"] / d["decision_sep_vs_fb"].clip(lower=0.05)  # alto = se separa tarde
        d.loc[d["pitch_id"].to_numpy() == d["primary_fb_id"].to_numpy(), ["velo_diff_vs_fb", "ivb_diff_vs_fb", "hb_diff_vs_fb", "spin_diff_vs_fb", "axis_diff_vs_fb"]] = 0.0
        return d.drop(columns=["ivb", "hb", "axis"])


def fit_arsenal(train: pd.DataFrame) -> ArsenalModel:
    """Aprende (solo de `train`, lanzamientos propios) la recta principal, el uso y el arsenal de cada pitcher-temporada."""
    d = with_arm_side(train[train["pitch_id"] >= 0])
    primary = primary_fastball(d)
    idx = pd.MultiIndex.from_frame(d[KEYS])
    is_prim = d["pitch_id"].to_numpy() == primary.reindex(idx).to_numpy()
    ref = d[is_prim].groupby(KEYS)[REF_COLS].mean()
    cnt = d.groupby(KEYS + ["pitch_id"]).size()
    usage = cnt / cnt.groupby(level=KEYS).transform("sum")
    size = (usage >= ARSENAL_MIN_USAGE).groupby(level=KEYS).sum()
    means = d.groupby(KEYS + ["pitch_id"])[["ivb", "hb"]].mean()
    spread = means[usage >= ARSENAL_MIN_USAGE].groupby(level=KEYS).std().fillna(0.0)
    return ArsenalModel(primary, ref, usage.rename("usage"), size.rename("size"), spread)
