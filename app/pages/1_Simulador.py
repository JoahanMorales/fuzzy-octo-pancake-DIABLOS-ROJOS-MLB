import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: streamlit solo agrega app/ al path

import plotly.graph_objects as go
import streamlit as st

from app import theme
from stuffplus.api import PitchInput, compare_environments
from stuffplus.schema import PITCH_TYPES

T = theme.TOKENS
theme.setup("Simulador")
st.title("Simulador de lanzamiento")

SOURCE = "stuffplus.api.predict_pitch (física: reports/physics; Stuff+ = 100 promedio LMB)"
form, out = st.columns([1.1, 2], gap="large")

with form:
    with st.form("pitch", border=False):
        c1, c2 = st.columns([3, 2])
        ptype = c1.selectbox("Tipo", PITCH_TYPES, help="Etiqueta Trackman; la identidad real se calcula por forma.")
        throws = c2.radio("Mano", ["Right", "Left"], horizontal=True, format_func=lambda x: "Der." if x == "Right" else "Zur.")
        c1, c2, c3 = st.columns(3)
        velo = c1.number_input("Velo (mph)", 55.0, 106.0, 95.0, 0.5)
        spin = c2.number_input("Giro (rpm)", 300.0, 3800.0, 2350.0, 25.0)
        axis = c3.number_input("Eje (°)", 0.0, 360.0, 205.0, 5.0)
        c1, c2, c3 = st.columns(3)
        ivb = c1.number_input("IVB (in)", -35.0, 35.0, 17.0, 0.5, help="Quiebre vertical inducido.")
        hb = c2.number_input("HB (in)", -35.0, 35.0, 8.0, 0.5, help="Vista del catcher, + hacia primera.")
        ext = c3.number_input("Ext. (ft)", 3.5, 8.5, 6.2, 0.1, help="Extensión de liberación.")
        measured = st.selectbox("Aire donde mediste el movimiento", ["sea_level", "harp_helu"],
                                format_func=lambda x: "Nivel del mar" if x == "sea_level" else "Harp Helú (CDMX)")
        go_btn = st.form_submit_button("Calcular", type="primary", use_container_width=True)

with out:
    if not go_btn and "result" not in st.session_state:
        st.info("Captura un lanzamiento y pulsa **Calcular** para ver su valor en Harp Helú y a nivel del mar.")
        st.stop()
    if go_btn:
        try:
            from stuffplus.api import resolve_rho

            p = PitchInput(ptype, throws, velo, spin, axis, ivb, hb, extension=ext, rho_measured=resolve_rho(measured))
            with st.spinner("Calculando…"):
                st.session_state["result"] = compare_environments(p, "harp_helu", "sea_level")
        except ValueError as e:
            st.session_state.pop("result", None)
            st.error(f"Entrada no válida: {e}")
            st.stop()
    r = st.session_state["result"]
    a, b = r["a"], r["b"]
    hdr1, hdr2 = st.columns([1, 3])
    with hdr1:
        theme.demo_badge(r["demo_data"])

    def gauge(title: str, value: float, color: str):
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=value, title={"text": title, "font": {"size": 16, "color": T["muted"]}},
            number={"font": {"size": 44, "color": T["white"]}},
            gauge={"axis": {"range": [60, 140], "nticks": 5, "tickcolor": T["muted"]}, "bar": {"color": color},
                   "bgcolor": T["panel"], "bordercolor": T["line"],
                   "threshold": {"line": {"color": T["white"], "width": 3}, "value": 100}}))
        fig.update_layout(height=170, margin=dict(l=25, r=25, t=40, b=5), paper_bgcolor="rgba(0,0,0,0)", font_color=T["text"])
        return fig

    g1, g2 = st.columns(2)
    g1.plotly_chart(gauge("Stuff+ en Harp Helú", a["stuff_plus"], T["red"]), use_container_width=True)
    g2.plotly_chart(gauge("Stuff+ a nivel del mar", b["stuff_plus"], T["muted"]), use_container_width=True)
    d = r["delta_stuff_plus"]
    hdr2.markdown(f"**ΔStuff+ CDMX = {d:+.1f}** · ΔIVB {r['delta_ivb']:+.1f}\" · ΔHB {r['delta_hb']:+.1f}\"")

    s, c = b["movement_expected"], a["movement_expected"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[s["hb"]], y=[s["ivb"]], mode="markers+text", text=["Nivel del mar"], textposition="bottom center",
                             marker=dict(size=14, color=T["muted"]), name="Nivel del mar"))
    fig.add_trace(go.Scatter(x=[c["hb"]], y=[c["ivb"]], mode="markers+text", text=["Harp Helú"], textposition="top center",
                             marker=dict(size=16, color=T["red"]), name="Harp Helú"))
    fig.add_annotation(x=c["hb"], y=c["ivb"], ax=s["hb"], ay=s["ivb"], xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=3, arrowcolor=T["red_soft"])
    fig.update_layout(height=215, margin=dict(l=40, r=20, t=5, b=35), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=T["panel"],
                      font_color=T["text"], showlegend=False, xaxis_title="HB (in)", yaxis_title="IVB (in)")
    fig.update_xaxes(zeroline=True, zerolinecolor=T["line"], gridcolor=T["line"])
    fig.update_yaxes(zeroline=True, zerolinecolor=T["line"], gridcolor=T["line"])
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Fuente: {SOURCE}. Modelo: {a['model_version']}.")
