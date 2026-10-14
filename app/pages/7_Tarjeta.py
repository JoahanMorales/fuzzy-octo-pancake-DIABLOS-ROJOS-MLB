import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: streamlit solo agrega app/ al path

import matplotlib.pyplot as plt
import streamlit as st

from app import theme
from stuffplus import cards

theme.setup("Tarjeta")
st.title("Tarjeta")
st.caption("Ficha por lanzador para el coach y el deck. Agregados, sin pitcheos sueltos.")

state = cards.prepare_page()
if not state["ok"]:
    st.info(state["message"])
    st.stop()

theme.demo_badge(False)
label = st.selectbox("Lanzador", state["options"], help="Ids anonimizados. Fuente: reports/leaderboards/pitcher_season.csv")
pitcher, year_s = label.split(" · ")
try:
    card = cards.build_card(pitcher, int(year_s), state["tables"])
except KeyError as exc:
    st.info(f"Este lanzador no tiene arsenal en el agregado. {exc}")
    st.stop()

fig = cards.render_card(card)
png_buf, pdf_buf = io.BytesIO(), io.BytesIO()
fig.savefig(png_buf, format="png", dpi=cards.DPI, facecolor=fig.get_facecolor())
fig.savefig(pdf_buf, format="pdf", facecolor=fig.get_facecolor())
plt.close(fig)
png_buf.seek(0)
pdf_buf.seek(0)

st.image(png_buf, caption=(
    "Punto blanco = nivel del mar. Punta de la flecha = Harp Helú. "
    f"Stuff+ neutral (nivel del mar) y Stuff+ Harp Helú (entorno, ρ={card['rho']:.3f}). "
    f"Fuente ρ: {card['sources']['rho']}. "
    "Arsenal: reports/leaderboards/pitcher_pitch.csv. "
    "Índice: reports/pitcher_sensitivity/pitchers.csv."
))
c1, c2 = st.columns(2)
stem = f"{card['pitcher_anon_id']}_{card['year']}"
c1.download_button("Descargar PNG", data=png_buf.getvalue(), file_name=f"{stem}.png", mime="image/png")
c2.download_button("Descargar PDF", data=pdf_buf.getvalue(), file_name=f"{stem}.pdf", mime="application/pdf")

st.markdown("### Recomendaciones")
for rec in card["recommendations"]:
    st.markdown(f"<div class='card' title='Fuente: {rec['source']}'>{rec['text']}"
                f"<br><small>Fuente: {rec['source']}</small></div>", unsafe_allow_html=True)
st.caption(card["sources"]["arsenal"])
st.caption(card["sources"]["index"])
