import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: streamlit solo agrega app/ al path

import plotly.graph_objects as go
import streamlit as st

from app import theme
from app.components.model import cached_bundle
from stuffplus.api import PitchInput, compare_environments, resolve_rho
from stuffplus.physics.constants import RHO_HARP_HELU, RHO_SEA_LEVEL
from stuffplus.schema import PITCH_TYPES
from stuffplus.serving import ensure_dashboard_tables, read_table

T = theme.TOKENS
SOURCE = "stuffplus.api.predict_pitch · tablas del bundle (agregados, sin pitcheos sueltos)"
theme.setup("Simulador")
cached_bundle()
st.title("Simulador de lanzamiento")

ensure_dashboard_tables()
parks = read_table("by_park")
options: list[tuple[str, float]] = [("Harp Helú (constante física)", float(RHO_HARP_HELU))]
if parks is not None and {"park_id", "rho"}.issubset(parks.columns):
    ordered = parks.sort_values("rho")
    for row in ordered.itertuples(index=False):
        alt = getattr(row, "altitude", "")
        options.append((f"Parque {int(row.park_id)} · ρ̂ {row.rho:.3f} · {alt}", float(row.rho)))
picked = st.selectbox("Parque (por densidad del aire)", [name for name, _ in options],
                      help="Cada parque de la LMB entra con su ρ̂. Harp Helú usa la constante física.")
rho_park = dict(options)[picked]

form, out = st.columns([1.1, 2], gap="large")
with form:
    with st.form("pitch_form", border=False):
        c1, c2 = st.columns([3, 2])
        ptype = c1.selectbox("Tipo", PITCH_TYPES, help="Etiqueta Trackman; la identidad real se calcula por forma.")
        throws = c2.radio("Mano", ["Right", "Left"], horizontal=True, format_func=lambda x: "Der." if x == "Right" else "Zur.")
        c1, c2, c3 = st.columns(3)
        velo = c1.number_input("Velo (mph)", 55.0, 106.0, 95.0, 0.5, help="Velocidad de salida.")
        spin = c2.number_input("Giro (rpm)", 300.0, 3800.0, 2350.0, 25.0, help="Revoluciones por minuto.")
        axis = c3.number_input("Eje (°)", 0.0, 360.0, 205.0, 5.0, help="Eje de giro, 180° = backspin puro.")
        c1, c2, c3 = st.columns(3)
        ivb = c1.number_input("IVB (in)", -35.0, 35.0, 17.0, 0.5, help="Quiebre vertical inducido.")
        hb = c2.number_input("HB (in)", -35.0, 35.0, 8.0, 0.5, help="Vista del catcher, + hacia primera.")
        ext = c3.number_input("Ext. (ft)", 3.5, 8.5, 6.2, 0.1, help="Extensión de liberación.")
        c1, c2, c3 = st.columns(3)
        plate_x = c1.number_input("Plato X (ft)", -2.5, 2.5, 0.0, 0.1, help="Vista del catcher. Hace falta para Location+.")
        plate_z = c2.number_input("Plato Z (ft)", 0.5, 5.0, 2.5, 0.1, help="Altura al cruce del plato.")
        batter = c3.radio("Bateador", ["Right", "Left"], horizontal=True, format_func=lambda x: "Der." if x == "Right" else "Zur.")
        measured = st.selectbox("Aire donde mediste el movimiento", ["sea_level", "harp_helu"],
                                format_func=lambda x: "Nivel del mar" if x == "sea_level" else "Harp Helú (CDMX)")
        go_btn = st.form_submit_button("Calcular", type="primary", use_container_width=True)

