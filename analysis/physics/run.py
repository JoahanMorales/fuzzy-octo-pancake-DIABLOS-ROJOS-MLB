"""HACK-004: ρ̂ por juego, validación Cl/Cd, ΔIVB/ΔHB/Δvelo por familia con IC bootstrap. Escribe reports/physics/."""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus.features.identity import assign_pitch_id
from stuffplus.io import load_raw
from stuffplus.physics import aero
from stuffplus.physics.translate import OUTCOMES, MovementModel
from stuffplus.schema import clean

warnings.filterwarnings("ignore")
OUT = Path("reports/physics")
OUT.mkdir(parents=True, exist_ok=True)
N_BOOT, SEED = 100, 2240
FB = ["Four-Seam", "Sinker", "Cutter"]

d = assign_pitch_id(clean(load_raw()))
d = d[d.pitch_id >= 0].copy()
d = d.join(aero.decompose(d)[["cd_proxy", "cl_proxy", "spin_eff"]])
d["is_fastball"] = d.pitch_family.isin(FB)

# --- ρ̂ por juego (referencia: mediana de Cd-proxy de rectas en juegos sin altitud = 1.0)
ref = d[d.is_fastball & (d.altitude_category == "No Altitude")].cd_proxy.median()
bucket = d.groupby("game_anon_id").altitude_category.agg(lambda s: s.mode().iat[0])
prior = pd.Series(d.groupby("altitude_category", observed=True).cd_proxy.median() / ref)
rho_game = aero.game_density_index(d, game_col="game_anon_id", ref_cd=ref, prior=bucket.astype(str).map(prior.rename(index=str)).astype(float))
d["rho_hat"] = d.game_anon_id.map(rho_game)
games = pd.DataFrame({"rho_hat": rho_game, "bucket": bucket, "n_fb": d[d.is_fastball].groupby("game_anon_id").size()})
games.groupby("bucket", observed=True).rho_hat.describe().round(4).to_csv(OUT / "rho_by_bucket.csv")
games.round(4).to_csv(OUT / "rho_by_game.csv")  # agregado por juego, sin lanzamientos
rho_b = d.groupby("altitude_category", observed=True).rho_hat.mean()

# --- validación: Cl/Cd no debe depender de ρ (ambos ∝ ρ); dentro de cada lanzamiento (pitch_key)
fb = d[d.is_fastball].copy()
fb["clcd"] = fb.cl_proxy / fb.cd_proxy
fb["clcd_dm"] = fb.clcd - fb.groupby("pitch_key").clcd.transform("mean")
val = fb.groupby("altitude_category", observed=True).agg(cd_proxy=("cd_proxy", "median"), cl_proxy=("cl_proxy", "median"),
                                                          clcd_within=("clcd_dm", "mean"), spin_eff=("spin_eff", "median"))
val["cd_ratio_vs_no"] = val.cd_proxy / val.loc["No Altitude", "cd_proxy"]
val["cl_ratio_vs_no"] = val.cl_proxy / val.loc["No Altitude", "cl_proxy"]
val.round(5).to_csv(OUT / "validation_cl_cd.csv")

# --- Δ Extreme vs No por familia, modelo de efectos fijos + bootstrap por pitcher-temporada
dr = rho_b["Extreme Altitude"] - rho_b["No Altitude"]
rng = np.random.default_rng(SEED)
rows = []
for fam, g in d.groupby("pitch_family"):
    if len(g) < 3000:
        continue
    est = MovementModel().fit(g, g.rho_hat).rho_effect
    cl = g.groupby(["pitcher_anon_id", "year"]).ngroup().to_numpy()
    groups = {c: np.flatnonzero(cl == c) for c in np.unique(cl)}
    keys = np.array(list(groups))
    boots = []
    for _ in range(N_BOOT):
        pick = rng.choice(keys, len(keys))
        idx = np.concatenate([groups[c] for c in pick])
        gb = g.iloc[idx].copy()
        gb["pitch_key"] = gb["pitch_key"] + "_" + pd.Series(np.repeat(np.arange(len(pick)), [len(groups[c]) for c in pick]), index=gb.index).astype(str)
        boots.append(MovementModel().fit(gb, gb.rho_hat).rho_effect)
    for k in OUTCOMES:
        b = np.array([x[k] for x in boots]) * dr
        rows.append(dict(pitch_family=fam, outcome=k, delta=est[k] * dr, lo95=np.percentile(b, 2.5), hi95=np.percentile(b, 97.5), n=len(g)))
res = pd.DataFrame(rows).round(3)
res.to_csv(OUT / "delta_extreme_vs_no.csv", index=False)
print("Δρ Extreme−No =", round(dr, 4))
print(res.pivot(index="pitch_family", columns="outcome", values="delta"))
print(val.round(4))
