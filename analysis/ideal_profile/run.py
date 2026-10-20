"""Ideal physical profile for Diablos Rojos (HACK-017): what maximizes Stuff+ at the Harp Helú's air density.

    python analysis/ideal_profile/run.py          # real data
    python analysis/ideal_profile/run.py --fast   # quick check

Uses the production Stuff+ (``fit_production_stuff``, as analysis/altitude_delta) on HACK-015's setup (altitude-invariant ``pitch_family`` + fitted physics translation, ``stuffplus.altitude``).
Reports in reports/ideal_profile/ (aggregates only, no pitcher ids):
  pdp_2d.csv · rho_sensitivity.csv · h_statistic.csv · shap_rho_interaction.csv   which traits matter more in thin air
  delta_by_trait.csv        counterfactual ΔStuff+ by VAA (net of plate height) and spin-efficiency quintile
  best_fastballs.csv · best_secondaries.csv · best_arsenals.csv · candidates_summary.csv   hull-bounded search
  pdp.png · receta.png · profile.md
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

from stuffplus import config, profile, schema  # noqa: E402
from stuffplus.config import SEED  # noqa: E402
from stuffplus.models.stuff import fit_production_stuff  # noqa: E402
from stuffplus.physics.aero import decompose  # noqa: E402
from stuffplus.physics.constants import RHO_HARP_HELU  # noqa: E402
from stuffplus.scale import PlusScaler  # noqa: E402

REPORTS = config.REPORTS_DIR / "ideal_profile"
RED, BLACK = "#D71920", "#111111"
SHOW = ["RelSpeed", "InducedVertBreak", "hb_arm", "SpinRate", "Extension", "RelHeight", "arm_angle"]


def _altitude_run():
    spec = importlib.util.spec_from_file_location("alt_run", ROOT / "analysis" / "altitude_delta" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fit(d: pd.DataFrame, shape_model, fast: bool):
    from stuffplus.altitude import physics_translator

    rounds = dict(class_rounds=60, contact_rounds=40) if fast else {}
    model = fit_production_stuff(d, translate=physics_translator(shape_model), k_inner=2 if fast else 3, **rounds)
    scaler = PlusScaler().fit(d.assign(x=model.predict_at_rho(d, 1.0)["xrv"].to_numpy()), "x")
    return model, scaler


def _shap(model, scaler, d: pd.DataFrame, fast: bool) -> pd.DataFrame:
    from stuffplus.models.common import as_model_frame

    sample = d.sample(min(len(d), 5_000 if fast else 60_000), random_state=SEED)
    booster, r2 = model.distill(sample, model.predict_xrv(sample), rounds=60 if fast else 300)
    X = as_model_frame(sample.sample(min(len(sample), 300 if fast else 2_000), random_state=SEED), model.features)
    X["pitch_family"] = X["pitch_family"].cat.codes  # TreeSHAP needs numeric input; same split order as the codes
    pts = 10.0 / scaler.stats["__all__"]["sd"]
    try:
        out = profile.shap_rho_interaction(booster, X, pts)
        out["distill_r2"] = r2
    except Exception as exc:  # categorical splits can break TreeSHAP; the PDP/H-statistic carry the result then
        out = pd.DataFrame({"feature": [], "main_pts": [], "rho_interaction_pts": [], "note": []})
        out.loc[0] = ["(no disponible)", np.nan, np.nan, f"TreeSHAP falló: {type(exc).__name__}"]
    return out


def run(d: pd.DataFrame, model, scaler, fast: bool = False) -> dict:
    sea = profile.to_sea_level(model, d)
    rhos = [1.0, 0.9, RHO_HARP_HELU]
    n_base = 300 if fast else 3_000
    pdps, sens, hs = [], [], []
    for group, mask in (("rectas", profile.is_fastball(sea)), ("secundarios", ~profile.is_fastball(sea))):
        base = sea[mask].sample(min(int(mask.sum()), n_base), random_state=SEED)
        p = profile.pdp_2d(model, scaler, base, profile.PROFILE_FEATURES, rhos, n_grid=5 if fast else 9).assign(group=group)
        pdps.append(p)
        phys = profile.pdp_2d(model, scaler, base, profile.PROFILE_FEATURES, [1.0, RHO_HARP_HELU],
                              n_grid=5 if fast else 9, direct=False)
        p_s = profile.rho_sensitivity(p, RHO_HARP_HELU)
        f_s = profile.rho_sensitivity(phys, RHO_HARP_HELU)[["feature", "swing_alt", "verdict"]]
        sens.append(p_s.merge(f_s.rename(columns={"swing_alt": "swing_alt_physics_only", "verdict": "verdict_physics_only"}),
                              on="feature").assign(group=group))
        hs.append(profile.h_statistic(p).assign(group=group))
    pdp, sens, hstat = pd.concat(pdps), pd.concat(sens), pd.concat(hs)
    shap_tab = _shap(model, scaler, d, fast)

    # traits outside the model: counterfactual ΔStuff+ by VAA (net of plate height) and spin efficiency, fastballs
    fb = sea[profile.is_fastball(sea)].sample(min(int(profile.is_fastball(sea).sum()), 5_000 if fast else 60_000), random_state=SEED)
    delta = pd.Series(profile.stuff_plus_at(model, scaler, fb, RHO_HARP_HELU) - profile.stuff_plus_at(model, scaler, fb, 1.0), index=fb.index)
    raw = d.loc[fb.index]
    spin_eff = decompose(raw, rho=raw["rho"].to_numpy(float))["spin_eff"]
    n_boot = 100 if fast else 300
    by_trait = pd.concat([
        profile.delta_by_bins(delta, profile.vaa_adjusted(raw), raw["pitcher_anon_id"], n_boot=n_boot, name="vaa_neto_altura"),
        profile.delta_by_bins(delta, spin_eff, raw["pitcher_anon_id"], n_boot=n_boot, name="eficiencia_giro"),
        profile.delta_by_bins(delta, fb["RelSpeed"], raw["pitcher_anon_id"], n_boot=n_boot, name="velocidad"),
        profile.delta_by_bins(delta, fb["Extension"], raw["pitcher_anon_id"], n_boot=n_boot, name="extension"),
    ], ignore_index=True)

    cents = profile.centroids(sea, min_n=20 if fast else 100)
    best_fb, fb_stats = profile.best_fastballs(model, scaler, cents, RHO_HARP_HELU, top=10)
    top_fb = best_fb.iloc[0]
    sec = profile.secondaries_given_fastball(model, scaler, cents, top_fb, RHO_HARP_HELU)
    ars = profile.best_arsenals(profile.score_profiles(model, scaler, cents, RHO_HARP_HELU))
    summary = pd.DataFrame([
        {"item": "perfiles_recta_en_casco", "value": fb_stats["candidates"]},
        {"item": "spearman_recta_altitud_vs_mar", "value": fb_stats["spearman_alt_vs_sea"]},
        {"item": "top10_recta_coinciden", "value": fb_stats["top_overlap"]},
        {"item": "spearman_recta_solo_fisica_vs_mar", "value": fb_stats["spearman_physics_only_vs_sea"]},
        {"item": "secundarios_en_casco_con_mejor_recta", "value": len(sec)},
        {"item": "arsenales_3", "value": len(ars)},
        {"item": "spearman_arsenal_altitud_vs_mar", "value": float(ars["stuff_alt"].corr(ars["stuff_sea"], method="spearman")) if len(ars) else np.nan},
        {"item": "rho_harp_helu", "value": RHO_HARP_HELU},
    ])
    keep = ["pitch_family"] + profile.PROFILE_FEATURES + ["usage", "stuff_sea", "stuff_alt", "delta"]
    return {"pdp": pdp, "sens": sens, "hstat": hstat, "shap": shap_tab, "by_trait": by_trait,
            "best_fb": best_fb, "best_fb_out": best_fb[keep + ["rank_alt", "rank_sea"]].head(15),
            "sec_out": sec[keep + profile.DIFF_FEATURES].groupby("pitch_family", group_keys=False).head(3),
            "ars_out": ars.drop(columns=["pitcher_anon_id"]).head(15) if len(ars) else ars,
            "ars": ars, "summary": summary, "top_fb": top_fb}


def _plots(res: dict, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pdp = res["pdp"][res["pdp"].group == "rectas"]
    fig, axes = plt.subplots(2, 4, figsize=(13, 6))
    for ax, f in zip(axes.flat, SHOW):
        g = pdp[pdp.feature == f]
        for rho, color, label in ((1.0, BLACK, "nivel del mar"), (RHO_HARP_HELU, RED, "Harp Helú")):
            s = g[np.isclose(g.rho, rho)].sort_values("value")
            ax.plot(s.value, s.stuff_plus, color=color, marker="o", ms=3, label=label)
        ax.set_title(profile.LABELS[f], fontsize=9)
    axes.flat[-1].axis("off")
    axes.flat[0].legend(fontsize=8)
    fig.suptitle("Rectas: Stuff+ medio al fijar un rasgo (dependencia parcial), mar vs Harp Helú", fontsize=11)
    fig.tight_layout()
    fig.savefig(out / "pdp.png", dpi=120)
    plt.close(fig)

    fb = res["best_fb"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, col, title, cmap in ((axes[0], "stuff_alt", "Stuff+ en el aire del Harp Helú", "Reds"),
                                 (axes[1], "delta", "ΔStuff+ (Harp Helú − nivel del mar)", "RdGy")):
        hb = ax.hexbin(fb.RelSpeed, fb.InducedVertBreak, C=fb[col], gridsize=14, mincnt=3, cmap=cmap, reduce_C_function=np.mean)
        fig.colorbar(hb, ax=ax)
        ax.set_xlabel("velocidad (mph)")
        ax.set_ylabel("IVB a nivel del mar (in)")
        ax.set_title(title, fontsize=10)
    fig.suptitle("Receta para scouts: perfiles de recta observados (promedio por hexágono, ≥ 3 perfiles)", fontsize=11)
    fig.tight_layout()
    fig.savefig(out / "receta.png", dpi=120)
    plt.close(fig)


def _extremes(tr: pd.DataFrame, trait: str):
    """First and last quintile of a trait in delta_by_trait, and whether their 95 % intervals overlap."""
    t = tr[tr.trait == trait].sort_values("bin_lo")
    lo, hi = t.iloc[0], t.iloc[-1]
    overlap = not (lo.delta_hi < hi.delta_lo or hi.delta_hi < lo.delta_lo)
    return lo, hi, overlap


def _checklist(fbs: pd.DataFrame, tr: pd.DataFrame) -> list[str]:
    """The recruiting checklist restated from this folder's CSVs, with a robustness read for every rule (HACK-083)."""
    out = ["## Lista de verificación para reclutar (de estos CSV)", ""]
    ivb = fbs.loc["InducedVertBreak"]
    out.append(f"1. **No pagar por *ride* de recta.** El swing de Stuff+ entre IVB bajo y alto es {ivb.swing_sea:+.1f} a nivel del mar "
               f"y {ivb.swing_alt:+.1f} en el Harp Helú ({ivb.swing_alt_physics_only:+.1f} solo con la física): la regla se sostiene.")
    lo, hi, ov = _extremes(tr, "extension")
    out.append(f"2. **Extensión alta.** Quintil superior ΔStuff+ {hi.delta_stuff:+.1f} contra {lo.delta_stuff:+.1f} del inferior "
               f"(brecha {hi.delta_stuff - lo.delta_stuff:+.1f}; {'los IC se traslapan: no es robusta' if ov else 'IC sin traslape: robusta'}).")
    lo, hi, ov = _extremes(tr, "vaa_neto_altura")
    out.append(f"3. **VAA plano, neto de la altura de salida.** Quintil más plano {lo.delta_stuff:+.1f} contra {hi.delta_stuff:+.1f} del más "
               f"inclinado (brecha {lo.delta_stuff - hi.delta_stuff:+.1f}; {'los IC se traslapan: no es robusta' if ov else 'IC sin traslape: robusta'}).")
    v = tr[tr.trait == "velocidad"].sort_values("bin_lo").delta_stuff
    mono = v.is_monotonic_increasing or v.is_monotonic_decreasing
    out.append(f"4. **Velocidad.** ΔStuff+ por quintil: {', '.join(f'{x:+.1f}' for x in v)}; "
               f"{'monótona' if mono else 'no monótona: sin umbral de velocidad'}.")
    return out + [""]


