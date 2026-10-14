"""python -m analysis.tuning.summary — reports/tuning/README.md from the CSVs of the search and the before/after.

The adoption rule was fixed BEFORE the before/after was run: a tuned model is adopted only if (1) its outcome
log-loss improves, (2) first-50 → rest-of-season r, first-200 r and split-half reliability do not drop, and
(3) for Stuff+, the altitude story holds (league ΔStuff+ within 1 point, same most- and least-resistant shapes).
"""
from __future__ import annotations

import json

import pandas as pd

from analysis.tuning.run import OUT

HUMAN_DECISION = (
    "**Decisión del responsable (joahan, 2026-10-14): no se adopta ningún ajuste.** Location+ pasa la regla pero gana poco "
    "(intervalos traslapados) y adoptarlo obliga a regenerar scores, leaderboards, validación y auditoría ya integrados. "
    "Los modelos y el bundle desplegado se quedan como están (no hace falta re-entrenamiento final); este estudio queda "
    "como evidencia de robustez de la configuración de producción.")
TOL = 0.005  # a pitcher-level r may move by sampling noise of this size and still count as "did not drop"


def decide(kf: pd.DataFrame, pk: pd.DataFrame, alt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    both = pd.concat([kf.set_index("model"), pk.set_index("model")])
    for base in ("Stuff+", "Location+", "Pitching+"):
        a, b = both.loc[base], both.loc[f"{base} ajustado"]
        checks = {}
        if "outcome_logloss" in both and pd.notna(a.get("outcome_logloss")):
            checks["log-loss mejora"] = b.outcome_logloss < a.outcome_logloss
        else:
            checks["habilidad vs nulo mejora"] = b.skill_vs_baseline > a.skill_vs_baseline
        for col, label in (("first50_r", "primeros 50 → resto"), ("first200_r", "primeros 200 → resto"),
                           ("split_half_r", "confiabilidad split-half")):
            checks[f"{label} no baja"] = b[col] >= a[col] - TOL
        if base == "Stuff+":
            p, t = alt.set_index("model").loc["Stuff+"], alt.set_index("model").loc["Stuff+ ajustado"]
            checks["historia de altitud se sostiene"] = (abs(t.league_delta - p.league_delta) <= 1
                                                        and t.best_shape == p.best_shape and t.worst_shape == p.worst_shape)
        failed = [k for k, v in checks.items() if not v]
        rows.append(dict(model=base, adopt=not failed, failed="; ".join(failed)))
    return pd.DataFrame(rows)


def _fmt(x, nd=3):
    return f"{x:.{nd}f}"


def build() -> str:
    chosen = json.loads((OUT / "chosen.json").read_text())
    kf = pd.read_csv(OUT / "before_after_kfold.csv")
    pk = pd.read_csv(OUT / "before_after_pitching_kfold.csv")
    pk = pk[pk.model != "baseline"]
    alt = pd.read_csv(OUT / "before_after_altitude.csv")
    hv = pd.read_csv(OUT / "holdouts" / "validation_table.csv")
    hv = hv[hv.metric == "skill_vs_baseline"].pivot(index="model", columns="split", values="value")
    bias = pd.read_csv(OUT / "holdouts" / "altitude_bias.csv")
    bias = bias[(bias.split == "park_holdout") & (bias.altitude_category == "Extreme Altitude")].set_index("model")
    dec = decide(kf, pk, alt).set_index("model")
    dec.reset_index().to_csv(OUT / "decision.csv", index=False)

    L = ["# Ajuste de modelos (HACK-028)", "",
         "Generado por `python -m analysis.tuning.summary` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.", "",
         "## Qué encontramos",
         "Los modelos de producción entrenan un número FIJO de rondas (300 multiclase a learning rate 0.08) sin early stopping. "
         "En pitchers que el modelo no vio eso sobreajusta. La búsqueda (solo 2024–25, 3 pliegues por pitcher, rondas elegidas "
         "con un conjunto interno de pitchers y evaluadas en el pliegue externo; la temporada 2026 nunca se usa) mejora la "
         "pérdida de los 14 boosters:", "",
         "| Booster | Producción (rondas) | Pérdida producción | Ajustado (rondas) | Pérdida ajustada |", "|---|---|---|---|---|"]
    for name, c in chosen.items():
        L.append(f"| {name} | {c['production_rounds']} | {c['production_loss']:.4f} | {c['rounds']} | {c['test_loss']:.4f} |")
    L += ["", "Fuente: `chosen.json`, `search_*.csv`, `search_summary.csv` (pérdida = log-loss o MSE en el pliegue externo, "
          "media de 3 pliegues).", "",
          "## Antes / después (regla de adopción fijada antes de correrlo)", "",
          "Se adopta un modelo ajustado solo si: mejora su log-loss; no bajan (más de "
          f"{TOL}) la predicción primeros 50 / 200 lanzamientos → resto de la temporada ni la confiabilidad split-half; "
          "y, para Stuff+, se sostiene la historia de altitud (ΔStuff+ de la liga a ±1 punto, mismas formas mejor y peor).", "",
          "| Modelo | Log-loss | Habilidad vs nulo (k-fold) | Pendiente de calibración | 50 → resto (r) | 200 → resto (r) | "
          "Split-half (r) | Temporada | Estadio | Sesgo en altitud extrema |", "|---|---|---|---|---|---|---|---|---|---|"]
    both = pd.concat([kf.set_index("model"), pk.set_index("model")])
    for m in ("Stuff+", "Stuff+ ajustado", "Location+", "Location+ ajustado", "Pitching+", "Pitching+ ajustado"):
        r = both.loc[m]
        ll = _fmt(r.outcome_logloss, 4) if pd.notna(r.get("outcome_logloss", float("nan"))) else "—"
        L.append(f"| {m} | {ll} | {100 * r.skill_vs_baseline:+.2f} % | {_fmt(r.calibration_slope, 2)} | {_fmt(r.first50_r)} | "
                 f"{_fmt(r.first200_r)} | {_fmt(r.split_half_r)} | {100 * hv.loc[m, 'season_holdout']:+.2f} % | "
                 f"{100 * hv.loc[m, 'park_holdout']:+.2f} % | {bias.loc[m, 'bias_obs_minus_pred']:+.4f} |")
    a = alt.set_index("model")
    L += ["", "Fuentes: `before_after_kfold.csv` (Stuff+, Location+: 5 pliegues por pitcher, todas las temporadas), "
          "`before_after_pitching_kfold.csv` (Pitching+ con combinación anidada), `holdouts/` (suite de HACK-014: temporada "
          "2024–25 → 2026, estadio sin altitud extrema → extrema; sesgo = observado − predicho en altitud extrema).", "",
          f"Historia de altitud (`before_after_altitude.csv`): ΔStuff+ de la liga {a.loc['Stuff+', 'league_delta']:+.1f} "
          f"(producción) vs {a.loc['Stuff+ ajustado', 'league_delta']:+.1f} (ajustado); forma que más resiste "
          f"{a.loc['Stuff+', 'best_shape']} vs {a.loc['Stuff+ ajustado', 'best_shape']}; la que más pierde "
          f"{a.loc['Stuff+', 'worst_shape']} ({a.loc['Stuff+', 'worst_delta']:+.1f}) vs {a.loc['Stuff+ ajustado', 'worst_shape']} "
          f"({a.loc['Stuff+ ajustado', 'worst_delta']:+.1f}).", "", "## Decisión", ""]
    for m, r in dec.iterrows():
        L.append(f"- **{m}: {'adoptar' if r.adopt else 'no adoptar'}**" + (f" (no cumple: {r.failed})." if r.failed else "."))
    L += ["", HUMAN_DECISION]
    s, st = both.loc["Stuff+"], both.loc["Stuff+ ajustado"]
    L += ["", "**Lectura.** El Stuff+ más regularizado predice mejor cada lanzamiento (log-loss, pendiente de calibración "
          f"{_fmt(s.calibration_slope, 2)} → {_fmt(st.calibration_slope, 2)}) pero distingue peor entre pitchers "
          f"(split-half {_fmt(s.split_half_r, 2)} → {_fmt(st.split_half_r, 2)}), que es para lo que sirve Stuff+. La varianza "
          "extra del modelo de producción no es solo ruido: lleva información estable de cada pitcher. Por eso Stuff+ se "
          "queda como está, y su sobre-dispersión por lanzamiento ya se corrige al convertir puntos a carreras "
          "(HACK-035 estima carreras por punto directamente, fuera de muestra).", "",
          "## Límites",
          "- Rejilla pequeña (regularización y número de rondas; learning rate 0.05); el criterio de búsqueda es la pérdida por "
          "lanzamiento, que no es lo mismo que la discriminación entre pitchers.",
          "- Mismas preparaciones transductivas que HACK-014 (identidad, densidad por juego, valores de carrera).", ""]
    return "\n".join(L)


def main() -> None:
    text = build()
    (OUT / "README.md").write_text(text, encoding="utf-8")
    print("wrote", OUT / "README.md")


if __name__ == "__main__":
    main()