with out:
    if not go_btn and "sim_result" not in st.session_state:
        st.info("Captura un lanzamiento y pulsa **Calcular** para ver su valor en el parque elegido y a nivel del mar.")
        st.stop()
    if go_btn:
        try:
            p = PitchInput(ptype, throws, velo, spin, axis, ivb, hb, extension=ext,
                           rho_measured=resolve_rho(measured), plate_x=plate_x, plate_z=plate_z,
                           balls=0, strikes=0, batter_side=batter)
            with st.spinner("Calculando…"):
                st.session_state["sim_result"] = compare_environments(p, rho_park, RHO_SEA_LEVEL)
                st.session_state["sim_pitch"] = p
                st.session_state["sim_rho"] = rho_park
                st.session_state["sim_park"] = picked
        except ValueError as e:
            st.session_state.pop("sim_result", None)
            st.error(f"Entrada no válida: {e}")
            st.stop()
    r = st.session_state["sim_result"]
    p = st.session_state["sim_pitch"]
    rho_used = float(st.session_state.get("sim_rho", rho_park))
    park_name = st.session_state.get("sim_park", picked)
    a, b = r["a"], r["b"]
    theme.demo_badge(r["demo_data"])

    def _num(v) -> str:
        return "—" if v is None else f"{float(v):.1f}"

    def gauge(title: str, value: float, color: str):
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=value, title={"text": title, "font": {"size": 14, "color": T["text"]}},
            number={"font": {"size": 42, "color": T["white"], "family": theme.FONT}},
            gauge={"axis": {"range": [60, 140], "nticks": 5, "tickcolor": T["muted"]}, "bar": {"color": color},
                   "bgcolor": T["panel"], "bordercolor": T["line"],
                   "threshold": {"line": {"color": T["white"], "width": 3}, "value": 100}}))
        fig.update_layout(height=160, margin=dict(l=20, r=20, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)", font_color=T["text"])
        return fig

    g1, g2 = st.columns(2)
    g1.plotly_chart(gauge(f"Stuff+ · {park_name.split('·')[0].strip()}", a["stuff_plus"], T["red_soft"]), use_container_width=True)
    g2.plotly_chart(gauge("Stuff+ a nivel del mar", b["stuff_plus"], T["white"]), use_container_width=True)
    m1, m2 = st.columns(2)
    m1.markdown(
        f'<div title="Fuente: {SOURCE}">Location+ {_num(a.get("location_plus"))} · Pitching+ {_num(a.get("pitching_plus"))}'
        f'<br><span style="color:{T["muted"]}">ρ̂ {rho_used:.3f}</span></div>', unsafe_allow_html=True)
    m2.markdown(
        f'<div title="Fuente: {SOURCE}">Location+ {_num(b.get("location_plus"))} · Pitching+ {_num(b.get("pitching_plus"))}'
        f'<br><span style="color:{T["muted"]}">ρ̂ {float(RHO_SEA_LEVEL):.3f}</span></div>', unsafe_allow_html=True)
    d = r["delta_stuff_plus"]
    st.markdown(
        f'<div class="big-number" title="Fuente: {SOURCE}" style="color:{T["red_soft"]}; font-size:2.2rem">ΔStuff+ CDMX {d:+.1f}'
        f'<small>ΔIVB {r["delta_ivb"]:+.1f}" · ΔHB {r["delta_hb"]:+.1f}" frente a nivel del mar</small></div>',
        unsafe_allow_html=True)

    s, c = b["movement_expected"], a["movement_expected"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[s["hb"]], y=[s["ivb"]], mode="markers+text", text=["Nivel del mar"], textposition="bottom center",
                             marker=dict(size=14, color=T["muted"]), name="Nivel del mar"))
    fig.add_trace(go.Scatter(x=[c["hb"]], y=[c["ivb"]], mode="markers+text", text=["Parque"], textposition="top center",
                             marker=dict(size=16, color=T["red"]), name="Parque"))
    fig.add_annotation(x=c["hb"], y=c["ivb"], ax=s["hb"], ay=s["ivb"], xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowwidth=3, arrowcolor=T["red_soft"])
    fig.update_layout(height=180, margin=dict(l=40, r=20, t=5, b=30), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=T["panel"],
                      font_color=T["text"], showlegend=False, xaxis_title="HB (in)", yaxis_title="IVB (in)")
    fig.update_xaxes(zeroline=True, zerolinecolor=T["line"], gridcolor=T["line"])
    fig.update_yaxes(zeroline=True, zerolinecolor=T["line"], gridcolor=T["line"])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### ¿Por qué?")
    why_lines: list[str] = []
    if not r["demo_data"]:
        try:
            from stuffplus.explain import altitude_breakdown, explain_pitch

            explained = explain_pitch(p, rho_used, top=3)
            broken = altitude_breakdown(p, rho_used, top=3)
            why_lines = [item["text"] for item in explained["contributions"]]
            why_lines += [item["text"] for item in broken["items"][:2]]
        except Exception:
            why_lines = []
    if not why_lines:
        why_lines = [
            f"Traslado físico: el movimiento cambia {r['delta_ivb']:+.1f}\" de IVB y {r['delta_hb']:+.1f}\" de HB al pasar a ρ̂ {rho_used:.3f}.",
            "El desglose SHAP aparece cuando el bundle de modelos está cargado (demo_data falso).",
        ]
    for line in why_lines:
        st.markdown(f"- {line}")
    st.caption("Fuente: " + SOURCE + ". " + ("Modelo de demostración." if r["demo_data"] else "Modelo entrenado."))
