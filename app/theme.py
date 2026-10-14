"""Identidad visual Diablos (rojo + negro, estilo transmisión). Tokens únicos; todo color sale de aquí."""
from __future__ import annotations

import streamlit as st

TOKENS = {
    "bg": "#0B0B0D", "panel": "#16161A", "line": "#2A2A31", "text": "#F4F4F5", "muted": "#A1A1AA",
    "red": "#D71920", "red_soft": "#FF4B52", "white": "#FFFFFF", "ok": "#3FB950",
}
FONT = "'Barlow Condensed', 'Arial Narrow', sans-serif"
NAV = [
    ("Home.py", "Inicio"), ("pages/1_Simulador.py", "Simulador"), ("pages/2_Leaderboard.py", "Leaderboard"),
    ("pages/3_Prospecto.py", "Prospecto"), ("pages/4_Altitud.py", "Altitud"),
    ("pages/5_Recomendaciones.py", "Recomendaciones"), ("pages/6_Laboratorio.py", "Laboratorio"),
    ("pages/7_Tarjeta.py", "Tarjeta"), ("pages/8_Staff_Diablos.py", "Staff Diablos"),
]
_CSS = f"""
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;700&display=swap" rel="stylesheet">
<style>
h1,h2,h3,.big-number,.badge {{font-family:{FONT}; letter-spacing:.02em; text-transform:uppercase;}}
[data-testid=stMainBlockContainer] {{padding-top:2.5rem; padding-bottom:1rem;}}
h1 {{font-size:2rem!important; padding:0!important; margin-bottom:.2rem;}}
h1 {{border-left:6px solid {TOKENS['red']}; padding-left:.6rem;}}
.big-number {{font-size:4rem; font-weight:700; line-height:1; color:{TOKENS['white']};}}
.big-number small {{font-family:'Source Sans Pro',sans-serif; font-size:.95rem; font-weight:400; letter-spacing:0; color:{TOKENS['muted']}; display:block; text-transform:none; margin-top:.3rem;}}
[data-testid=stHorizontalBlock] .card {{height:100%; min-height:9rem;}}
button[kind=primaryFormSubmit], button[kind=primary] {{background:{TOKENS['red']}!important; border-color:{TOKENS['red']}!important; font-weight:700;}}
.card {{background:{TOKENS['panel']}; border:1px solid {TOKENS['line']}; border-radius:8px; padding:1rem 1.2rem;}}
.card.hot {{border-top:4px solid {TOKENS['red']};}}
.badge {{background:{TOKENS['red']}; color:#fff; padding:.1rem .5rem; border-radius:4px; font-size:.8rem;}}
.badge.ok {{background:{TOKENS['ok']}; color:#000;}}
:focus-visible {{outline:3px solid {TOKENS['red_soft']}!important; outline-offset:2px;}}
@media (prefers-reduced-motion: reduce) {{* {{animation:none!important; transition:none!important;}}}}
</style>
"""


def setup(title: str, icon: str = "⚾", sidebar: str = "collapsed") -> None:
    st.set_page_config(page_title=f"{title} · Stuff+ 2240", page_icon=icon, layout="wide", initial_sidebar_state=sidebar)
    st.markdown(_CSS, unsafe_allow_html=True)


def demo_badge(demo: bool) -> None:
    st.markdown('<span class="badge" title="Valores simulados; el modelo real aún no está conectado">DATOS DE DEMOSTRACIÓN</span>'
                if demo else '<span class="badge ok" title="Modelo entrenado con datos LMB 2024–2026">MODELO REAL</span>',
                unsafe_allow_html=True)


def big_number(label: str, value: str, source: str, hot: bool = False, short_source: str = "física LMB") -> None:
    """Número grande; la ruta técnica de la fuente va solo en el tooltip."""
    st.markdown(f'<div class="card{" hot" if hot else ""}" title="Fuente: {source}"><div class="big-number">{value}'
                f'<small>{label} · fuente: {short_source}</small></div></div>', unsafe_allow_html=True)


def coming_soon(title: str, owner_task: str, blurb: str) -> None:
    setup(title)
    st.title(title)
    st.info(f"{blurb}\n\nEn construcción ({owner_task}).")
