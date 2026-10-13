"""Traducción de movimiento entre densidades de aire.

Modelo con efectos fijos por `pitch_key` (pitcher × temporada × pitch_id, HACK-029): la
variación *dentro* de cada lanzamiento entre juegos a distinta densidad identifica el
efecto de ρ sin confundirlo con diferencias entre pitchers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

OUTCOMES = {"ivb": "InducedVertBreak", "hb": "HorzBreak", "speed_drop": "SpeedDrop", "plate_velo": "ZoneSpeed"}
BASE_FEATURES = ["RelSpeed", "SpinRate", "RelHeight", "RelSide", "Extension"]


def design(df: pd.DataFrame) -> pd.DataFrame:
    """Rasgos de liberación y giro (el eje de giro entra como sen/cos)."""
    x = df[BASE_FEATURES].astype(float).copy()
    ang = np.deg2rad(df["SpinAxis"].astype(float))
    x["axis_sin"], x["axis_cos"] = np.sin(ang), np.cos(ang)
    return x


@dataclass
class MovementModel:
    """y = X·β + γ·ρ (+ efecto fijo del lanzamiento). `fit` estima β, γ por outcome."""

    coef: dict = field(default_factory=dict)  # outcome -> (β_rasgos, γ_rho)
    intercept: dict = field(default_factory=dict)
    cols: list = field(default_factory=list)

    def fit(self, df: pd.DataFrame, rho: pd.Series, key_col: str = "pitch_key") -> "MovementModel":
        x = design(df)
        x["rho"] = rho.to_numpy(float)
        self.cols = list(x.columns)
        ok = x.notna().all(axis=1) & df[list(OUTCOMES.values())].notna().all(axis=1)
        x, d, key = x[ok], df[ok], df.loc[ok, key_col]
        xd = x - x.groupby(key.to_numpy()).transform("mean")
        for name, col in OUTCOMES.items():
            y = d[col].astype(float)
            yd = y - y.groupby(key.to_numpy()).transform("mean")
            beta, *_ = np.linalg.lstsq(xd.to_numpy(), yd.to_numpy(), rcond=None)
            self.coef[name] = beta
            self.intercept[name] = float((y - x.to_numpy() @ beta).mean())
        return self

    @property
    def rho_effect(self) -> dict:
        """Cambio en cada outcome por +1.0 de ρ relativa (pulgadas o mph)."""
        return {k: float(b[-1]) for k, b in self.coef.items()}

    def expected_movement(self, df: pd.DataFrame, rho) -> pd.DataFrame:
        """(ivb, hb, speed_drop, plate_velo) esperados de rasgos de liberación/giro y ρ (escalar o serie)."""
        x = design(df)
        x["rho"] = np.broadcast_to(np.asarray(rho, float), len(x))
        return pd.DataFrame(
            {k: x[self.cols].to_numpy() @ b + self.intercept[k] for k, b in self.coef.items()}, index=df.index
        )

    def translate_pitch(self, pitch: pd.DataFrame | pd.Series, rho_from, rho_to) -> pd.DataFrame:
        """Mueve lanzamientos observados de ρ_from a ρ_to conservando su idiosincrasia (solo suma γ·Δρ)."""
        p = pitch.to_frame().T if isinstance(pitch, pd.Series) else pitch
        delta = np.asarray(rho_to, float) - np.asarray(rho_from, float)
        return pd.DataFrame(
            {k: p[col].astype(float).to_numpy() + self.rho_effect[k] * delta for k, col in OUTCOMES.items()},
            index=p.index,
        )
