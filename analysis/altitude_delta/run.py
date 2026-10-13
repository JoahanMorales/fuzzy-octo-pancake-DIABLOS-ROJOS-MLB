"""Altitude effect (HACK-015): ΔStuff+ by pitch shape, Harp Helú air vs sea level, with observed triangulation.

    python analysis/altitude_delta/run.py          # real data, ~10 min
    python analysis/altitude_delta/run.py --fast

Reports in reports/altitude_delta/ (aggregates only):
  delta_by_shape.csv / delta_by_family.csv   ΔStuff+ (Harp Helú − sea level) with pitcher-cluster 95 % CI,
                                              movement and component deltas, verdict vs league, physics sentence
  triangulation.csv                          counterfactual Δ at Extreme-bucket air vs within-pitcher observed Δ
  altitude_curves.csv                        mean Stuff+ by shape as ρ goes 1.0 → 0.80 (every LMB park in between)
  forest_by_shape.png, altitude_curves.png   figures for the paper, deck and dashboard
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stuffplus import config, schema  # noqa: E402
from stuffplus.altitude import (  # noqa: E402
    STUFF_FEATURES_INVARIANT, altitude_curve, counterfactual_scores, delta_table, physics_translator,
    within_pitcher_observed,
)
from stuffplus.features.shapes import fit_shapes  # noqa: E402
from stuffplus.models.location import add_pitch_family  # noqa: E402
from stuffplus.models.stuff import StuffModel  # noqa: E402
from stuffplus.physics.constants import RHO_HARP_HELU  # noqa: E402
from stuffplus.scale import PlusScaler  # noqa: E402

REPORTS = config.REPORTS_DIR / "altitude_delta"


def _stuff_run():
    spec = importlib.util.spec_from_file_location("stuff_run", ROOT / "analysis" / "stuff_model" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepare(df_clean: pd.DataFrame):
    frame = add_pitch_family(_stuff_run().prepare(df_clean))
    shape_model, d = fit_shapes(frame)
    return shape_model, d


def _forest(table: pd.DataFrame, league: float, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = table.sort_values("delta_stuff")
    colors = ["#1f77b4" if v == "gana relativo" else "#D71920" if v == "pierde relativo" else "#7f7f7f" for v in t.verdict]
    fig, ax = plt.subplots(figsize=(7.5, 0.42 * len(t) + 1.4))
    y = np.arange(len(t))
    ax.errorbar(t.delta_stuff, y, xerr=[t.delta_stuff - t.delta_lo, t.delta_hi - t.delta_stuff], fmt="none", ecolor="#555", capsize=3)
    ax.scatter(t.delta_stuff, y, c=colors, s=60, zorder=3)
    ax.axvline(league, color="#555", ls="--", lw=1)
    ax.text(league, -0.9, f" promedio liga {league:+.1f}", fontsize=8, color="#555")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y, [f"{s} (n={n:,})" for s, n in zip(t.iloc[:, 0], t.pitches)])
    ax.set_xlabel("ΔStuff+ en aire del Harp Helú vs nivel del mar (IC 95 % por pitcher)")
    ax.set_title("¿Qué formas de pitch resisten la altitud?\nazul = pierde menos que la liga · rojo = pierde más", fontsize=10)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _curves(curves: pd.DataFrame, by: str, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for key, g in curves.groupby(by):
        g = g.sort_values("rho")
        ax.plot(g.rho, g.delta_vs_sea_level, marker="o", ms=3, label=key)
    ax.axvline(RHO_HARP_HELU, color="#D71920", ls="--", lw=1)
    ax.text(RHO_HARP_HELU, ax.get_ylim()[1], " Harp Helú", color="#D71920", fontsize=8, va="top")
    ax.invert_xaxis()
    ax.set_xlabel("densidad del aire relativa al nivel del mar (ρ)  →  más altitud")
    ax.set_ylabel("ΔStuff+ vs nivel del mar")
    ax.legend(fontsize=7, ncol=2)
    ax.set_title("Curvas de altitud por forma de pitch", fontsize=10)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def run(shape_model, d: pd.DataFrame, fast: bool = False, write_reports: bool = True) -> dict:
    rounds = dict(class_rounds=60, contact_rounds=40) if fast else {}
    model = StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=physics_translator(shape_model), **rounds).fit(d)
    neutral = model.predict_at_rho(d, 1.0)
    scaler = PlusScaler().fit(d.assign(x=neutral["xrv"].to_numpy()), "x")
    scores = counterfactual_scores(d, model, scaler, rho_a=RHO_HARP_HELU, rho_b=1.0)
    n_boot = 100 if fast else 500
    min_n = 20 if fast else 500
    by_shape = delta_table(scores, d, "shape", n_boot=n_boot, min_n=min_n)
    by_family = delta_table(scores, d, "pitch_family", n_boot=n_boot, min_n=min_n)
    league = float(scores["delta_stuff"].mean())

    # triangulation: counterfactual at the Extreme bucket's air vs what the same pitches did in Extreme games
    rho_ext = float(d.loc[d.altitude_category.astype(str) == "Extreme Altitude", "rho"].median())
    cf_ext = counterfactual_scores(d, model, scaler, rho_a=rho_ext, rho_b=1.0)
    env = model.predict_components(d)["xrv"].to_numpy()
    sd = float(np.mean([v["sd"] for k, v in scaler.stats.items() if k != "__all__"]))
    obs = d.assign(stuff_env=scaler.transform(d.assign(x=env), "x").to_numpy(),
                   rv_x_as_plus=-10 * d["rv_x"] / sd)
    w = within_pitcher_observed(obs, ["stuff_env", "rv_x_as_plus", "is_whiff"], by="pitch_family",
                                min_n=10 if fast else 30, n_boot=n_boot)
    w = w.pivot_table(index="pitch_family", columns="metric", values="extreme_minus_no").reset_index()
    cf = cf_ext.groupby(d["pitch_family"].astype(str))["delta_stuff"].mean().rename("counterfactual_delta").reset_index()
    tri = cf.merge(w, on="pitch_family", how="left").rename(columns={
        "stuff_env": "observed_model_delta", "rv_x_as_plus": "observed_results_delta_plus", "is_whiff": "observed_whiff_delta"})
    tri["rho_extreme"] = rho_ext
    tri["same_sign_as_model"] = np.sign(tri["counterfactual_delta"]) == np.sign(tri["observed_model_delta"])

    curves = altitude_curve(d, model, scaler, "shape", sample=5_000 if fast else 60_000)
    if write_reports:
        REPORTS.mkdir(parents=True, exist_ok=True)
        by_shape.round(4).to_csv(REPORTS / "delta_by_shape.csv", index=False)
        by_family.round(4).to_csv(REPORTS / "delta_by_family.csv", index=False)
        tri.round(4).to_csv(REPORTS / "triangulation.csv", index=False)
        curves.round(4).to_csv(REPORTS / "altitude_curves.csv", index=False)
        _forest(by_shape, league, REPORTS / "forest_by_shape.png")
        _curves(curves, "shape", REPORTS / "altitude_curves.png")
    return {"by_shape": by_shape, "by_family": by_family, "triangulation": tri, "curves": curves, "league": league,
            "model": model, "scaler": scaler, "scores": scores}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    from stuffplus.io import load_raw

    shape_model, d = prepare(schema.clean(load_raw()))
    res = run(shape_model, d, fast=args.fast)
    cols = ["shape", "pitches", "delta_stuff", "delta_lo", "delta_hi", "delta_ivb_in", "delta_hb_arm_in",
            "delta_whiff_pct", "delta_contact_runs", "verdict"]
    print(f"league mean delta {res['league']:+.2f} at rho {RHO_HARP_HELU}")
    print(res["by_shape"][cols].round(3).to_string(index=False))
    print(res["triangulation"].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
