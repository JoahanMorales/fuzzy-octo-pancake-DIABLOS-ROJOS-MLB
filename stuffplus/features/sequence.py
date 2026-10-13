"""Rasgos de secuencia. Las filas están en orden de juego (`pitch_idx_in_game` de `schema.clean`).

Solo mira hacia atrás (lanzamiento previo del mismo PA), nunca hacia adelante: sin fuga.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TTO_SIZE = 9  # bateadores por vuelta al orden


def add_sequence_features(df: pd.DataFrame) -> pd.DataFrame:
    """`prev_pitch_id`, `prev_velo_diff`, `prev_loc_diff` (ft, ubicación en el plato), `pitch_number_in_pa`, `times_through_order`."""
    d = df.sort_values("pitch_idx_in_game", kind="stable") if "pitch_idx_in_game" in df else df
    g = d.groupby("pa_id", sort=False)
    out = d.copy()
    out["prev_pitch_id"] = g["pitch_id"].shift(1).fillna(-1).astype(int) if "pitch_id" in d else np.nan
    out["prev_velo_diff"] = d["RelSpeed"] - g["RelSpeed"].shift(1)
    out["prev_loc_diff"] = np.hypot(
        d["PlateLocSide"] - g["PlateLocSide"].shift(1), d["PlateLocHeight"] - g["PlateLocHeight"].shift(1))
    if "pitch_number_in_pa" not in out:
        out["pitch_number_in_pa"] = g.cumcount() + 1
    # vuelta al orden: rango del PA entre los PA que enfrentó ese pitcher en el juego
    first = out.drop_duplicates("pa_id")[["pa_id", "game_anon_id", "pitcher_anon_id"]]
    first = first.assign(_r=first.groupby(["game_anon_id", "pitcher_anon_id"], sort=False).cumcount())
    out["times_through_order"] = out["pa_id"].map(first.set_index("pa_id")["_r"] // TTO_SIZE + 1).astype(int)
    return out.loc[df.index]
