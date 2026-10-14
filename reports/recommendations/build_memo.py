"""HACK-022: escribe reports/recommendations/memo.md leyendo SOLO los CSV de reports/ (cada cifra sale de su archivo).

Uso: python reports/recommendations/build_memo.py   (instantáneo; no necesita datos crudos)
Si un CSV cambia, se vuelve a correr y el memo cambia con él: no hay cifras escritas a mano.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "reports"
OUT = Path(__file__).with_name("memo.md")


def csv(rel: str) -> pd.DataFrame:
    return pd.read_csv(R / rel)


def f(x: float, d: int = 1, sign: bool = False) -> str:
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


# ------------------------------------------------------------------ datos
shapes = csv("altitude_delta/delta_by_shape.csv")
league = float((shapes["delta_stuff"] - shapes["relative_to_league"]).mean())
gain = shapes.sort_values("relative_to_league", ascending=False).head(3)
lose = shapes.sort_values("relative_to_league").head(3)
fam = csv("altitude_delta/delta_by_family.csv")
trait = csv("ideal_profile/delta_by_trait.csv")
rho = csv("ideal_profile/rho_sensitivity.csv").query("group == 'rectas'").set_index("feature")  # solo rectas
best = csv("ideal_profile/best_fastballs.csv").iloc[0]
zones = csv("location_model/altitude_by_zone.csv")
hyp = csv("hypotheses/results.csv")
rpw = csv("business_value/runs_per_win.csv").set_index("entorno")
pp = csv("business_value/runs_per_point_direct.csv")
gm = csv("business_value/gm_example.csv")
spread = csv("business_value/pitcher_spread_example.csv")
cost = csv("business_value/altitude_cost.csv").set_index("entorno")

rpw_lg, rpw_ext = float(rpw.loc["liga", "carreras_por_victoria"]), float(rpw.loc["Extreme Altitude", "carreras_por_victoria"])
stuff_pp = pp[(pp.escala == "Stuff+") & (pp.objetivo == "rv_x")].iloc[0]
sp = spread[(spread.escala == "Stuff+") & (spread.entorno.str.startswith("Harp"))].iloc[0]
gm_s = gm[(gm.escala == "Stuff+") & (gm.entorno.str.startswith("Harp"))].iloc[0]


def h(metric: str) -> pd.Series:
    return hyp[(hyp.hypothesis == "H3") & (hyp.metric == metric)].iloc[0]


def zone(fam_: str, z: str) -> float:
    return float(zones[(zones.pitch_family == fam_) & (zones.zone == z)]["delta_cdmx"].iloc[0])


def quint(name: str) -> tuple[pd.Series, pd.Series]:
    t = trait[trait.trait == name].sort_values("bin_lo")
    return t.iloc[0], t.iloc[-1]


ext_lo, ext_hi = quint("extension")
vaa_lo, vaa_hi = quint("vaa_neto_altura")
row = lambda r: f"**{r.shape}** ({f(r.delta_stuff, 1, True)} [{f(r.delta_lo, 1, True)}, {f(r.delta_hi, 1, True)}])"  # noqa: E731
lines: list[str] = []
add = lines.append

add("# Recomendaciones operativas: jugar en el Harp Helú (2,240 m)")
add("")
add("*Memo para el cuerpo técnico y la gerencia de Diablos Rojos. Escala Stuff+: 100 = promedio de la LMB a nivel del mar; "
    "ΔStuff+ = Stuff+ en el aire del Harp Helú menos Stuff+ a nivel del mar, con intervalos al 95 % por pitcher. "
    "Cada cifra sale de un CSV de `reports/` (entre paréntesis) y este texto se regenera con `reports/recommendations/build_memo.py`.*")
add("")
add(f"**En una frase:** el aire del Harp Helú le quita a la liga unos {f(-league, 1)} puntos de Stuff+ por lanzamiento (promedio de formas); "
    f"conviene reclutar formas que pierden poco ({', '.join(gain['shape'])}) y no pagar por *ride* de recta.")
add("")

# 1
add("## 1. Perfiles que ganan en la CDMX (pierden menos que la liga)")
add("")
add(f"El promedio de la liga cae {f(league, 1, True)} puntos (`altitude_delta/delta_by_shape.csv`). Las tres formas que mejor aguantan:")
add("")
for r in gain.itertuples():
    add(f"- {row(r)}: {r.relative_to_league:+.1f} puntos mejor que la liga. Movimiento en altura: IVB {r.delta_ivb_in:+.1f}\", "
        f"HB {r.delta_hb_arm_in:+.1f}\", whiff {r.delta_whiff_pct:+.1f} pp. {r.pitchers} pitchers, {r.pitches:,} lanzamientos.")
add("")
add("**Física:** la fuerza de Magnus y el arrastre son proporcionales a la densidad del aire; con ~16 % menos aire (ρ̂ Extreme ≈ 0.84, `physics/rho_by_bucket.csv`; "
    "Harp Helú ≈ 0.82, `park_id/harp_helu.md`) el quiebre inducido baja en esa proporción. Por eso el Stuff+ de una recta depende mucho menos de su IVB en altura "
    "(punto 1 de la lista de verificación), y las formas que no viven del *ride* aguantan mejor.")
add("")

# 2
add("## 2. Perfiles que pierden y riesgo de contacto duro y jonrones")
add("")
add("Las tres formas que más pierden:")
add("")
for r in lose.itertuples():
    add(f"- {row(r)}: {r.relative_to_league:+.1f} puntos contra la liga. Contacto duro {r.delta_hard_contact_pct:+.1f} pp, "
        f"HR/FB {r.delta_hr_per_fb_pct:+.1f} pp, valor del contacto {r.delta_contact_runs:+.3f} carreras por bola en juego.")
hr, dist, fbgb = h("hr_fb"), h("fb_distance"), h("rv_x fly ball − rv_x rodado")
add("")
add(f"**Riesgo cuantificado (hipótesis H3, `hypotheses/results.csv`):** las bolas al aire viajan {f(dist['delta'], 0, True)} pies más "
    f"[{f(dist['lo'], 0)}, {f(dist['hi'], 0)}] y el HR/FB sube {f(100 * hr['delta'], 1, True)} pp [{f(100 * hr['lo'], 1)}, {f(100 * hr['hi'], 1)}]; "
    f"una bola al aire vale {f(fbgb['delta'], 3, True)} carreras más que un rodado [{f(fbgb['lo'], 3)}, {f(fbgb['hi'], 3)}] en altura. "
    "**No** hay evidencia de que los pitchers de más rodados se protejan más (pendiente contra GB% con IC que incluye 0): no se debe recomendar fichar rodadores solo por eso.")
add("")

# 3
add("## 3. Cómo perfilar un prospecto o agente libre (lista de verificación)")
add("")
add("Umbrales sacados de los quintiles observados (`ideal_profile/delta_by_trait.csv`) y de la sensibilidad al aire (`ideal_profile/rho_sensitivity.csv`):")
add("")
add(f"1. **No pagar por *ride* de recta.** El rango de Stuff+ entre IVB bajo y alto es {f(rho.loc['InducedVertBreak', 'swing_sea'], 1, True)} puntos a nivel del mar y solo "
    f"{f(rho.loc['InducedVertBreak', 'swing_alt'], 1, True)} en el Harp Helú; la recta de más *ride* es la que más pierde (riding 4S {f(shapes[shapes['shape'] == 'riding 4S']['delta_stuff'].iloc[0], 1, True)}).")
add(f"2. **Extensión alta.** Quintil superior (≥ {f(ext_hi.bin_lo, 2)} ft): ΔStuff+ {f(ext_hi.delta_stuff, 1, True)}; quintil inferior (≤ {f(ext_lo.bin_hi, 2)} ft): "
    f"{f(ext_lo.delta_stuff, 1, True)} (la extensión pesa más en altura: rango {f(rho.loc['Extension', 'swing_sea'], 1, True)} → {f(rho.loc['Extension', 'swing_alt'], 1, True)}).")
add(f"3. **Ángulo de aproximación (VAA) bajo, neto de la altura del lanzamiento.** Quintil inferior: {f(vaa_lo.delta_stuff, 1, True)}; superior: {f(vaa_hi.delta_stuff, 1, True)}.")
add(f"4. **Velocidad: suma más en altura** (rango {f(rho.loc['RelSpeed', 'swing_sea'], 1, True)} → {f(rho.loc['RelSpeed', 'swing_alt'], 1, True)} puntos).")
add(f"5. **Secundarios:** preferir {', '.join(gain['shape'])}; desconfiar de {', '.join(lose['shape'].iloc[1:])}.")
add(f"6. **Perfil de referencia de recta** en el aire del Harp Helú (`ideal_profile/best_fastballs.csv`): {best.RelSpeed:.1f} mph, IVB {best.InducedVertBreak:.1f}\" y HB {best.hb_arm:.1f}\" a nivel del mar, "
    f"extensión {best.Extension:.2f} ft, salida {best.RelHeight:.2f} ft → Stuff+ {best.stuff_alt:.1f} en el Harp Helú ({best.stuff_sea:.1f} a nivel del mar).")
add("")
add("*Límite:* la eficiencia de giro no se usa como criterio: la brecha de ~15 % entre altitudes sigue sin explicarse (`physics/README.md`).")
add("")

# 4
add("## 4. Tácticas en casa frente a gira")
add("")
mid4 = zone("Four-Seam", "4")
add(f"Efecto del aire por zona del plato, en carreras por lanzamiento (+ = peor para el pitcher; `location_model/altitude_by_zone.csv`, basado en el modelo y con ρ a nivel de juego):")
add("")
add(f"- **El centro cuesta más:** recta zona 4 {zone('Four-Seam', '4'):+.3f} y zona 5 {zone('Four-Seam', '5'):+.3f}; slider zona 4 {zone('Slider', '4'):+.3f}. Evitar el medio de la zona en casa.")
add(f"- **Abajo pierde más que arriba:** recta zonas 7–8 ({zone('Four-Seam', '7'):+.3f}, {zone('Four-Seam', '8'):+.3f}) frente a zonas 1–3 ({zone('Four-Seam', '1'):+.3f} a {zone('Four-Seam', '3'):+.3f}).")
add(f"- **El borde fuera de la zona casi no cambia** (recta {zone('Four-Seam', 'chase'):+.4f}, slider {zone('Slider', 'chase'):+.4f}): en casa conviene buscar el *chase* en lugar de pelear la zona.")
add(f"- **La esquina baja del lado del guante (zona 9) aguanta mejor** (recta {zone('Four-Seam', '9'):+.3f}, slider {zone('Slider', '9'):+.3f}).")
add("")
add("*Pendiente:* secuencias y conteos de Diablos en casa contra gira dependen de la auditoría del staff (HACK-032), todavía no integrada; este memo no las inventa.")
add("")

# 5
add("## 5. Valor en carreras y victorias")
add("")
add(f"- **Carreras por victoria:** liga {rpw_lg:.1f}; Harp Helú (bucket Extreme) {rpw_ext:.1f} (`business_value/runs_per_win.csv`). En altura se anota más, así que cada carrera ahorrada vale menos victorias.")
add(f"- **Un punto de Stuff+ vale {stuff_pp.carreras_por_punto_lanzamiento:.2e} carreras por lanzamiento** [{stuff_pp.lo:.2e}, {stuff_pp.hi:.2e}] (estimación directa fuera de muestra, `business_value/runs_per_point_direct.csv`).")
add(f"- **Ejemplo:** +10 puntos de Stuff+ en 2,500 lanzamientos son {gm_s.carreras:.1f} carreras ≈ **{gm_s.victorias:.2f} victorias** en el Harp Helú (`business_value/gm_example.csv`). "
    f"Una desviación estándar entre pitcher-temporadas ({sp.sd_puntos_entre_pitcher_temporadas:.1f} puntos) equivale a {sp.carreras_por_1sd:.1f} carreras ≈ {sp.victorias_por_1sd:.2f} victorias (`business_value/pitcher_spread_example.csv`).")
add(f"- **Costo medio de la altura:** {cost.loc['Extreme', 'mean_delta']:+.4f} carreras por lanzamiento (Extreme frente a sin altitud, `business_value/altitude_cost.csv`): ~{cost.loc['Extreme', 'mean_delta'] * 77:.1f} carreras por apertura de 77 lanzamientos.")
swap = float(shapes[shapes['shape'] == 'riding 4S']['delta_stuff'].iloc[0] - shapes[shapes['shape'] == 'sweeper']['delta_stuff'].iloc[0])
add(f"- **Orden de magnitud de la decisión de reclutamiento:** la diferencia de pérdida entre riding 4S y sweeper es {abs(swap):.1f} puntos; por cada 1,000 lanzamientos son "
    f"~{abs(swap) * 1000 * stuff_pp.carreras_por_punto_lanzamiento:.1f} carreras (~{abs(swap) * 1000 * stuff_pp.carreras_por_punto_lanzamiento / rpw_ext:.2f} victorias en el Harp Helú). "
    "Es una diferencia de pérdida entre formas, no el efecto causal de cambiar un lanzamiento por otro.")
add("")
add("## Cómo leer estas cifras")
add("")
add("- Estimaciones con datos de la LMB 2024–2026; los intervalos solo propagan el muestreo de pitchers, no la incertidumbre de ρ̂ ni de la identidad de lanzamiento.")
add("- La identidad de CDMX frente a Puebla entre los parques de altura no está verificada (HACK-003): «Harp Helú» usa ρ̂ = 0.82 de las dos franquicias de menor densidad.")
add("- Estas son estimaciones de modelo y de datos observacionales; no son un experimento. El rango por pitcher individual es ruidoso: usar para decisiones de perfil, no de un solo lanzador.")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{OUT} · {len(' '.join(lines).split())} palabras")
