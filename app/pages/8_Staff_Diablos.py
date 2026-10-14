import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: streamlit solo agrega app/ al path

import pandas as pd
import streamlit as st

from app import theme

AUDIT = Path(__file__).resolve().parents[2] / "reports" / "staff_audit"
SRC = "reports/staff_audit/"

theme.setup("Staff Diablos")
st.title("Staff candidato de los Diablos")
theme.demo_badge(False)  # agregados del modelo real (HACK-032)
st.caption("Qué lanzamiento reducir en casa, en cuál apoyarse, orden de rotación casa/visita y bullpen. "
           "Stuff+ neutral = nivel del mar (100 = liga); Stuff+ CDMX = el mismo lanzamiento en aire del Harp Helú.")


def _read(name: str) -> pd.DataFrame | None:
    try:
        return pd.read_csv(AUDIT / f"{name}.csv")
    except (OSError, pd.errors.EmptyDataError):
        return None


t = {n: _read(n) for n in ("staff_pitchers", "staff_pitch_plan", "mix_runs", "rotation", "bullpen", "runs_saved")}
if any(v is None for v in t.values()):
    st.info("Aún no está la auditoría del staff: ejecuta `python -m analysis.staff_audit.run`.")
    st.stop()

st.warning("**Identificación inferida.** Los ids son anónimos: el staff son los pitchers de las dos franquicias con el "
           "aire más ligero. Los datos no separan CDMX de Puebla, así que se muestran por separado. Confirmar con el club.")

franchises = sorted(t["staff_pitchers"].franchise.unique())
f = st.radio("Franquicia candidata", franchises, horizontal=True, format_func=lambda x: f"Franquicia {x}")
sel = {k: v[v.franchise == f] for k, v in t.items()}

rs = sel["runs_saved"].set_index("component")
p = sel["staff_pitchers"]
c1, c2, c3 = st.columns(3)
with c1:
    theme.big_number("carreras salvadas por temporada", f"{rs.loc['total', 'runs_per_season']:.1f}",
                     SRC + "runs_saved.csv", hot=True, short_source="auditoría")
with c2:
    theme.big_number("victorias por temporada", f"{rs.loc['total', 'wins_per_season']:.2f}", SRC + "runs_saved.csv",
                     short_source="HACK-035")
with c3:
    theme.big_number("ΔStuff+ medio del staff en CDMX", f"{p.delta_cdmx.mean():+.1f}", SRC + "staff_pitchers.csv",
                     short_source="modelo")

tab1, tab2, tab3, tab4 = st.tabs(["Qué reducir en casa", "Casa vs visita", "Rotación", "Bullpen"])
with tab1:
    st.markdown("Para cada pitcher: el lanzamiento con **mayor Stuff+ en aire del Harp Helú** (apoyarse) y el **más bajo** "
                "(reducir en casa), solo si la brecha es ≥ 5 puntos y el uso ≥ 5 %.")
    m = sel["mix_runs"].rename(columns={
        "pitcher_anon_id": "pitcher", "role": "rol", "cut_pitch": "reducir", "cut_stuff_hh": "Stuff+ CDMX (reducir)",
        "lean_pitch": "apoyarse", "lean_stuff_hh": "Stuff+ CDMX (apoyarse)", "gap_points": "brecha",
        "runs_saved_per_season": "carreras/temporada"})
    st.dataframe(m[["pitcher", "rol", "reducir", "Stuff+ CDMX (reducir)", "apoyarse", "Stuff+ CDMX (apoyarse)", "brecha",
                    "carreras/temporada"]].round(2), hide_index=True, width="stretch")
    st.caption("Supuesto: mover 10 puntos de uso en casa sin que cambie la calidad del lanzamiento ni la respuesta de "
               "los bateadores (estimación optimista de primer orden).")
with tab2:
    cols = {"pitcher_anon_id": "pitcher", "role": "rol", "pitches": "lanzamientos", "home_pitches": "en casa",
            "stuff_plus": "Stuff+ neutral", "stuff_plus_harp_helu": "Stuff+ CDMX", "delta_cdmx": "ΔCDMX",
            "own_air_home": "aire real · casa", "own_air_road": "aire real · visita", "pitching_plus": "Pitching+"}
    st.dataframe(p[list(cols)].rename(columns=cols).sort_values("ΔCDMX", ascending=False).round(1),
                 hide_index=True, width="stretch")
    st.caption("Las columnas de aire real son promedios observados (pocos juegos en casa): solo sirven de control.")
with tab3:
    r = sel["rotation"]
    if r.empty:
        st.info("No hay suficientes abridores con ≥ 5 aperturas en la última temporada.")
    else:
        st.markdown(f"Temporada {int(r.season.iloc[0])}. En casa se ordena por valor neutral + resistencia a la altura; "
                    "de visita, solo por valor neutral (carreras por 100 lanzamientos vs un pitcher promedio).")
        st.dataframe(r.rename(columns={"pitcher_anon_id": "pitcher", "home_order": "orden en casa",
                                       "road_order": "orden de visita", "delta_cdmx": "ΔCDMX",
                                       "home_value_runs_100": "valor en casa", "road_value_runs_100": "valor de visita"})
                     [["orden en casa", "orden de visita", "pitcher", "ΔCDMX", "valor en casa", "valor de visita"]]
                     .sort_values("orden en casa").round(2), hide_index=True, width="stretch")
        rr = _read("rotation_runs")
        if rr is not None and (rr.franchise == f).any():
            x = rr[rr.franchise == f].iloc[0]
            st.markdown(f"Más que el orden, importa **a quién le tocan las aperturas en casa**: cada apertura en casa que "
                        f"pasa de {x.worst_resilience} a {x.best_resilience} vale {x.runs_per_swapped_start:.2f} carreras "
                        f"({x.swaps:.0f} cambios posibles en la temporada).")
with tab4:
    b = sel["bullpen"].rename(columns={"pitcher_anon_id": "pitcher", "home_leverage_rank": "prioridad en casa",
                                        "pitching_plus_vs_Left": "Pitching+ vs zurdos",
                                        "pitching_plus_vs_Right": "Pitching+ vs derechos", "matchup": "usar",
                                        "platoon_vs_league": "ventaja vs zurdos sobre la liga", "delta_cdmx": "ΔCDMX"})
    st.dataframe(b[[c for c in ("prioridad en casa", "pitcher", "usar", "Pitching+ vs zurdos", "Pitching+ vs derechos",
                                "ventaja vs zurdos sobre la liga", "ΔCDMX") if c in b]].round(1),
                 hide_index=True, width="stretch")
    st.caption("\"Usar\" compara su diferencia zurdos − derechos con la normal de la liga para su mano: todo derecho "
               "rinde mejor contra derechos, eso solo no es una recomendación.")

readme = AUDIT / "README.md"
if readme.exists():
    with st.expander("Metodología y supuestos"):
        st.markdown(readme.read_text(encoding="utf-8").split("\n", 1)[1])
