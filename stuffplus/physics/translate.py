"""Traducción de movimiento entre densidades de aire.

El efecto de ρ es **proporcional al movimiento propio del lanzamiento** (Magnus y arrastre ∝ ρ): una recta con
19" de ride cambia más que una de 13", y una curva (IVB negativo) se mueve en sentido contrario a una recta. Por
eso `PROPORTIONAL` outcomes se modelan como y = Xβ + k·ρ·ȳ_lanzamiento y se trasladan como y·(1 + k·Δρ); solo
`plate_velo` (nivel de velocidad, no movimiento) usa un γ aditivo.

Modelo con efectos fijos por `pitch_key` (pitcher × temporada × pitch_id, HACK-029): la
variación *dentro* de cada lanzamiento entre juegos a distinta densidad identifica el
efecto de ρ sin confundirlo con diferencias entre pitchers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

OUTCOMES = {"ivb": "InducedVertBreak", "hb": "HorzBreak", "speed_drop": "SpeedDrop", "plate_velo": "ZoneSpeed"}
PROPORTIONAL = {"ivb", "hb", "speed_drop"}  # efecto ∝ valor propio del lanzamiento; el resto, aditivo
BASE_FEATURES = ["RelSpeed", "SpinRate", "RelHeight", "RelSide", "Extension"]


def design(df: pd.DataFrame) -> pd.DataFrame:
    """Rasgos de liberación y giro (el eje de giro entra como sen/cos)."""
    x = df[BASE_FEATURES].astype(float).copy()
    ang = np.deg2rad(df["SpinAxis"].astype(float))
    x["axis_sin"], x["axis_cos"] = np.sin(ang), np.cos(ang)
    return x


@dataclass
class MovementModel:
    """y = Xβ + k·ρ·ȳ (proporcional) o Xβ + γ·ρ (aditivo) con efecto fijo del lanzamiento. `fit` estima β, k|γ por outcome."""

    coef: dict = field(default_factory=dict)  # outcome -> (β_rasgos, k|γ)
    intercept: dict = field(default_factory=dict)
    cols: list = field(default_factory=list)
    rho_ref: float = 1.0  # ρ media del ajuste: nivel de `intercept`

    def fit(self, df: pd.DataFrame, rho: pd.Series, key_col: str = "pitch_key") -> "MovementModel":
        x = design(df)
        self.cols = list(x.columns)
        rho_a = np.asarray(rho, float)
        ok = x.notna().all(axis=1).to_numpy() & df[list(OUTCOMES.values())].notna().all(axis=1).to_numpy() & np.isfinite(rho_a)
        x, d, r = x[ok], df[ok], rho_a[ok]
        key = d[key_col].to_numpy()
        for name, col in OUTCOMES.items():
            y = d[col].astype(float)
            ybar = y.groupby(key).transform("mean").to_numpy()
            z = pd.Series(r * ybar if name in PROPORTIONAL else r, index=x.index, name="rho_term")
            xz = x.assign(rho_term=z)
            xd = xz - xz.groupby(key).transform("mean")
            yd = y - y.groupby(key).transform("mean")
            beta, *_ = np.linalg.lstsq(xd.to_numpy(), yd.to_numpy(), rcond=None)
            self.coef[name] = beta
            self.intercept[name] = float((y - x.to_numpy() @ beta[:-1]).mean())  # nivel a la ρ media de ajuste
        self.rho_ref = float(r.mean())
        return self

    @property
    def rho_effect(self) -> dict:
        """k (fracción de cambio del outcome por +1.0 de ρ relativa) en `PROPORTIONAL`; γ (pulgadas o mph) en el resto."""
        return {k: float(b[-1]) for k, b in self.coef.items()}

    def expected_movement(self, df: pd.DataFrame, rho) -> pd.DataFrame:
        """(ivb, hb, speed_drop, plate_velo) esperados de rasgos de liberación/giro y ρ (escalar o serie)."""
        x = design(df)
        r = np.broadcast_to(np.asarray(rho, float), len(x))
        out = {}
        for name, b in self.coef.items():
            base = x.to_numpy() @ b[:-1] + self.intercept[name]  # esperado a ρ_ref
            out[name] = base * (1.0 + b[-1] * (r - self.rho_ref)) if name in PROPORTIONAL else base + b[-1] * (r - self.rho_ref)
        return pd.DataFrame(out, index=df.index)

    def translate_pitch(self, pitch: pd.DataFrame | pd.Series, rho_from, rho_to) -> pd.DataFrame:
        """Mueve lanzamientos observados de ρ_from a ρ_to conservando su idiosincrasia.

        Outcomes proporcionales: y·(1 + k·Δρ); `plate_velo`: y + γ·Δρ.
        """
        p = pitch.to_frame().T if isinstance(pitch, pd.Series) else pitch
        delta = np.asarray(rho_to, float) - np.asarray(rho_from, float)
        out = {}
        for k, col in OUTCOMES.items():
            y = p[col].astype(float).to_numpy()
            out[k] = y * (1.0 + self.rho_effect[k] * delta) if k in PROPORTIONAL else y + self.rho_effect[k] * delta
        return pd.DataFrame(out, index=p.index)

    def delta_mean(self, pitches: pd.DataFrame, rho_from, rho_to) -> dict:
        """Cambio medio por outcome al trasladar `pitches` (p.ej. una familia) de ρ_from a ρ_to."""
        t = self.translate_pitch(pitches, rho_from, rho_to)
        return {k: float((t[k] - pitches[col].astype(float)).mean()) for k, col in OUTCOMES.items()}
