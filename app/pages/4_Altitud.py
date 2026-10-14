import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app import theme
from app.components.model import cached_bundle
from app.components.movement import SIGMA_IN, extremes, shape_points
from stuffplus import config
from stuffplus.serving import ensure_dashboard_tables, read_table

T = theme.TOKENS
theme.setup("Altitud")
cached_bundle()
st.title("Altitud")
ensure_dashboard_tables()
deltas = read_table("delta_by_shape")
shapes = read_table("shapes")
if deltas is None or shapes is None:
    st.info("Faltan delta_by_shape.csv o shapes.csv en artifacts/bundle/tables.")
    st.stop()

order = deltas.sort_values("delta_stuff", ascending=False)
st.markdown("### ΔStuff+ por forma, Harp Helú frente a nivel del mar")
view = order[["shape", "delta_stuff", "verdict", "pitches", "physics"]].rename(columns={
    "shape": "Forma", "delta_stuff": "ΔStuff+", "verdict": "Veredicto", "pitches": "Pitcheos", "physics": "Física",
})
st.dataframe(view, use_container_width=True, hide_index=True,
             column_config={"ΔStuff+": st.column_config.NumberColumn(format="%+.1f")})
bar = go.Figure(go.Bar(
    x=order["delta_stuff"], y=order["shape"], orientation="h",
    marker_color=[T["red"] if v < -10 else T["muted"] for v in order["delta_stuff"]],
    hovertext=order["physics"],
))
bar.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=30), paper_bgcolor="rgba(0,0,0,0)",
                  plot_bgcolor=T["panel"], font_color=T["text"], xaxis_title="ΔStuff+ (Harp Helú − nivel del mar)")
bar.update_xaxes(gridcolor=T["line"], zerolinecolor=T["white"])
st.plotly_chart(bar, use_container_width=True)
st.caption("Fuente: artifacts/bundle/tables/delta_by_shape.csv. El valor es el contrafactual del modelo, no un scatter de pitcheos.")

st.markdown("### Mapa de movimiento")
air_label = st.radio("Aire", ["CDMX", "Nivel del mar"], horizontal=True)
air = "cdmx" if air_label == "CDMX" else "sea"
points = shape_points(shapes, deltas, air)
best, worst = extremes(points)
fig = go.Figure()
for shape, color in ((best, T["red_soft"]), (worst, T["white"])):
    row = points.loc[points["shape"] == shape].iloc[0]
    grid = np.linspace(-4 * SIGMA_IN, 4 * SIGMA_IN, 35)
    xs, ys = row.hb + grid, row.ivb + grid
    xx, yy = np.meshgrid(xs, ys)
    zz = np.exp(-((xx - row.hb) ** 2 + (yy - row.ivb) ** 2) / (2 * SIGMA_IN ** 2))
    fig.add_trace(go.Contour(
        x=xs, y=ys, z=zz, showscale=False, contours_coloring="lines", ncontours=4,
        line_width=2, name=shape, colorscale=[[0, "rgba(0,0,0,0)"], [1, color]],
        hoverinfo="skip",
    ))
fig.add_trace(go.Scatter(
    x=points["hb"], y=points["ivb"], mode="markers+text", text=points["shape"],
    textposition="top center", textfont=dict(size=11, color=T["text"]),
    marker=dict(size=np.clip(points["n"] / 8000, 8, 22), color=points["stuff"],
                colorscale=[[0, T["muted"]], [1, T["red"]]], showscale=False,
                line=dict(width=1, color=T["white"])),
    name="Centroides",
    hovertemplate="%{text}<br>Stuff+ %{marker.color:.1f}<extra></extra>",
))
raw = config.data_path()
if raw.is_file() and st.checkbox("Mostrar una muestra local (solo si el parquet está en esta máquina)"):
    try:
        import pyarrow.parquet as pq

        batch = next(pq.ParquetFile(raw).iter_batches(batch_size=2500, columns=["InducedVertBreak", "HorzBreak"]))
        sample = batch.to_pandas()
        fig.add_trace(go.Scattergl(
            x=sample["HorzBreak"], y=sample["InducedVertBreak"], mode="markers",
            marker=dict(size=3, color=T["line"], opacity=0.35), name="Muestra local", hoverinfo="skip",
        ))
    except (OSError, StopIteration, KeyError, ValueError) as exc:
        st.warning(f"No se pudo leer la muestra local: {exc}")
fig.update_layout(height=520, margin=dict(l=40, r=10, t=10, b=40), paper_bgcolor="rgba(0,0,0,0)",
                  plot_bgcolor=T["panel"], font_color=T["text"], showlegend=False,
                  xaxis_title="HB (in)", yaxis_title="IVB (in)",
                  title=dict(text=f"Más efectivo: {best} · Menos efectivo: {worst}", font=dict(size=14)))
fig.update_xaxes(zeroline=True, zerolinecolor=T["line"], gridcolor=T["line"])
fig.update_yaxes(zeroline=True, zerolinecolor=T["line"], gridcolor=T["line"])
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Centroides: artifacts/bundle/tables/shapes.csv. El traslado a CDMX suma delta_ivb_in y delta_hb_arm_in. "
    f"El contorno (±{SIGMA_IN:.1f}\") es esquemático: las tablas no publican la dispersión dentro de la forma. "
    "El scatter de pitcheos solo aparece si el parquet local existe y se pide."
)
