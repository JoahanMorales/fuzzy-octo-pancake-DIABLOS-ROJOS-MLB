import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: streamlit solo agrega app/ al path

import pandas as pd
import streamlit as st

from app import theme

LAB = Path(__file__).resolve().parents[2] / "reports" / "design_lab"

theme.setup("Laboratorio")
st.title("Laboratorio de diseño")
theme.demo_badge(False)  # resultados del modelo real (reports/design_lab/), no valores simulados
st.caption("¿Qué ajuste a un lanzamiento gana más Stuff+ en el aire del Harp Helú (2,240 m)? Cada ajuste se acota a lo observado en pitchers comparables.")


def read(name: str) -> pd.DataFrame | None:
    try:
        return pd.read_csv(LAB / name)
    except (OSError, ValueError):
        return None


summary, new, plan = read("tweak_summary.csv"), read("new_pitch_summary.csv"), read("development_plan_top3.csv")
if summary is None or summary.empty:
    st.warning("Faltan los resultados: ejecuta `python reports/design_lab/run.py`.")
    st.stop()

best = summary.sort_values("arsenal_gain_hh", ascending=False).iloc[0]
more_cdmx = summary.sort_values("arsenal_diff", ascending=False).iloc[0]
c1, c2, c3 = st.columns(3)
with c1:
    theme.big_number(f"Mayor ganancia en CDMX: {best['label']}", f"{best['arsenal_gain_hh']:+.2f}", "reports/design_lab/tweak_summary.csv",
                     hot=True, short_source="puntos de Stuff+ del arsenal")
with c2:
    theme.big_number(f"Vale más en CDMX que en el mar: {more_cdmx['label']}", f"{more_cdmx['arsenal_diff']:+.2f}", "reports/design_lab/tweak_summary.csv",
                     short_source="puntos extra por altura")
if new is not None and "arsenal_gain_hh" in new and new["arsenal_gain_hh"].notna().any():
    nb = new.sort_values("arsenal_gain_hh", ascending=False).iloc[0]
    with c3:
        theme.big_number(f"Agregar un {nb['new_pitch']} (uso 10 %)", f"{nb['arsenal_gain_hh']:+.2f}", "reports/design_lab/new_pitch_summary.csv",
                         short_source="puntos de Stuff+ del arsenal")

t1, t2, t3 = st.tabs(["Ajustes", "Lanzamiento nuevo", "Plan por pitcher"])
with t1:
    st.markdown("Ganancia de Stuff+ del **arsenal completo** al aplicar el ajuste a una familia de lanzamiento (media entre pitcher-temporadas donde el ajuste es admisible).")
    show = summary.rename(columns={
        "label": "Ajuste", "arsenal_gain_hh": "Ganancia en el Harp Helú", "hh_lo": "IC inf.", "hh_hi": "IC sup.", "arsenal_gain_sea": "Ganancia a nivel del mar",
        "arsenal_diff": "Valor extra en CDMX", "admissible_share": "Admisible (%)", "share_above_noise": "Sobre el ruido (%)"})
    for c in ("Admisible (%)", "Sobre el ruido (%)"):
        show[c] = (100 * show[c]).round(0)
    st.dataframe(show[["Ajuste", "Ganancia en el Harp Helú", "IC inf.", "IC sup.", "Ganancia a nivel del mar", "Valor extra en CDMX", "Admisible (%)", "Sobre el ruido (%)"]]
                 .round(3), hide_index=True, use_container_width=True)
    png = LAB / "forest_tweaks.png"
    if png.exists():
        st.image(str(png), use_container_width=True)
with t2:
    if new is None:
        st.info("Sin resultados de lanzamiento nuevo.")
    else:
        st.markdown("Perfil mediano de pitchers **comparables** (misma mano, velocidad de recta y ángulo de brazo parecidos), con la salida del propio pitcher y un uso **supuesto** del 10 %.")
        st.dataframe(new.round(3), hide_index=True, use_container_width=True)
with t3:
    if plan is None or plan.empty:
        st.info("Sin plan por pitcher.")
    else:
        ids = sorted(plan["pitcher_id"].unique())
        pick = st.selectbox("Pitcher-temporada (anonimizado)", ids)
        p = plan[plan["pitcher_id"] == pick].sort_values("rank")
        st.dataframe(p.rename(columns={"rank": "Lugar", "ajuste": "Ajuste", "gain_hh": "Ganancia CDMX", "gain_sea": "Ganancia nivel del mar", "diff": "Valor extra CDMX"})
                     .drop(columns=["pitcher_id"]).round(3), hide_index=True, use_container_width=True)

with st.expander("Cómo leer esto y límites"):
    st.markdown(
        "- Es una diferencia del **modelo** de Stuff+ (sin ubicación ni conteo), no un efecto causal medido.\n"
        "- Un ajuste solo aplica si el perfil resultante cae dentro de lo observado (casco de datos); fuera de ahí los árboles son planos.\n"
        "- +5 % de eficiencia de giro es un supuesto físico (más movimiento con el mismo giro): la brecha de eficiencia de giro entre altitudes sigue sin explicarse.\n"
        "- Los intervalos solo propagan el muestreo de pitchers. Detalle y definiciones: `reports/design_lab/README.md`.")
