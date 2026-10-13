"""Formas por pitch_family a nivel del mar: shapes.csv, shape_shift.csv, centroids.png. Uso: python reports/shapes/make_shapes.py"""
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stuffplus.features.identity import assign_pitch_id, usage_shift
from stuffplus.features.shapes import fit_shapes
from stuffplus.io import load_raw
from stuffplus.schema import clean

warnings.filterwarnings("ignore")
here = Path(__file__).parent
full = assign_pitch_id(clean(load_raw()))
model, d = fit_shapes(full)
print(f"asignado: {len(d) / len(full):.2%}")
g = d.groupby("shape").agg(n=("shape", "size"), RelSpeed=("RelSpeed", "mean"), ivb_sl=("ivb_sl", "mean"), hb_sl=("hb_sl", "mean"),
                           spin=("SpinRate", "mean")).round(1)
g["pct"] = (100 * g.n / g.n.sum()).round(2)
g.sort_values("n", ascending=False).to_csv(here / "shapes.csv")
usage_shift(d, "shape").round(2).rename("shape_pp_extreme_minus_no").to_csv(here / "shape_shift.csv")
print(g.sort_values("n", ascending=False))
fig, ax = plt.subplots(figsize=(7, 6))
for s, r in g.iterrows():
    ax.scatter(r.hb_sl, r.ivb_sl, s=r.n / 400, color="#B71C1C", alpha=0.6)
    ax.annotate(s, (r.hb_sl, r.ivb_sl), ha="center", fontsize=8)
ax.axhline(0, color="k", lw=.5); ax.axvline(0, color="k", lw=.5)
ax.set_xlabel("HB a nivel del mar (+ = lado del brazo), in"); ax.set_ylabel("IVB a nivel del mar, in")
ax.set_title("Centroides de forma (ρ=1)"); fig.tight_layout(); fig.savefig(here / "centroids.png", dpi=130)
