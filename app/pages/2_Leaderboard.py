import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app import theme
from app.components.model import cached_bundle
from stuffplus.serving import ensure_dashboard_tables, read_table

theme.setup("Leaderboard")
cached_bundle()
st.title("Leaderboard")
ensure_dashboard_tables()
table = read_table("pitcher_season")
if table is None or table.empty:
    st.info("No hay tabla de lanzadores en artifacts/bundle/tables. Hace falta pitcher_season.csv (agregados, no pitcheos).")
    st.stop()

show = table.sort_values("pitching_plus", ascending=False).head(25)
labels = {
    "pitcher_anon_id": "Lanzador", "year": "Año", "pitches": "Pitcheos",
    "stuff_plus": "Stuff+ neutral", "stuff_plus_harp_helu": "Stuff+ Harp Helú",
    "location_plus": "Location+", "pitching_plus": "Pitching+",
    "delta_cdmx": "ΔStuff+ CDMX", "arsenal": "Arsenal",
}
cols = [c for c in labels if c in show.columns]
view = show[cols].rename(columns=labels)
st.dataframe(view, use_container_width=True, hide_index=True,
             column_config={name: st.column_config.NumberColumn(format="%.1f")
                            for name in view.columns if name not in ("Lanzador", "Año", "Pitcheos", "Arsenal")})
st.caption("Fuente: artifacts/bundle/tables/pitcher_season.csv. IDs anonimizados. 100 = promedio LMB. Sin datos crudos.")
