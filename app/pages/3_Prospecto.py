import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: streamlit solo agrega app/ al path

import pandas as pd
import streamlit as st

from app import theme
from stuffplus.api import PitchInput
from stuffplus.prospect import evaluate_arsenal
from stuffplus.schema import PITCH_TYPES

T = theme.TOKENS
AXIS = {"Four-Seam": 210.0, "Sinker": 220.0, "Cutter": 170.0, "Slider": 90.0, "Curveball": 40.0, "Changeup": 225.0, "Splitter": 220.0}
theme.setup("Prospecto")
st.title("Perfil de prospecto")
st.caption("Arsenal de 2 a 5 lanzamientos, o un CSV de Trackman. El veredicto es para jugar en casa, en Harp Helú.")

EXAMPLE = [
    {"pitch_type": "Four-Seam", "velo": 95.0, "spin_rate": 2350.0, "spin_axis": 210.0, "ivb": 18.0, "hb": 8.0, "usage": 0.55},
    {"pitch_type": "Slider", "velo": 86.0, "spin_rate": 2500.0, "spin_axis": 90.0, "ivb": 3.0, "hb": -8.0, "usage": 0.25},
    {"pitch_type": "Changeup", "velo": 85.0, "spin_rate": 1750.0, "spin_axis": 225.0, "ivb": 8.0, "hb": 14.0, "usage": 0.20},
]


def _inputs(rows, throws, rho_measured):
    pitches = []
    for row in rows:
        pitches.append(PitchInput(
            row["pitch_type"], throws, float(row["velo"]), float(row["spin_rate"]), float(row["spin_axis"]),
            float(row["ivb"]), float(row["hb"]), extension=6.2, rho_measured=rho_measured,
            arsenal={"usage": float(row["usage"])},
        ))
    return pitches


