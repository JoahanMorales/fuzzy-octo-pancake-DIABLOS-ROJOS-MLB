"""Tabla de desplazamiento de etiquetas: AutoPitchType vs pitch_family (Extreme − No, pp). Uso: python reports/shapes/make_label_shift.py"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus.features.identity import assign_pitch_id, usage_shift
from stuffplus.io import load_raw
from stuffplus.schema import clean

warnings.filterwarnings("ignore")
d = assign_pitch_id(clean(load_raw()))
rng = np.random.default_rng(0)
m = d.altitude_category.isin(["No Altitude", "Extreme Altitude"])
null = d.copy()
null.loc[m, "altitude_category"] = null[m].groupby(["pitcher_anon_id", "year"])["altitude_category"].transform(
    lambda s: pd.Series(rng.permutation(s.values), index=s.index))
t = pd.DataFrame({
    "AutoPitchType_pp": usage_shift(d, "AutoPitchType"),
    "pitch_family_pp": usage_shift(d, "pitch_family"),
    "pitch_family_null_pp": usage_shift(null, "pitch_family"),
}).round(2)
t.index.name = "tipo"
t.to_csv(Path(__file__).with_name("label_shift.csv"))
print(t, f"\nmax|Δ| APT={t.AutoPitchType_pp.abs().max():.2f}  family={t.pitch_family_pp.abs().max():.2f}  unassigned={(d.pitch_id<0).mean():.3%}")
