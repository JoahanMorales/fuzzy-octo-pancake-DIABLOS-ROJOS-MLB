"""python -m analysis.physics_v2.run  (HACK-041, ~10 min).

Aerodynamics per pitch (C_D, C_L, spin parameter S, Reynolds) by family and altitude bucket, the split of the lift
gap at altitude, Magnus elasticity vs air density within the same pitch, and a check of the RK4 flight engine
against the observed Extreme − No changes (HACK-004). Writes reports/physics_v2/ (aggregates), physics.json for
the browser engine (HACK-042) and a README built from the CSVs.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from stuffplus import config
from stuffplus.features.shapes import fit_shapes
from stuffplus.physics import coefficients as co
from stuffplus.physics.constants import RHO_HARP_HELU, RHO_HARP_HELU_BAROMETRIC
from stuffplus.physics.flight import DT, K_SEA, Release, fly

OUT = config.REPORTS_DIR / "physics_v2"
NO, EXT = "No Altitude", "Extreme Altitude"


def load_frame() -> pd.DataFrame:
    main = config.main_checkout_root()
    cache = (main / "artifacts" if main else config.ARTIFACTS_DIR) / "tuning" / "frame_pitching.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    from analysis.altitude_delta.run import prepare
    from stuffplus.io import load_raw
    from stuffplus.schema import clean

    return prepare(clean(load_raw()))[1]


def flight_check(t: pd.DataFrame, elasticity: dict, observed: pd.DataFrame) -> pd.DataFrame:
    """Median four-seamer / sinker thrown at the two buckets' median ρ̂: predicted vs observed ΔIVB and Δ plate mph."""
    rows = []
    for fam in ("Four-Seam", "Sinker"):
        g = t[t.pitch_family == fam].set_index("bucket")
        if NO not in g.index or EXT not in g.index:
            continue
        rel = Release(velo_mph=float(g.loc[NO, "velo"]), ivb_in=float(g.loc[NO, "ivb"]), hb_in=float(g.loc[NO, "hb"]),
                      cd=float(g.loc[NO, "cd"]))
        obs = observed[observed.pitch_family == fam].set_index("outcome")
        for label, e in (("física de libro (elasticidad 1)", 1.0), ("elasticidad medida", elasticity.get(fam, 1.0))):
            a, b = fly(rel, float(g.loc[NO, "rho"]), e), fly(rel, float(g.loc[EXT, "rho"]), e)
            rows.append(dict(pitch_family=fam, model=label, elasticity=e, pred_delta_ivb=b.ivb_in - a.ivb_in,
                             obs_delta_ivb=float(obs.loc["ivb", "delta"]), pred_delta_plate_mph=b.plate_mph - a.plate_mph,
                             obs_delta_plate_mph=float(obs.loc["plate_velo", "delta"])))
    return pd.DataFrame(rows)


