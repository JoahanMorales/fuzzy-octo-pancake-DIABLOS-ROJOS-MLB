"""HACK-035: carreras por victoria de la LMB, conversión Stuff+ → carreras → victorias y ejemplo del brazo a prueba de altura.

Uso: python analysis/business_value/run.py  (≈ 3 min: el build de rv_x). Escribe agregados en reports/business_value/.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from stuffplus import targets
from stuffplus import value as V
from stuffplus.io import load_raw
from stuffplus.physics import parks
from stuffplus.schema import clean

warnings.filterwarnings("ignore")
OUT = Path("reports/business_value")
OUT.mkdir(parents=True, exist_ok=True)
NO, MED, EXT = "No Altitude", "Medium Altitude", "Extreme Altitude"
R2_SCENARIOS = {"modelo débil (R²=0.25 % del xRV)": 0.0025, "modelo moderado (R²=1 %)": 0.01, "modelo fuerte (R²=3 %)": 0.03}
PITCH_GRID = (100, 500, 1000, 2500)
RED, BLACK = "#B71C1C", "#111111"

raw = clean(load_raw())
df, _, _ = targets.build(raw)

# --- 1. marcadores, equipo-temporadas y exponente pitagórico
scores = V.game_scores(df)
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

# --- 4. escenarios de σ(xRV predicho) y tabla de conversión
sd_rv = float(df["rv_x"].std())
sigmas = {k: V.sigma_from_variance_explained(sd_rv, r2) for k, r2 in R2_SCENARIOS.items()}
conv = V.conversion_table(sigmas, PITCH_GRID, {"liga": rpw["liga"], "Harp Helú (bucket Extreme)": rpw[EXT]})
conv.round(5).to_csv(OUT / "conversion_table.csv", index=False)

# --- 5. costo observado de la altura y brazo a prueba de altura
sens = V.altitude_sensitivity(df, "rv_x", NO, EXT, min_n=100)
sens_med = V.altitude_sensitivity(df, "rv_x", NO, MED, min_n=100)
ex = V.altitude_proof_example(sens["mean_delta"], sens["tau_hi"], pitches_per_start, home_starts, rpw[EXT])
ex.round(4).to_csv(OUT / "altitude_proof_example.csv", index=False)
pd.DataFrame([dict(entorno="Extreme", **sens), dict(entorno="Medium", **sens_med)]).round(5).to_csv(OUT / "altitude_cost.csv", index=False)

# --- figura: victorias por +1 punto de Stuff+ sostenido en 1,000 lanzamientos, por escenario y entorno
sub = conv[conv["lanzamientos"] == 1000]
fig, ax = plt.subplots(figsize=(7, 3.8))
for i, (env, g) in enumerate(sub.groupby("entorno")):
    ax.bar(np.arange(len(g)) + i * 0.38, g["victorias"], 0.36, label=env, color=[RED, BLACK][i])
ax.set_xticks(np.arange(len(g)) + 0.19); ax.set_xticklabels([s.split(" (")[0] for s in g["escenario"]], fontsize=8)
ax.set_ylabel("victorias por +1 Stuff+ en 1,000 lanzamientos"); ax.legend(fontsize=8)
ax.set_title("Valor de un punto de Stuff+ (según la calidad del modelo)")
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
    "## Tabla de conversión: +1 punto de Stuff+ → carreras → victorias", "",
    "Por definición de la escala (HACK-013), 1 punto = 0.1 σ del xRV *predicho* por lanzamiento. Esa σ depende del modelo final (HACK-010/012), "
    "que todavía no está integrado, así que se muestran **escenarios de calidad del modelo** (fracción de la varianza del `rv_x` por lanzamiento que explica; "
    f"σ(rv_x) = {sd_rv:.3f}). **No son resultados del modelo**: cuando exista el bundle final se sustituye la σ real en `analysis/business_value/run.py`.", "",
    tbl(conv, ["escenario", "lanzamientos", "entorno", "carreras", "victorias"], "{:.4g}"), "",
    f"Referencia: un abridor lanza ~{pitches_per_start:.0f} lanzamientos por apertura (mediana de los datos).", "",
    "## Ejemplo: valor de un brazo a prueba de altura", "",
    f"Costo observado de la altura (Δ `rv_x` por lanzamiento, Extreme − sin altitud, intra pitcher-temporada, {sens['n_pitcher_seasons']} pitcher-temporadas con ≥ 100 lanzamientos en ambos): "
    f"**{sens['mean_delta']:+.4f} carreras por lanzamiento** (Medium: {sens_med['mean_delta']:+.4f}). Dispersión verdadera entre pitchers (descontado el ruido de muestreo, método de momentos): "
    f"τ̂ = {sens['tau']:.4f} (sd observada {sens['raw_sd']:.4f}, ruido de muestreo medio {sens['mean_sampling_sd']:.4f}); cota superior 95 % (bootstrap) τ ≤ {sens['tau_hi']:.4f}. "
    "**Con el run value por lanzamiento no se detecta heterogeneidad entre pitchers más allá del ruido**: el ejemplo usa esa cota como la brecha *máxima compatible con los datos*, no como una medición. "
    "La sensibilidad por pitcher la medirá HACK-018 con la física (ΔStuff+), no con el resultado ruidoso.", "",
    f"Escenario: {home_starts} aperturas en casa por temporada (juegos de local por equipo-temporada en los datos ÷ rotación de 5) × {pitches_per_start:.0f} lanzamientos, "
    f"a {rpw[EXT]:.1f} carreras por victoria en altura.", "",
    tbl(ex, ["brazo", "carreras_extra_por_lanzamiento", "carreras_extra", "victorias_perdidas"]), "",
    f"Brecha entre el brazo de alta pérdida y el de a prueba de altura: **{ex.attrs['gap_runs']:.1f} carreras ≈ {ex.attrs['gap_wins']:.2f} victorias** en esa temporada de aperturas en casa.", "",
    "## Advertencias", "",
    "- `rv_x` valora las bolas en juego con la altitud como rasgo (HACK-030): el costo de la altura incluye parte del modelo de contacto, no solo los lanzamientos.",
    "- La tabla Stuff+ → carreras usa escenarios, no el modelo final (aún no integrado). Las cifras absolutas cambiarán; la fórmula y el cociente entre entornos no.",
    "- Marcadores reconstruidos: partidos incompletos en los datos o carreras fuera de los lanzamientos pueden sesgar; los datos solo cubren una muestra de la temporada por equipo.",
    "- Linealización pitagórica válida cerca de un equipo promedio; ±1σ en sensibilidad supone dispersión aproximadamente normal.",
    "- La identidad CDMX vs Puebla sigue sin verificar (HACK-003): «entorno Extreme» agrupa los parques de altura.",
]
(OUT / "summary.md").write_text("\n".join(lines))
print("\n".join(lines[:14]))
print(ex.round(4).to_string()); print(sens, sens_med)
