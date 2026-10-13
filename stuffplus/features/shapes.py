"""Formas de lanzamiento interpretables ("riding 4S", "sweeper"...) a partir del movimiento
trasladado a nivel del mar (HACK-004), para que la etiqueta no dependa de la altitud.

HorzBreak se normaliza por mano: positivo = lado del brazo (mismo signo para zurdos y derechos).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from stuffplus.physics import aero
from stuffplus.physics.translate import MovementModel, proportional_shift

FASTBALLS = ("Four-Seam", "Sinker", "Cutter")
NO_ALTITUDE = "No Altitude"


def _sign(throws) -> np.ndarray:
    return np.where(pd.Series(throws).astype(str).str.startswith("L"), -1.0, 1.0)


def shape_rule(family, ivb, hb, velo):
    """Regla vectorizada familia + movimiento a nivel del mar → forma. Umbrales de los cuantiles reales."""
    fam = np.asarray(family, dtype=object)
    ivb, hb, velo = (np.asarray(a, float) for a in (ivb, hb, velo))
    out = fam.copy()
    out[fam == "Four-Seam"] = np.where(ivb[fam == "Four-Seam"] >= 17, "riding 4S", "4S")
    out[fam == "Sinker"] = np.where(ivb[fam == "Sinker"] < 11, "sinking 2S", "running 2S")
    out[fam == "Cutter"] = "cutter"
    m = fam == "Slider"
    out[m] = np.where(hb[m] <= -9, "sweeper", np.where(hb[m] > -5, "gyro slider", "slider"))
    m = fam == "Curveball"
    out[m] = np.where(np.abs(hb[m]) <= 6, "12-6 CB", "11-5 CB")
    m = fam == "Changeup"
    out[m] = np.where(velo[m] >= 86, "power CH", "changeup")
    out[fam == "Splitter"] = "splitter"
    return out


@dataclass
class ShapeModel:
    rho_effect: dict = field(default_factory=dict)  # familia -> {ivb, hb}: k de HACK-004 (cambio relativo del movimiento por +1 de ρ)
    rho_ref: float = 1.0  # ρ media de ajuste (nivel de ȳ en `proportional_shift`)
    centroids: pd.DataFrame | None = None  # familia -> (RelSpeed, ivb, hb) a nivel del mar
    scale: pd.Series | None = None

    def to_sea_level(self, family, ivb, hb_norm, rho):
        """Traslada movimiento observado (hb ya normalizado por mano) a ρ=1: `proportional_shift` (HACK-004): proporcional al
        movimiento propio, no un desplazamiento fijo por familia."""
        e_i = np.array([self.rho_effect.get(f, {"ivb": 0})["ivb"] for f in family])
        e_h = np.array([self.rho_effect.get(f, {"hb": 0})["hb"] for f in family])
        r = np.asarray(rho, float)
        return (proportional_shift(ivb, e_i, r, 1.0, self.rho_ref), proportional_shift(hb_norm, e_h, r, 1.0, self.rho_ref))

    def infer_family(self, velo, ivb, hb) -> np.ndarray:
        x = pd.DataFrame({"RelSpeed": velo, "ivb": ivb, "hb": hb}) / self.scale
        c = self.centroids / self.scale
        dist = ((x.to_numpy()[:, None, :] - c.to_numpy()[None]) ** 2).sum(-1)
        return c.index.to_numpy()[dist.argmin(1)]


def _calibrate_k(g: pd.DataFrame, col: str, k0: float, rho: np.ndarray, rho_ref: float, min_n: int = 30) -> float:
    """Ajusta k para que el movimiento trasladado no difiera entre No y Extreme *dentro* de cada lanzamiento.

    La regresión de efectos fijos subestima/sobrestima k cuando la muestra de ajuste (peso por n, ρ̂ ruidosa)
    difiere de la que usa `usage_shift` (cada pitcher-temporada pesa igual). Una sola raíz por familia/outcome.
    """
    cat = g["altitude_category"].astype(str).to_numpy()
    sel = np.isin(cat, [NO_ALTITUDE, "Extreme Altitude"])
    y, key, env, r = g[col].to_numpy(float)[sel], g["pitch_key"].to_numpy()[sel], cat[sel], rho[sel]
    n = pd.crosstab(key, env)
    keep = n.index[(n.get(NO_ALTITUDE, 0) >= min_n) & (n.get("Extreme Altitude", 0) >= min_n)]
    m = np.isin(key, keep)
    if m.sum() == 0:
        return k0
    y, key, env, r = y[m], key[m], env[m], r[m]

    def gap(k):
        t = pd.DataFrame({"key": key, "env": env, "y": proportional_shift(y, k, r, 1.0, rho_ref)})
        mu = t.groupby(["key", "env"])["y"].mean().unstack()
        return float((mu["Extreme Altitude"] - mu[NO_ALTITUDE]).mean())

    g0, g1 = gap(k0), gap(k0 + 0.5)
    return float(k0 - g0 * 0.5 / (g1 - g0)) if g1 != g0 else k0


def fit_shapes(df: pd.DataFrame):
    """Ajusta ρ̂ por juego y el efecto de ρ por familia; devuelve (ShapeModel, df con sea-level + shape).

    `df` debe traer `pitch_family` (assign_pitch_id) y `pitch_id >= 0` para quedar asignado.
    """
    d = df[df["pitch_id"] >= 0].copy()
    cd = aero.decompose(d)["cd_proxy"]  # proxy ∝ ρ: no depende de la densidad asumida
    fb = d["pitch_family"].isin(FASTBALLS)
    ref = cd[fb & (d["altitude_category"] == NO_ALTITUDE)].median()
    d["is_fastball"] = fb
    d["rho_hat"] = d["game_anon_id"].map(aero.game_density_index(d, game_col="game_anon_id", ref_cd=ref))
    # ρ̂ por juego trae ruido de medición (sd≈0.04 en No Altitude) que atenúa k y desordena el traslado:
    # se usa la ρ̂ media del bucket de altitud (el efecto de altitud es el que importa para la etiqueta)
    d["rho_env"] = d.groupby("altitude_category", observed=True)["rho_hat"].transform("mean")
    sg = _sign(d["PitcherThrows"])
    d["hb_norm"] = d["HorzBreak"] * sg
    model = ShapeModel()
    fit_df = d.assign(HorzBreak=d["hb_norm"])  # el efecto de ρ en HB se estima con la escala normalizada por mano
    for fam, g in fit_df.groupby("pitch_family"):
        eff = MovementModel().fit(g, g["rho_env"], equal_key_weight=True).rho_effect
        rho_e, ref = g["rho_env"].to_numpy(), float(d["rho_env"].mean())
        model.rho_effect[fam] = {
            "ivb": _calibrate_k(g, "InducedVertBreak", eff["ivb"], rho_e, ref),
            "hb": _calibrate_k(g, "HorzBreak", eff["hb"], rho_e, ref),
        }
    model.rho_ref = float(d["rho_env"].mean())
    rho = d["rho_env"].to_numpy()
    e_i = d["pitch_family"].map(lambda f: model.rho_effect[f]["ivb"]).to_numpy()
    e_h = d["pitch_family"].map(lambda f: model.rho_effect[f]["hb"]).to_numpy()
    d["ivb_sl"] = proportional_shift(d["InducedVertBreak"], e_i, rho, 1.0, model.rho_ref)
    d["hb_sl"] = proportional_shift(d["hb_norm"], e_h, rho, 1.0, model.rho_ref)
    cen = d.groupby("pitch_family").agg(RelSpeed=("RelSpeed", "mean"), ivb=("ivb_sl", "mean"), hb=("hb_sl", "mean"))
    model.centroids = cen
    model.scale = pd.Series({"RelSpeed": d["RelSpeed"].std(), "ivb": d["ivb_sl"].std(), "hb": d["hb_sl"].std()})
    d["shape"] = shape_rule(d["pitch_family"], d["ivb_sl"], d["hb_sl"], d["RelSpeed"])
    return model, d


def assign_shape(model: ShapeModel, velo: float, ivb: float, hb: float, throws: str = "Right",
                 rho: float = 1.0, family: str | None = None) -> str:
    """Forma de un solo lanzamiento (entrada del dashboard). `hb` crudo (+ = derecha del catcher)."""
    hb_n = hb * float(_sign([throws])[0])
    fam = np.array([family] if family else model.infer_family([velo], [ivb], [hb_n]), dtype=object)
    for _ in range(2 if family is None else 1):  # familia → traslado → refina familia
        s_ivb, s_hb = model.to_sea_level(fam, [ivb], [hb_n], [rho])
        if family is None:
            fam = np.array(model.infer_family([velo], s_ivb, s_hb), dtype=object)
    return str(shape_rule(fam, s_ivb, s_hb, [velo])[0])
