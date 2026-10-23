"""HACK-035: carreras por victoria de la LMB, conversión Stuff+ → carreras → victorias y ejemplo del brazo a prueba de altura.

Uso: python analysis/business_value/run.py  (≈ 1 h sin caché: 5 ajustes del Stuff+ de producción). Escribe agregados en
reports/business_value/.

Desde HACK-078 los puntos de Stuff+ son los de producción (v2: valor neutral al conteo + temperatura, HACK-057): xRV fuera
de pliegue por pitcher con ``fit_production_stuff`` y la escala Plus del modelo exportado (web/public/data/models/stuff.json).
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.pitching_model import run as pitching_run
from analysis.stuff_model import run as stuff_run
from stuffplus import splits
from stuffplus import value as V
import json
from stuffplus.io import load_raw
from stuffplus.models import pitching as pitching_models
from stuffplus.models.location import add_pitch_family
from stuffplus.models.stuff import PRODUCTION_VERSION, fit_production_stuff
from stuffplus.physics import parks
from stuffplus.scale import PlusScaler
from stuffplus.schema import clean

warnings.filterwarnings("ignore")
OUT = Path("reports/business_value")
OUT.mkdir(parents=True, exist_ok=True)
NO, MED, EXT = "No Altitude", "Medium Altitude", "Extreme Altitude"
PITCH_GRID = (100, 500, 1000, 2500)
RED, BLACK = "#B71C1C", "#111111"

raw = clean(load_raw())
df = pitching_run.prepare(raw)  # targets (rv, rv_x) + rasgos de Stuff+ y Pitching+; mismo marco con el que se entrenan

# --- 1. marcadores, equipo-temporadas y exponente pitagórico
scores = V.game_scores(raw)
maps = parks.load_maps(raw)
pm = maps["park_map"].drop_duplicates("game_anon_id").set_index("game_anon_id")
ts = V.team_seasons(scores, pm)
ts = ts[ts["games"] >= 20]
fit = V.fit_pythagorean(ts)
x = fit["exponent"]
pd.DataFrame([fit | {"games_used": int(scores.shape[0])}]).round(4).to_csv(OUT / "pythagorean.csv", index=False)

# empírico: pendiente de W% contra diferencia de carreras por juego (control de la linealización)
ts["rdiff"] = (ts["rs"] - ts["ra"]) / ts["games"]
ts["wpct"] = ts["wins"] / ts["games"]
w = ts["games"]
slope = float(np.polyfit(ts["rdiff"], ts["wpct"], 1, w=np.sqrt(w))[0])

# --- 2. carreras por equipo-juego y carreras por victoria por entorno
scores["total"] = scores["home_runs"] + scores["away_runs"]
r_env = scores.groupby("bucket")["total"].mean() / 2.0
r_league = float(scores["total"].mean() / 2.0)
rpw = {"liga": V.runs_per_win(r_league, x)} | {b: V.runs_per_win(r, x) for b, r in r_env.items()}
rpw_table = pd.DataFrame({"entorno": list(rpw), "carreras_por_equipo_juego": [r_league] + [r_env[b] for b in list(rpw)[1:]],
                          "carreras_por_victoria": list(rpw.values())})
rpw_table["victorias_por_100_carreras"] = 100 / rpw_table["carreras_por_victoria"]
rpw_table.loc[len(rpw_table)] = ["empírico liga (1/pendiente de W% vs dif. de carreras por juego)", np.nan, 1.0 / slope,
                                 100 * slope]
rpw_table.round(4).to_csv(OUT / "runs_per_win.csv", index=False)

# --- 3. lanzamientos por apertura y aperturas en casa por temporada
df["_half"] = df["game_anon_id"].astype(str) + "_" + df["Top/Bottom"].astype(str)
starter = df.groupby("_half")["pitcher_anon_id"].agg(lambda s: s.iloc[0])
df["_is_starter"] = df["pitcher_anon_id"].to_numpy() == df["_half"].map(starter).to_numpy()
per_start = df[df["_is_starter"]].groupby(["game_anon_id", "pitcher_anon_id"]).size()
pitches_per_start = float(per_start.median())
games_per_team_season = float(ts["games"].median())
home_starts = max(int(round(games_per_team_season / 2 / 5)), 1)  # juegos de local por temporada en los datos / rotación de 5

# --- 4. carreras por punto: estimación DIRECTA fuera de muestra (puntos con el scaler del modelo, regresión del run value realizado)
STUFF_JSON = Path("web/public/data/models/stuff.json")
stuff_export = json.loads(STUFF_JSON.read_text(encoding="utf-8"))
assert stuff_export["model_version"] == PRODUCTION_VERSION, "stuff.json no es el Stuff+ de producción"
st = stuff_export["plus"]["stats"]
sigma = float(st["__all__"]["sd"])
sigma_years = {k: float(v["sd"]) for k, v in st.items() if k != "__all__"}
def plus_from_export(x: np.ndarray, year: np.ndarray) -> np.ndarray:
    """100 + 10·sign·(x − media)/de con la escala del Stuff+ exportado, por temporada (global si falta)."""
    sign = stuff_export["plus"].get("sign", -1)
    out = np.empty(len(x))
    for i, (v, y) in enumerate(zip(x, year)):
        g = st.get(str(int(y)), st["__all__"])
        out[i] = 100 + 10 * sign * (v - g["mean"]) / g["sd"]
    return out


cache = Path(f"artifacts/business_value_oof_{PRODUCTION_VERSION}.parquet")
if cache.exists():
    oofdf = pd.read_parquet(cache)
else:
    folds = list(splits.pitcher_group_kfold(df))
    dfam = add_pitch_family(df)
    stuff_oof = np.full(len(df), np.nan)  # valor de Stuff+ v2 fuera de muestra, por pitcher
    for tr, te in folds:
        stuff_oof[te] = fit_production_stuff(dfam.iloc[tr]).predict_xrv(dfam.iloc[te])
    po = pitching_models.run_oof(df, folds)
    pitch_neutral = pitching_models.combine(po, df["rv_x"].to_numpy(), folds)["combined_neutral"]  # Pitching+ del dashboard: bateador neutral
    oofdf = pd.DataFrame({"stuff_xrv": stuff_oof, "pitching_xrv": pitch_neutral})
    cache.parent.mkdir(parents=True, exist_ok=True)
    oofdf.to_parquet(cache, index=False)
pts = {
    "Stuff+": plus_from_export(oofdf["stuff_xrv"].to_numpy(float), df["year"].to_numpy()),
    # el scaler de Pitching+ del bundle local no es el de joahan-1: se reajusta con el mismo procedimiento (PlusScaler por temporada)
    "Pitching+": PlusScaler().fit(df.assign(x=oofdf["pitching_xrv"].to_numpy()), "x").transform(
        df.assign(x=oofdf["pitching_xrv"].to_numpy()), "x"),
}
groups = df["pitcher_anon_id"].to_numpy()
est, rows = {}, []
for name, p_ in pts.items():
    for tgt, label in (("rv_x", "rv_x (valor esperado de la bola en juego)"), ("rv", "rv observado")):
        ok = np.isfinite(p_) & df[tgt].notna().to_numpy()
        e = V.direct_runs_per_point(np.asarray(p_)[ok], df[tgt].to_numpy(float)[ok], groups[ok])
        est[(name, tgt)] = e
        rows.append(dict(escala=name, objetivo=tgt, carreras_por_punto_lanzamiento=e["per_point"], lo=e["lo"], hi=e["hi"],
                         n=e["n"], pitchers=e["n_groups"]))
direct = pd.DataFrame(rows)
direct.round(7).to_csv(OUT / "runs_per_point_direct.csv", index=False)
# control cruzado: σ del scaler × pendiente de calibración (xRV predicho OOF) × 0.1 debe ser similar a la estimación directa de Stuff+
cal = V.calibration_slope(oofdf["stuff_xrv"].to_numpy(float), df["rv_x"].to_numpy(float), groups)
check = 0.1 * sigma * cal["slope"]
pd.DataFrame([dict(sigma_scaler_all=sigma, **{f"sigma_{k}": v for k, v in sigma_years.items()}, **cal, sigma_x_slope_x_0p1=check,
                   direct_stuff_rv_x=est[("Stuff+", "rv_x")]["per_point"], model_version=PRODUCTION_VERSION,
                   scale_source=str(STUFF_JSON).replace("\\", "/"))]).round(7).to_csv(OUT / "stuff_scale_calibration.csv", index=False)
per_point = {}
for name in pts:
    e = est[(name, "rv_x")]
    per_point |= {f"{name} · rv_x (central)": e["per_point"], f"{name} · rv_x (IC 2.5 %)": e["lo"],
                  f"{name} · rv_x (IC 97.5 %)": e["hi"], f"{name} · rv observado": est[(name, "rv")]["per_point"]}
conv = V.conversion_table(per_point, PITCH_GRID, {"liga": rpw["liga"], "Harp Helú (bucket Extreme)": rpw[EXT]})
conv.round(6).to_csv(OUT / "conversion_table.csv", index=False)
GM_POINTS, GM_PITCHES = 10, 2500
gm = []
for name in pts:
    e = est[(name, "rv_x")]
    for env, r in (("liga", rpw["liga"]), ("Harp Helú (bucket Extreme)", rpw[EXT])):
        runs = [GM_POINTS * GM_PITCHES * v for v in (e["per_point"], e["lo"], e["hi"])]
        gm.append(dict(escala=name, entorno=env, carreras=runs[0], carreras_lo=runs[1], carreras_hi=runs[2],
                       victorias=runs[0] / r, victorias_lo=runs[1] / r, victorias_hi=runs[2] / r))
gm = pd.DataFrame(gm)
gm.round(4).to_csv(OUT / "gm_example.csv", index=False)
# escala realista: dispersión de los puntos MEDIOS por pitcher-temporada (≥ 300 lanzamientos); +10 puntos en TODOS los lanzamientos es un salto enorme
spread = []
for name, p_ in pts.items():
    m = pd.DataFrame({"ps": df["pitcher_anon_id"].astype(str) + "_" + df["year"].astype(str), "x": np.asarray(p_)}).groupby("ps")["x"].agg(["mean", "size"])
    m = m[m["size"] >= 300]
    sd = float(m["mean"].std())
    e = est[(name, "rv_x")]
    for env, r in (("liga", rpw["liga"]), ("Harp Helú (bucket Extreme)", rpw[EXT])):
        runs = sd * GM_PITCHES * e["per_point"]
        spread.append(dict(escala=name, entorno=env, sd_puntos_entre_pitcher_temporadas=sd, pitcher_temporadas=len(m),
                           carreras_por_1sd=runs, victorias_por_1sd=runs / r))
spread = pd.DataFrame(spread)
spread.round(4).to_csv(OUT / "pitcher_spread_example.csv", index=False)

# --- 5. costo observado de la altura y brazo a prueba de altura
sens = V.altitude_sensitivity(df, "rv_x", NO, EXT, min_n=100)
sens_med = V.altitude_sensitivity(df, "rv_x", NO, MED, min_n=100)
ex = V.altitude_proof_example(sens["mean_delta"], sens["tau_hi"], pitches_per_start, home_starts, rpw[EXT])
ex.round(4).to_csv(OUT / "altitude_proof_example.csv", index=False)
pd.DataFrame([dict(entorno="Extreme", **sens), dict(entorno="Medium", **sens_med)]).round(5).to_csv(OUT / "altitude_cost.csv", index=False)

# --- figura: victorias de +10 puntos sostenidos en 2,500 lanzamientos (IC 95 %), por escala y entorno
fig, ax = plt.subplots(figsize=(7, 3.8))
for i, (env, g) in enumerate(gm.groupby("entorno")):
    xs = np.arange(len(g)) + i * 0.38
    ax.bar(xs, g["victorias"], 0.36, label=env, color=[RED, BLACK][i],
           yerr=[g["victorias"] - g["victorias_lo"], g["victorias_hi"] - g["victorias"]], capsize=3)
ax.set_xticks(np.arange(len(g)) + 0.19); ax.set_xticklabels(list(g["escala"]))
ax.set_ylabel("victorias"); ax.legend(fontsize=8)
ax.set_title(f"+{GM_POINTS} puntos sostenidos en {GM_PITCHES:,} lanzamientos")
fig.tight_layout(); fig.savefig(OUT / "stuff_point_wins.png", dpi=130); plt.close(fig)

# --- resumen
def tbl(d: pd.DataFrame, cols: list[str], fmt: str = "{:.4g}") -> str:
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols)
    body = ["| " + " | ".join(("–" if pd.isna(v) else fmt.format(v)) if isinstance(v, (float, np.floating)) else str(v) for v in r) + " |" for r in d[cols].itertuples(index=False)]
    return "\n".join([head] + body)

lines = [
    "# Valor de negocio: Stuff+ → carreras → victorias (HACK-035)", "",
    f"**Datos:** {len(scores)} juegos con marcador reconstruido (suma de `RunsScored` por juego y media entrada; se descartan empates y juegos de < 5 entradas), "
    f"{len(ts)} equipo-temporadas con ≥ 20 juegos (equipos de HACK-003). Carreras por equipo-juego: liga {r_league:.2f}; "
    + ", ".join(f"{b} {r:.2f}" for b, r in r_env.items()) + ".", "",
    "## Carreras por victoria (LMB)", "",
    f"Exponente pitagórico **x = {x:.2f}** (IC 95 % bootstrap {fit['lo']:.2f}–{fit['hi']:.2f}, {fit['n_team_seasons']} equipo-temporadas). "
    "Con W% = RS^x/(RS^x+RA^x), una carrera menos permitida por juego vale x/(4r) de W%: **carreras por victoria = 4r/x**, "
    f"con r las carreras por equipo-juego. Control empírico: pendiente de W% contra diferencia de carreras por juego = {slope:.3f} "
    f"({1/slope:.1f} carreras por victoria por juego).", "",
    tbl(rpw_table, ["entorno", "carreras_por_equipo_juego", "carreras_por_victoria", "victorias_por_100_carreras"]), "",
    f"**Lectura:** en el Harp Helú (bucket Extreme) se anota más, así que cada carrera ahorrada vale **menos** victorias que en la liga "
    f"({rpw[EXT]:.1f} vs {rpw['liga']:.1f} carreras por victoria).", "",
    "## Tabla de conversión: +1 punto → carreras → victorias", "",
    "**Estimación directa, fuera de muestra:** los puntos de Stuff+ y Pitching+ (xRV predicho con validación cruzada por pitcher, escalado con el scaler del modelo: 100 + 10·z) "
    "se regresan contra el run value realizado; las carreras ahorradas por punto y por lanzamiento son menos la pendiente. IC 95 % por pitcher (bootstrap).", "",
    tbl(direct, ["escala", "objetivo", "carreras_por_punto_lanzamiento", "lo", "hi"], "{:.3g}"), "",
    f"Control cruzado (Stuff+ {PRODUCTION_VERSION}): σ de la escala del modelo exportado ({sigma:.5f}, `{STUFF_JSON.as_posix()}`) × calibración {cal['slope']:.2f} × 0.1 = {check:.2e}, "
    f"frente a {est[('Stuff+', 'rv_x')]['per_point']:.2e} directo. El xRV fuera de pliegue es el valor neutral al conteo de `fit_production_stuff` (HACK-057, HACK-078). "
    "Pitching+ usa el xRV combinado con bateador neutral (el que sirve el dashboard) escalado con un `PlusScaler` ajustado con el mismo procedimiento.", "",
    "### Ejemplo para el GM", "",
    f"**+{GM_POINTS} puntos de Stuff+ sostenidos en {GM_PITCHES:,} lanzamientos** (orden de magnitud de una temporada de abridor: ~30 aperturas × ~80 lanzamientos; supuesto, no de los datos):", "",
    tbl(gm, ["escala", "entorno", "carreras", "carreras_lo", "carreras_hi", "victorias", "victorias_lo", "victorias_hi"], "{:.3g}"), "",
    "Cada carrera ahorrada vale menos victorias en el Harp Helú que en la liga (más anotación), pero el valor en carreras es el mismo. "
    "**+10 puntos en todos los lanzamientos es un salto muy grande**: es 1 σ del xRV *por lanzamiento* (incluye conteo, ubicación y contexto), mucho más que la diferencia típica entre pitchers, sobre todo para Pitching+. "
    "Una escala más realista es 1 desviación estándar entre pitcher-temporadas (≥ 300 lanzamientos; observada, incluye ruido de muestreo):", "",
    tbl(spread, ["escala", "entorno", "sd_puntos_entre_pitcher_temporadas", "pitcher_temporadas", "carreras_por_1sd", "victorias_por_1sd"], "{:.3g}"), "",
    "Tabla completa (lanzamientos × entorno × estimación) en `conversion_table.csv`; aquí 1,000 y 2,500 lanzamientos en la liga y en el Harp Helú:", "",
    tbl(conv[conv["lanzamientos"].isin([1000, 2500])], ["escenario", "lanzamientos", "entorno", "carreras", "victorias"], "{:.3g}"), "",
    f"Referencia: un abridor lanza ~{pitches_per_start:.0f} lanzamientos por apertura (mediana de los datos).", "",
    "## Ejemplo: valor de un brazo a prueba de altura", "",
    f"Costo observado de la altura (Δ `rv_x` por lanzamiento, Extreme − sin altitud, intra pitcher-temporada, {sens['n_pitcher_seasons']} pitcher-temporadas con ≥ 100 lanzamientos en ambos): "
    f"**{sens['mean_delta']:+.4f} carreras por lanzamiento** (Medium: {sens_med['mean_delta']:+.4f}). Dispersión verdadera entre pitchers (descontado el ruido de muestreo, método de momentos): "
    f"τ̂ = {sens['tau']:.4f} (sd observada {sens['raw_sd']:.4f}, ruido de muestreo medio {sens['mean_sampling_sd']:.4f}); cota superior 95 % (bootstrap) τ ≤ {sens['tau_hi']:.4f}. "
    "**Con el run value por lanzamiento no se detecta heterogeneidad entre pitchers más allá del ruido**: el ejemplo usa esa cota como la brecha *máxima compatible con los datos*, no como una medición. "
    "La sensibilidad por pitcher con la física (ΔStuff+) está en HACK-018 (`reports/pitcher_sensitivity/`), no con el resultado ruidoso.", "",
    f"Escenario: {home_starts} aperturas en casa por temporada (juegos de local por equipo-temporada en los datos ÷ rotación de 5) × {pitches_per_start:.0f} lanzamientos, "
    f"a {rpw[EXT]:.1f} carreras por victoria en altura.", "",
    tbl(ex, ["brazo", "carreras_extra_por_lanzamiento", "carreras_extra", "victorias_perdidas"]), "",
    f"Brecha entre el brazo de alta pérdida y el de a prueba de altura: **{ex.attrs['gap_runs']:.1f} carreras ≈ {ex.attrs['gap_wins']:.2f} victorias** en esa temporada de aperturas en casa.", "",
    "## Advertencias", "",
    "- `rv_x` valora las bolas en juego con la altitud como rasgo (HACK-030): el costo de la altura incluye parte del modelo de contacto, no solo los lanzamientos.",
    "- La escala de Stuff+ es la del modelo exportado (`web/public/data/models/stuff.json`); si el modelo se reentrena, hay que volver a correr este análisis (la caché OOF está en `artifacts/`, git-ignored).",
    "- Los puntos usan el xRV de los modelos completos fuera de muestra, no el modelo destilado del dashboard (R² 0.92 / 0.94 con ellos): aproximan el mismo número.",
    "- El efecto de un punto es chico por lanzamiento y crece con el volumen: sumas grandes (miles de lanzamientos) y grupos de lanzamientos, no un lanzamiento suelto. El `rv` observado es más ruidoso que `rv_x`: su IC es más ancho.",
    "- Marcadores reconstruidos: partidos incompletos en los datos o carreras fuera de los lanzamientos pueden sesgar; los datos solo cubren una muestra de la temporada por equipo.",
    "- Linealización pitagórica válida cerca de un equipo promedio; ±1σ en sensibilidad supone dispersión aproximadamente normal.",
    "- La identidad CDMX vs Puebla sigue sin verificar (HACK-003): «entorno Extreme» agrupa los parques de altura.",
]
(OUT / "summary.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines[:14]))
print(ex.round(4).to_string()); print(sens, sens_med)