def main() -> None:
    d = load_frame().reset_index(drop=True)
    shape_model, _ = fit_shapes(d)
    c = co.coefficients(d)
    d = d.join(c[["drag_acc", "magnus_acc", "cd", "cl", "S", "Re", "spin_eff"]])
    t = co.bucket_table(d)
    mov = d.groupby([d.pitch_family.astype(str), d.altitude_category.astype(str)], observed=True).agg(
        ivb=("InducedVertBreak", "median"), hb=("hb_arm", "median")).reset_index().rename(
        columns={"altitude_category": "bucket"})
    t = t.merge(mov, on=["pitch_family", "bucket"], how="left")
    shs = co.cl_vs_s(d)
    slope = shs["b"]
    bias = RHO_HARP_HELU_BAROMETRIC / RHO_HARP_HELU
    gap = co.gap_decomposition(t, slope, bias)
    cdre = co.cd_vs_re(d)
    # seam-shifted-wake test on the most efficient four-seamers, chosen on half of their sea-level games. The spec
    # asked for >= 95 % efficiency; with efficiency inferred from C_L (Nathan) almost no four-seamer reaches it
    # (median about 0.63), so the test uses the top 10 % of pitch identities and reports the threshold.
    fs4 = d[d.pitch_family.astype(str) == "Four-Seam"]
    n95 = len(co.efficient_pitches(fs4)[0])
    keep, held, thr = co.efficient_pitches(fs4, min_eff=None, top_share=0.10)
    eff = fs4[held]
    t_eff = co.bucket_table(eff)
    gap_eff = co.gap_decomposition(t_eff, slope, bias) if len(t_eff) else pd.DataFrame()
    if len(gap_eff):
        gap_eff = gap_eff.assign(pitch_identities=len(keep), pitches=len(eff), eff_threshold=thr,
                                 identities_at_95=n95, eff_median_sea=float(fs4[fs4.altitude_category.astype(str) == NO].spin_eff.median()))
    el = co.magnus_elasticity(d)
    observed = pd.read_csv(config.REPORTS_DIR / "physics" / "delta_extreme_vs_no.csv")
    check = flight_check(t, dict(zip(el.pitch_family, el.elasticity)), observed)

    OUT.mkdir(parents=True, exist_ok=True)
    t.round(5).to_csv(OUT / "coefficients_by_bucket.csv", index=False)
    gap.round(3).to_csv(OUT / "lift_gap.csv", index=False)
    pd.DataFrame([shs]).round(5).to_csv(OUT / "cl_vs_s.csv", index=False)
    cdre.round(5).to_csv(OUT / "cd_vs_re.csv", index=False)
    t_eff.round(5).to_csv(OUT / "coefficients_efficient_fourseam.csv", index=False)
    gap_eff.round(3).to_csv(OUT / "lift_gap_efficient_fourseam.csv", index=False)
    el.round(4).to_csv(OUT / "magnus_elasticity.csv", index=False)
    check.round(3).to_csv(OUT / "flight_check.csv", index=False)
    sea = t[t.bucket == NO].set_index("pitch_family")
    physics = {
        "model_version": "physics_v2",
        "translator": {"formula": "y_to = y * (1 + k*(rho_to - rho_from) / (1 + k*(rho_from - rho_ref)))",
                       "rho_ref": shape_model.rho_ref,
                       "k": {f: {"ivb": float(v["ivb"]), "hb": float(v["hb"])} for f, v in shape_model.rho_effect.items()}},
        "flight": {"dt": DT, "k_sea": K_SEA, "cd_sea": {f: float(r.cd) for f, r in sea.iterrows()},
                   "magnus_elasticity": {r.pitch_family: float(r.elasticity) for _, r in el.iterrows()}},
        "rho": {"harp_helu": RHO_HARP_HELU, "harp_helu_barometric": RHO_HARP_HELU_BAROMETRIC},
    }
    (OUT / "physics.json").write_text(json.dumps(physics, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(readme(t, gap, el, check, shs, bias, cdre, gap_eff), encoding="utf-8")
    print("wrote", OUT, flush=True)


def readme(t, gap, el, check, shs, bias, cdre, gap_eff) -> str:
    fs = t[t.pitch_family == "Four-Seam"].set_index("bucket")
    L = ["# Física v2: coeficientes, brecha de sustentación y vuelo RK4 (HACK-041)", "",
         "Generado por `python -m analysis.physics_v2.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.", "",
         "Del ajuste de 9 parámetros de cada lanzamiento salen el arrastre y la fuerza de Magnus; con la densidad de cada "
         "juego se convierten en C_D y C_L. El parámetro de giro es S = Rω/v (Nathan et al. 2006) y el número de Reynolds "
         "Re = ρvD/μ (Smith y Sciacchitano 2022). La densidad por juego se calibra con el arrastre de las rectas (Kagan y "
         "Nathan 2014), así que el C_D de las rectas es casi igual en todos los parques por construcción.", "",
         "## Coeficientes por bucket (`coefficients_by_bucket.csv`, medianas)", "",
         "| Familia | Bucket | ρ̂ | C_D [IC 95 %] | C_L [IC 95 %] | S | Re (miles) |", "|---|---|---|---|---|---|---|"]
    for _, r in t.sort_values(["pitch_family", "bucket"]).iterrows():
        L.append(f"| {r.pitch_family} | {r.bucket} | {r.rho:.3f} | {r.cd:.3f} [{r.cd_lo:.3f}, {r.cd_hi:.3f}] | "
                 f"{r.cl:.3f} [{r.cl_lo:.3f}, {r.cl_hi:.3f}] | "
                 f"{r.S:.3f} | {r.Re / 1000:.0f} |")
    L += ["", "## C_L contra S en la forma SHS (`cl_vs_s.csv`)", "",
          f"Sawicki, Hubbard y Stronge (2003): C_L = 1.5 S para S < 0.1 y una recta a + b S arriba. Ajustada en rectas sin "
          f"altitud: a = {shs['a']:.3f}, b = {shs['b']:.3f} [IC 95 % {shs['b_lo']:.3f}, {shs['b_hi']:.3f}] con "
          f"{shs['n_above']:,} lanzamientos sobre S = 0.1 ({shs['n_below']:,} debajo). La literatura da a = "
          f"{shs['a_literature']:.2f}, b = {shs['b_literature']:.2f}; nuestra pendiente es menor porque S usa el giro total "
          "(el giro de bala no levanta).",
          "", "## C_D contra Reynolds (`cd_vs_re.csv`)", "",
          "Pendiente de C_D contra Re (por 10^5) dentro de cada familia y bucket, con IC por pitcher. Negativa = la crisis "
          "de arrastre (C_D baja cuando Re sube).", "",
          "| Familia | Bucket | Pendiente [IC 95 %] | Re p10-p90 (miles) | Lanzamientos |", "|---|---|---|---|---|"]
    for _, r in cdre.sort_values(["pitch_family", "bucket"]).iterrows():
        L.append(f"| {r.pitch_family} | {r.bucket} | {r.slope_per_1e5:+.4f} [{r.slope_lo:+.4f}, {r.slope_hi:+.4f}] | "
                 f"{r.re_p10 / 1000:.0f}-{r.re_p90 / 1000:.0f} | {int(r.pitches):,} |")
    g4 = gap.set_index("pitch_family").loc["Four-Seam"]
    L += ["", "## ¿Por qué cae la sustentación en altura? (`lift_gap.csv`)", "",
          f"El C_L de la recta baja {abs(g4.gap_pct):.1f} % en altitud extrema. Lo separamos en tres partes:", "",
          f"- **Parámetro de giro:** S casi no cambia ({fs.loc[NO, 'S']:.3f} contra {fs.loc[EXT, 'S']:.3f}); con la pendiente "
          f"medida de C_L contra S ({slope:.3f}) explica {g4.explained_by_spin_param_pct:+.1f} %. **La hipótesis de la "
          "literatura (menor S en altura) no explica la brecha en estos datos.**",
          f"- **Sesgo de densidad:** si la densidad real del Harp Helú es la barométrica ({RHO_HARP_HELU_BAROMETRIC:.3f}) y no "
          f"la calibrada con el arrastre ({RHO_HARP_HELU:.3f}), el C_L calculado sale bajo por {100 * (bias - 1):+.1f} %. "
          "Eso implica que el C_D sube en aire más delgado (menor Reynolds); lo apoya que en los lanzamientos lentos "
          "(menor Re) el C_D sí sube en altitud (tabla de arriba).",
          f"- **Residuo sin explicar:** {g4.residual_pct:+.1f} %: puede ser un efecto real del régimen de Reynolds sobre C_L o "
          "calibración de Trackman por parque; se reporta como hipótesis.", "",
          "| Familia | Brecha de C_L | Por parámetro de giro | Por sesgo de densidad | Residuo |", "|---|---|---|---|---|"]
    for _, r in gap.iterrows():
        L.append(f"| {r.pitch_family} | {r.gap_pct:+.1f} % | {r.explained_by_spin_param_pct:+.1f} % | "
                 f"{r.explained_by_density_bias_pct:+.1f} % | {r.residual_pct:+.1f} % |")
    if len(gap_eff):
        e4 = gap_eff.iloc[0]
        L += ["", "## Prueba de estela desplazada por costura (`lift_gap_efficient_fourseam.csv`)", "",
              f"La tarea pedía rectas con eficiencia de giro de 95 % o más, pero con la eficiencia inferida del C_L (Nathan) "
              f"solo {int(e4.identities_at_95)} identidades llegan ahí (mediana a nivel del mar {e4.eff_median_sea:.2f}). "
              f"Usamos el 10 % más eficiente: eficiencia de {e4.eff_threshold:.2f} o más ({int(e4.pitch_identities):,} "
              f"identidades, {int(e4.pitches):,} lanzamientos). La eficiencia se elige con la mitad de sus juegos a nivel del mar y se mide "
              "con la otra mitad, para no seleccionar sobre el mismo ruido. Con casi todo el giro transversal, la estela "
              "desplazada por costura debería pesar poco; si el residuo sigue igual, no es la explicación.", "",
              f"- Brecha de C_L {e4.gap_pct:+.1f} % (todas las rectas: {g4.gap_pct:+.1f} %); parámetro de giro "
              f"{e4.explained_by_spin_param_pct:+.1f} %, sesgo de densidad {e4.explained_by_density_bias_pct:+.1f} %, residuo "
              f"{e4.residual_pct:+.1f} % (todas: {g4.residual_pct:+.1f} %).",
              "- Medido: la brecha y su reparto. Hipótesis (no medida directamente): el origen físico del residuo."]
    L += ["", "## Elasticidad del Magnus contra la densidad (`magnus_elasticity.csv`)", "",
          "Dentro del mismo lanzamiento (pitcher × temporada × identidad) y entre juegos: pendiente de log(aceleración de "
          "Magnus) contra log(ρ̂). Con C_L constante la física predice 1.", "",
          "| Familia | Elasticidad [IC 95 %] | Lanzamientos-juego |", "|---|---|---|"]
    for _, r in el.iterrows():
        L.append(f"| {r.pitch_family} | {r.elasticity:.2f} [{r.lo:.2f}, {r.hi:.2f}] | {int(r.pitch_games):,} |")
    L += ["", "## El integrador RK4 contra lo observado (`flight_check.csv`)", "",
          "Recta y sinker medianos lanzados con la ρ̂ mediana de cada bucket, contra el cambio observado dentro del mismo "
          "pitcher (HACK-004):", "", "| Familia | Modelo | ΔIVB predicho | ΔIVB observado | Δ mph al plato predicho | observado |",
          "|---|---|---|---|---|---|"]
    for _, r in check.iterrows():
        L.append(f"| {r.pitch_family} | {r.model} | {r.pred_delta_ivb:+.2f} in | {r.obs_delta_ivb:+.2f} in | "
                 f"{r.pred_delta_plate_mph:+.2f} | {r.obs_delta_plate_mph:+.2f} |")
    L += ["", "`physics.json` lleva la traducción por familia (la misma del paper) y los coeficientes del vuelo para el "
          "motor del navegador (HACK-042).", "",
          "## Límites", "- La temperatura y la humedad no están en los datos; μ del aire se fija en 1.81e-5 Pa·s.",
          "- S usa el giro total (incluye giro de bala), lo que aplana la pendiente de C_L contra S.",
          "- La eficiencia de giro se infiere del C_L con la relación de Nathan (Trackman no da el giro de bala), así que "
          "elegir rectas eficientes favorece C_L alto; por eso se elige con una mitad de juegos y se mide con la otra.",
          "- El sesgo de densidad usa la densidad barométrica del Harp Helú para todo el bucket extremo (aproximación).", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
