import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # raíz del repo: streamlit solo agrega app/ al path

import streamlit as st

from app import theme

theme.setup("Inicio")
st.title("Stuff+ 2240")
st.caption("¿Cuánto vale tu lanzamiento en Harp Helú? Modelo de Stuff+ para la LMB ajustado por la densidad del aire (2,240 m).")
c1, c2, c3 = st.columns(3)
with c1:
    theme.big_number("Menos aire en CDMX", "−19 %", "reports/physics/rho_by_bucket.csv (ρ̂ Extreme ≈ 0.84; Harp Helú ≈ 0.81)", hot=True)
with c2:
    theme.big_number("Menos IVB en la recta", "−3.5\"", "reports/physics/delta_extreme_vs_no.csv")
with c3:
    theme.big_number("La recta llega más rápido", "+1.3 mph", "reports/physics/delta_extreme_vs_no.csv")
st.markdown("### Explora")
st.page_link("pages/1_Simulador.py", label="Probar el simulador →", use_container_width=True)
cols = st.columns(4)
for i, (path, label) in enumerate(theme.NAV[2:]):
    cols[i % 4].page_link(path, label=label, use_container_width=True)