def _md(res: dict) -> str:
    s = res["sens"]
    fbs = s[s.group == "rectas"].set_index("feature")
    more = fbs[fbs.verdict == "importa más en altitud"]
    less = fbs[fbs.verdict == "importa menos en altitud"]
    summ = res["summary"].set_index("item")["value"]
    top = res["best_fb_out"].iloc[0]
    tr = res["by_trait"]
    h = res["hstat"][res["hstat"].group == "rectas"].sort_values("h2_rho", ascending=False)
    lines = [
        "# Perfil físico ideal para Diablos Rojos (HACK-017)", "",
        f"Stuff+ de producción v2 (HACK-057, el mismo de HACK-015; identidad `pitch_family`, traslado físico ajustado). Aire del Harp Helú: ρ = {RHO_HARP_HELU:.3f} "
        "(`RHO_HARP_HELU`). Escala neutral: 100 = promedio LMB a nivel del mar. Cifras copiadas de los CSV de esta carpeta.", "",
        "## Qué rasgos importan más en altitud (`rho_sensitivity.csv`, rectas)", "",
        "Dependencia parcial: el rasgo se fija en una rejilla (cuantiles 5–95 %) con el movimiento definido a nivel del mar, "
        "se traslada al aire de cada ρ con la física de HACK-015 y se puntúa. *Swing* = cambio de Stuff+ entre p5 y p95.", "",
        "Dos vías del aire: **total** (física + rasgo `rho` del modelo) y **solo física** (movimiento trasladado, `rho` del modelo "
        "fijo a nivel del mar). Si el veredicto cambia entre ambas, el efecto viene de lo que el modelo aprendió de los juegos "
        "en altura y no solo de Magnus ∝ ρ.", "",
        "| rasgo | swing mar | swing Harp Helú (total) | veredicto total | swing Harp Helú (solo física) | veredicto solo física |",
        "|---|---:|---:|---|---:|---|",
    ]
    for f, r in fbs.iterrows():
        lines.append(f"| {r.label} | {r.swing_sea:+.2f} | {r.swing_alt:+.2f} | {r.verdict} | "
                     f"{r.swing_alt_physics_only:+.2f} | {r.verdict_physics_only} |")
    ivb = res["pdp"][(res["pdp"].group == "rectas") & (res["pdp"].feature == "InducedVertBreak")]
    ivb = ivb.pivot_table(index="value", columns="rho", values="stuff_plus")
    lines += ["", "IVB de la recta (`pdp_2d.csv`): Stuff+ medio al fijar el IVB a nivel del mar, lanzado en cada aire.", "",
              "| IVB a nivel del mar (in) | " + " | ".join(f"ρ = {r:.3f}" for r in ivb.columns) + " |",
              "|---:|" + "---:|" * len(ivb.columns)]
    for v, r in ivb.iterrows():
        lines.append(f"| {v:.1f} | " + " | ".join(f"{x:.1f}" for x in r) + " |")
    lines += ["", f"- Importan **más** en altitud: {', '.join(more.label) or 'ninguno'}.",
              f"- Importan **menos** en altitud: {', '.join(less.label) or 'ninguno'}.",
              f"- Interacción rasgo × ρ más fuerte (H², `h_statistic.csv`): {h.iloc[0].feature} ({h.iloc[0].h2_rho:.3f}).", "",
              "## Rasgos fuera del modelo (`delta_by_trait.csv`, rectas, IC 95 % por pitcher)", "",
              "| rasgo | quintil | ΔStuff+ | IC 95 % |", "|---|---|---:|---|"]
    for _, r in tr.iterrows():
        lines.append(f"| {r.trait} | [{r.bin_lo:.2f}, {r.bin_hi:.2f}] | {r.delta_stuff:+.2f} | [{r.delta_lo:+.2f}, {r.delta_hi:+.2f}] |")
    lines += ["", "VAA se usa neto de la altura en el plato (residuo por familia). La eficiencia de giro solo ordena lanzamientos: "
              "la brecha de ~15 % entre altitudes (HACK-004) sigue sin explicarse, así que no se presentan sus deltas como hecho.", "",
              "## Mejor recta observada en el aire del Harp Helú (`best_fastballs.csv`)", "",
              f"Perfiles de recta dentro del casco de datos (kNN): {int(summ['perfiles_recta_en_casco'])}. "
              f"Correlación de rangos altitud vs mar: {summ['spearman_recta_altitud_vs_mar']:.3f}; "
              f"coinciden {int(summ['top10_recta_coinciden'])} de las 10 mejores. Solo con la vía física, la correlación es "
              f"{summ['spearman_recta_solo_fisica_vs_mar']:.3f}.", "",
              f"La mejor: {top.pitch_family}, {top.RelSpeed:.1f} mph, IVB {top.InducedVertBreak:.1f}\" y HB {top.hb_arm:.1f}\" a nivel del mar, "
              f"extensión {top.Extension:.2f} ft, salida {top.RelHeight:.2f} ft → Stuff+ {top.stuff_alt:.1f} en el Harp Helú "
              f"({top.stuff_sea:.1f} a nivel del mar, Δ {top.delta:+.1f}).", "",
              "## Mejor secundario dado esa recta (`best_secondaries.csv`) y mejor arsenal de 3 (`best_arsenals.csv`)", "",
              f"Secundarios observados re-anclados a esa recta y dentro del casco conjunto (rasgos + diferencias): {int(summ['secundarios_en_casco_con_mejor_recta'])}. "
              f"Arsenales de 3 pitches observados: {int(summ['arsenales_3'])}; correlación de rangos altitud vs mar "
              f"{summ['spearman_arsenal_altitud_vs_mar']:.3f}.", "",
              "## Receta (`receta.png`)", "",
              "Hexágonos con el Stuff+ medio de perfiles de recta observados (≥ 3 por hexágono) en el aire del Harp Helú y su Δ contra el nivel del mar.", "",
              *_checklist(fbs, tr),
              "## Limitaciones", "",
              "- Perfiles = centroides pitcher-temporada-familia; el Stuff+ de un perfil promedio no es el promedio de sus Stuff+.",
              "- `add_stuff_features` (HACK-010) elige la recta principal por `AutoPitchType`, no por `pitch_family`.",
              "- La interacción SHAP con ρ (`shap_rho_interaction.csv`) mide solo la vía directa del rasgo `rho`; la vía física "
              "(menos Magnus) está en la dependencia parcial.",
              "- Escalas transductivas: identidad, densidad y valores de carrera se ajustan con todos los datos antes de puntuar.",
              "- Los quintiles extremos de velocidad y extensión incluyen lecturas atípicas de Trackman (ver límites en `delta_by_trait.csv`).",
              "- Requiere HACK-015 en `main` (`stuffplus.altitude`, `analysis/altitude_delta`)."]
    return "\n".join(lines) + "\n"


