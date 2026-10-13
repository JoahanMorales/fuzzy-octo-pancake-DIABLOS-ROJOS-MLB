"""Identidad de lanzamiento invariante a la altitud.

`AutoPitchType` de Trackman cambia con la densidad del aire, así que los lanzamientos se
comparan por `pitch_id`: mezcla gaussiana por pitcher-temporada sobre rasgos que la
altitud no toca (velocidad de salida, punto de liberación, extensión; sin giro, que sí se mueve con la altitud).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

# SpinRate queda fuera: sube ~+17 rpm en Extreme dentro del mismo lanzamiento (medición/efecto de la altitud) y con él
# el uso por pitch_family se desplazaba hasta 0.70 pp (Changeup/Slider); sin él, 0.49 pp (pureza vs AutoPitchType
# en nivel del mar baja de 0.77 a 0.73). Ajustar SpinRate por bucket no ayudó (reports/shapes/README.md).
IDENTITY_FEATURES = ["RelSpeed", "RelHeight", "RelSide", "Extension"]
NO_ALTITUDE = "No Altitude"
MIN_FIT = 40  # lanzamientos mínimos para ajustar la mezcla
MAX_K = 5
MIN_WEIGHT = 0.05  # un componente con <5 % del uso no es un lanzamiento
SEED = 2240


def _fit_mixture(x: np.ndarray) -> GaussianMixture | None:
    """Mejor k por BIC; descarta k cuyo componente más chico pese < MIN_WEIGHT."""
    best, best_bic = None, np.inf
    for k in range(1, min(MAX_K, len(x) // 25) + 1):
        gm = GaussianMixture(k, covariance_type="diag", n_init=3, reg_covar=1e-4, random_state=SEED).fit(x)
        if gm.weights_.min() < MIN_WEIGHT:
            continue
        bic = gm.bic(x)
        if bic < best_bic:
            best, best_bic = gm, bic
    return best


def _assign_group(g: pd.DataFrame, feats: list[str], alt_col: str, type_col: str) -> pd.DataFrame:
    x = g[feats].to_numpy(float)
    ok = np.isfinite(x).all(axis=1)
    base = ok & (g[alt_col].to_numpy() == NO_ALTITUDE)
    if base.sum() < MIN_FIT:  # sin suficientes juegos a nivel del mar: ajusta con todo
        base = ok
    out = pd.DataFrame({"pitch_id": -1, "pitch_family": pd.NA}, index=g.index)
    if base.sum() < MIN_FIT:
        return out
    mu, sd = x[base].mean(0), x[base].std(0) + 1e-9
    z = (x - mu) / sd
    gm = _fit_mixture(z[base])
    if gm is None:
        return out
    lab = np.full(len(g), -1)
    lab[ok] = gm.predict(z[ok])
    # ordena componentes por velocidad media para que los ids sean estables y legibles
    order = np.argsort(-gm.means_[:, feats.index("RelSpeed")])
    remap = {int(c): i for i, c in enumerate(order)}
    lab = np.array([remap.get(int(v), -1) for v in lab])
    out["pitch_id"] = lab
    # etiqueta de familia: AutoPitchType modal en juegos sin altitud (si no hay, en todos)
    ref = g.assign(_l=lab)
    ref = ref[ref["_l"] >= 0]
    pool = ref[ref[alt_col] == NO_ALTITUDE]
    fam = {}
    for c in ref["_l"].unique():
        src = pool[pool["_l"] == c][type_col]
        if src.empty:
            src = ref[ref["_l"] == c][type_col]
        fam[c] = src.mode().iat[0] if not src.mode().empty else pd.NA
    out["pitch_family"] = pd.Series(lab, index=g.index).map(fam)
    return out


def assign_pitch_id(
    df: pd.DataFrame,
    features: list[str] | None = None,
    pitcher_col: str = "pitcher_anon_id",
    season_col: str = "year",
    alt_col: str = "altitude_category",
    type_col: str = "AutoPitchType",
) -> pd.DataFrame:
    """Devuelve df con `pitch_id` (int por pitcher-temporada; -1 = sin asignar) y `pitch_family`.

    El ajuste usa solo juegos sin altitud; luego se puntúan todos los lanzamientos, así que
    el uso por pitch_id no cambia con la densidad. `pitch_key` = '{pitcher}_{season}_{pitch_id}'.
    """
    feats = features or IDENTITY_FEATURES
    parts = [
        _assign_group(g, feats, alt_col, type_col)
        for _, g in df.groupby([pitcher_col, season_col], sort=False)
    ]
    res = pd.concat(parts).reindex(df.index)
    out = df.copy()
    out["pitch_id"] = res["pitch_id"].astype(int)
    out["pitch_family"] = res["pitch_family"]
    out["pitch_key"] = (
        out[pitcher_col].astype(str) + "_" + out[season_col].astype(str) + "_" + out["pitch_id"].astype(str)
    )
    return out


def usage_shift(df: pd.DataFrame, label: str, pitcher_col: str = "pitcher_anon_id",
                season_col: str = "year", alt_col: str = "altitude_category",
                min_n: int = 100) -> pd.Series:
    """Δ de uso (pp) Extreme − No por valor de `label`, promedio con peso igual entre pitcher-temporadas.

    Solo cuenta pitcher-temporadas con ≥ `min_n` lanzamientos en ambos ambientes. El ruido de
    muestreo se cancela al promediar con signo (el |Δ| por pitcher tiene un piso de ~3 pp).
    """
    k = [pitcher_col, season_col]
    e = df[df[alt_col].isin([NO_ALTITUDE, "Extreme Altitude"])]
    n = e.groupby(k + [alt_col], observed=True).size().unstack(fill_value=0)
    ok = n[(n.get(NO_ALTITUDE, 0) >= min_n) & (n.get("Extreme Altitude", 0) >= min_n)].index
    if len(ok) == 0:
        return pd.Series(dtype=float)
    e = e.set_index(k).loc[ok].reset_index()
    cnt = e.groupby(k + [alt_col, label], observed=True).size()
    share = (cnt / e.groupby(k + [alt_col], observed=True).size()).unstack(alt_col, fill_value=0)
    return ((share["Extreme Altitude"] - share[NO_ALTITUDE]) * 100).groupby(label, observed=True).sum() / len(ok)
