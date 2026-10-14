import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: streamlit solo agrega app/ al path

import pandas as pd
import streamlit as st

from app import theme

REPORTS = Path(__file__).resolve().parents[2] / "reports"
MEMO = REPORTS / "recommendations" / "memo.md"

theme.setup("Recomendaciones")
st.title("Recomendaciones para el Harp Helú")
theme.demo_badge(False)  # cifras del modelo real y de reports/ (app/DESIGN.md: MODELO REAL)
st.caption("Memo operativo: perfiles que ganan y pierden, lista para perfilar prospectos, tácticas y valor en victorias.")

if not MEMO.exists():
    st.warning("Falta reports/recommendations/memo.md: ejecuta `python reports/recommendations/build_memo.py`.")
    st.stop()

try:  # los tres números grandes salen de los mismos CSV que el memo
    shapes = pd.read_csv(REPORTS / "altitude_delta" / "delta_by_shape.csv")
    league = float((shapes["delta_stuff"] - shapes["relative_to_league"]).mean())
    riding = float(shapes.loc[shapes["shape"] == "riding 4S", "delta_stuff"].iloc[0])
    sweeper = float(shapes.loc[shapes["shape"] == "sweeper", "delta_stuff"].iloc[0])
    c1, c2, c3 = st.columns(3)
    with c1:
        theme.big_number("Stuff+ promedio de la liga en CDMX", f"{league:+.1f}", "reports/altitude_delta/delta_by_shape.csv", hot=True)
    with c2:
        theme.big_number("La recta con más ride", f"{riding:+.1f}", "reports/altitude_delta/delta_by_shape.csv", short_source="ΔStuff+ riding 4S")
    with c3:
        theme.big_number("El barrido (sweeper)", f"{sweeper:+.1f}", "reports/altitude_delta/delta_by_shape.csv", short_source="ΔStuff+ sweeper")
except (OSError, KeyError, IndexError, ValueError):
    st.info("Aún no están disponibles los números de altitud por forma.")

text = MEMO.read_text(encoding="utf-8").split("\n", 1)[1]  # sin el título H1: la página ya lo trae
st.markdown(text)
st.download_button("Descargar el memo (.md)", MEMO.read_bytes(), file_name="recomendaciones_harp_helu.md", mime="text/markdown")