def write(res: dict, out: Path = REPORTS) -> None:
    out.mkdir(parents=True, exist_ok=True)
    res["pdp"].round(4).to_csv(out / "pdp_2d.csv", index=False)
    res["sens"].round(4).to_csv(out / "rho_sensitivity.csv", index=False)
    res["hstat"].round(4).to_csv(out / "h_statistic.csv", index=False)
    res["shap"].round(4).to_csv(out / "shap_rho_interaction.csv", index=False)
    res["by_trait"].round(4).to_csv(out / "delta_by_trait.csv", index=False)
    res["best_fb_out"].round(3).to_csv(out / "best_fastballs.csv", index=False)
    res["sec_out"].round(3).to_csv(out / "best_secondaries.csv", index=False)
    res["ars_out"].round(3).to_csv(out / "best_arsenals.csv", index=False)
    res["summary"].round(4).to_csv(out / "candidates_summary.csv", index=False)
    _plots(res, out)
    (out / "profile.md").write_text(_md(res), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    from stuffplus.io import load_raw

    shape_model, d = _altitude_run().prepare(schema.clean(load_raw()))
    model, scaler = fit(d, shape_model, args.fast)
    res = run(d, model, scaler, fast=args.fast)
    write(res)
    print(res["sens"].round(3).to_string(index=False))
    print(res["summary"].to_string(index=False))


if __name__ == "__main__":
    main()