def _show(result):
    theme.demo_badge(result["demo_data"])
    verdict = result["verdict"]
    color = T["ok"] if verdict == "Firmar" else T["red_soft"] if verdict == "Evitar para casa" else T["white"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="card hot" title="Fuente: stuffplus.prospect · percentiles de reports/leaderboards/pitcher_season.csv">'
            f'<div class="big-number" style="font-size:1.7rem; color:{color}">{verdict}'
            f'<small>Veredicto para casa · fuente: leaderboard LMB</small></div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        theme.big_number("Stuff+ Harp Helú", f'{result["arsenal"]["stuff_plus_harp_helu"]:.1f}', result["sources"]["stuff"], short_source="modelo Stuff+")
    with c3:
        theme.big_number("Stuff+ nivel del mar", f'{result["arsenal"]["stuff_plus_neutral"]:.1f}', result["sources"]["stuff"], short_source="sabor neutral")
    with c4:
        theme.big_number("Índice a prueba de altura", f'{result["altitude_proof_index"]:.1f}', result["sources"]["index"], short_source="Δ vs media liga")
    st.markdown(
        f'<p style="color:{color}; font-family:{theme.FONT}; letter-spacing:.04em; text-transform:uppercase; margin:.2rem 0 1rem">'
        f'ΔStuff+ CDMX {result["arsenal"]["delta_cdmx"]:+.1f} · umbral firmar ≥ {result["thresholds"]["p75"]:.0f} · evitar &lt; {result["thresholds"]["p25"]:.0f}</p>',
        unsafe_allow_html=True,
    )
    h1, h2, h3 = st.columns(3)
    hr = "Sí" if result["hr_risk"] else "No"
    detail = f' · lo empuja {result["hr_risk_shape"]}' if result["hr_risk_shape"] else ""
    h1.metric("Riesgo de HR en CDMX", hr + detail)
    h2.metric("Carreras en casa / temporada", f'{result["runs_saved_home"]:+.2f}')
    h3.metric("Victorias en casa", f'{result["wins_saved_home"]:+.2f}')
    st.caption(
        f'Carreras: (Stuff+ Harp Helú − 100) × {result["runs_per_point"]:.6f} × {result["home_pitches"]} lanzamientos. '
        f'{result["sources"]["home_pitches"]}. Victorias con {result["runs_per_win_home"]:.2f} carreras por victoria '
        f'({result["sources"]["wins"]}). El índice no es el EB de brazos que ya jugaron: es el Δ del modelo menos la media de la liga.'
    )
    table = pd.DataFrame(result["pitches"])[
        ["shape", "pitch_type", "usage", "velo", "stuff_plus_harp_helu", "stuff_plus_neutral", "delta_cdmx"]
    ].rename(columns={
        "shape": "Forma", "pitch_type": "Etiqueta Trackman", "usage": "Uso", "velo": "Velo",
        "stuff_plus_harp_helu": "Stuff+ HH", "stuff_plus_neutral": "Stuff+ mar", "delta_cdmx": "Δ CDMX",
    })
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.caption("La forma se calcula con el movimiento llevado a nivel del mar, no con la etiqueta de Trackman. Fuente: " + result["sources"]["stuff"])
    comps = pd.DataFrame(result["comparables"])
    if comps.empty:
        st.info("No hay comparables en el leaderboard para la forma principal.")
    else:
        focus = result["comparable_pitch"]
        st.subheader(f'5 comparables LMB · {focus["shape"]}')
        show = comps.rename(columns={
            "pitcher_anon_id": "Lanzador", "year": "Año", "shape": "Forma", "distance": "Distancia",
            "stuff_plus_harp_helu": "Stuff+ HH", "velo": "Velo",
        })[["Lanzador", "Año", "Forma", "Velo", "Stuff+ HH", "Distancia"]]
        st.dataframe(show, hide_index=True, use_container_width=True)
        st.caption("Identidades anonimizadas. Vecinos por velo, IVB y HB del lanzamiento de más uso, misma mano. Fuente: " + result["sources"]["comparables"])
    st.caption("Riesgo de HR: Δ de HR/FB de la forma, ponderado por uso, por encima de la media de la liga. Fuente: " + result["sources"]["hr"])


form, out = st.columns([1.05, 1.4], gap="large")
with form:
    if st.button("Ver arsenal de ejemplo", use_container_width=True):
        try:
            st.session_state["prospect"] = evaluate_arsenal(_inputs(EXAMPLE, "Right", 1.0))
            st.session_state.pop("prospect_error", None)
        except (ValueError, FileNotFoundError) as exc:
            st.session_state["prospect_error"] = str(exc)
    uploaded = st.file_uploader("CSV Trackman", type=["csv"], help="Muchos lanzamientos: se agrupan por tipo y se quedan los 5 de más uso.")
    with st.form("arsenal", border=False):
        c1, c2 = st.columns(2)
        throws = c1.radio("Mano", ["Right", "Left"], horizontal=True, format_func=lambda x: "Der." if x == "Right" else "Zur.")
        measured = c2.selectbox("Aire de la medición", ["sea_level", "harp_helu"], format_func=lambda x: "Nivel del mar" if x == "sea_level" else "Harp Helú")
        n = st.selectbox("Lanzamientos", [2, 3, 4, 5], index=1)
        rows = []
        defaults = EXAMPLE + EXAMPLE
        for i in range(n):
            st.markdown(f"**Lanzamiento {i + 1}**")
            base = defaults[i]
            a, b, c = st.columns(3)
            ptype = a.selectbox("Tipo", PITCH_TYPES, index=PITCH_TYPES.index(base["pitch_type"]), key=f"t{i}")
            velo = b.number_input("Velo", 55.0, 106.0, base["velo"], 0.5, key=f"v{i}")
            usage = c.number_input("Uso", 0.0, 1.0, base["usage"], 0.05, key=f"u{i}")
            a, b, c = st.columns(3)
            spin = a.number_input("Giro", 300.0, 3800.0, base["spin_rate"], 25.0, key=f"s{i}")
            ivb = b.number_input("IVB", -35.0, 35.0, base["ivb"], 0.5, key=f"i{i}")
            hb = c.number_input("HB", -35.0, 35.0, base["hb"], 0.5, key=f"h{i}")
            rows.append({"pitch_type": ptype, "velo": velo, "spin_rate": spin, "spin_axis": AXIS[ptype], "ivb": ivb, "hb": hb, "usage": usage})
        go = st.form_submit_button("Evaluar arsenal", type="primary", use_container_width=True)

with out:
    if go or (uploaded is not None and st.session_state.get("prospect_file") != getattr(uploaded, "name", None)):
        try:
            from stuffplus.api import resolve_rho

            if uploaded is not None:
                st.session_state["prospect"] = evaluate_arsenal(pd.read_csv(uploaded))
                st.session_state["prospect_file"] = uploaded.name
            elif go:
                st.session_state["prospect"] = evaluate_arsenal(_inputs(rows, throws, resolve_rho(measured)))
            st.session_state.pop("prospect_error", None)
        except (ValueError, FileNotFoundError, KeyError) as exc:
            st.session_state.pop("prospect", None)
            st.session_state["prospect_error"] = str(exc)
    if error := st.session_state.get("prospect_error"):
        st.error(f"No se pudo armar el perfil: {error}")
    elif "prospect" not in st.session_state:
        st.info("Carga un CSV o pulsa **Ver arsenal de ejemplo**. El veredicto sale en esta columna, sin bajar la página.")
    else:
        _show(st.session_state["prospect"])
