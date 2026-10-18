"""One validation summary for the paper and the jury, built only from the CSVs it cites (HACK-014).

    python -m stuffplus.validation.summary

Sources (all aggregates, real data):
  pitcher 5-fold OOF, production settings ...... reports/{stuff_model,location_model,pitching_model}/metrics.csv
  season and park holdouts, production ......... reports/validation/official_full/
  leave-one-park-out (20 parks) and stability ... reports/validation/official_fast/ (fast settings: conservative)
Writes reports/validation/summary.md and reports/validation/headline.csv. No number is typed by hand.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from stuffplus import config

MODEL_FILES = {"Stuff+": "stuff_model", "Location+": "location_model", "Pitching+": "pitching_model"}
MODEL_ROWS = {"Stuff+": "stuff_v1", "Location+": "location_v1", "Pitching+": "pitching_combined"}


def _pct(x: float) -> str:
    return f"{100 * x:+.2f} %"


def headline(reports: Path) -> pd.DataFrame:
    rows = []
    for model, folder in MODEL_FILES.items():
        m = pd.read_csv(reports / folder / "metrics.csv")
        if "target" in m:
            m = m[m.target == "rv_x"]
        if "baseline_name" in m:
            m = m[m.baseline_name == "mean xRV by count"]
        r = m[m.model == MODEL_ROWS[model]].iloc[0]
        rows.append(dict(split="pitcher_kfold", settings="production", model=model, skill=r.skill_vs_baseline,
                         lo=r.skill_lo, hi=r.skill_hi, source=f"reports/{folder}/metrics.csv"))
    full = pd.read_csv(reports / "validation" / "official_full" / "validation_table.csv")
    w = full.pivot_table(index=["split", "model"], columns="metric", values="value").reset_index()
    for _, r in w[w.model.isin(MODEL_FILES)].iterrows():
        rows.append(dict(split=r.split, settings="production", model=r.model, skill=r.skill_vs_baseline,
                         lo=r.skill_lo, hi=r.skill_hi, source="reports/validation/official_full/validation_table.csv"))
    fast = pd.read_csv(reports / "validation" / "official_fast" / "validation_table.csv")
    lopo = fast[fast.split.str.startswith("leave_one_park_out") & (fast.metric == "skill_vs_baseline")]
    for model, g in lopo[lopo.model.isin(MODEL_FILES)].groupby("model"):
        rows.append(dict(split="leave_one_park_out (20 parks)", settings="fast", model=model, skill=g.value.mean(),
                         lo=g.value.min(), hi=g.value.max(), parks=len(g), parks_positive=int((g.value > 0).sum()),
                         source="reports/validation/official_fast/validation_table.csv (lo/hi = min/max over parks)"))
    return pd.DataFrame(rows)


def build(reports: Path | None = None) -> tuple[str, pd.DataFrame]:
    reports = reports or config.REPORTS_DIR
    h = headline(reports)
    order = ["pitcher_kfold", "season_holdout", "park_holdout", "leave_one_park_out (20 parks)"]
    lines = ["# Validación · resumen (HACK-014)", "",
             "Generado por `python -m stuffplus.validation.summary` desde los CSV citados; ninguna cifra se escribió a mano.",
             "Objetivo `rv_x` (run value esperado LMB). Línea base de la rúbrica: xRV medio por conteo, ajustada solo con "
             "entrenamiento. Habilidad = reducción del RMSE vs esa línea base; IC 95 % remuestreando pitchers completos.", "",
             "## Habilidad fuera de muestra vs el modelo nulo de la rúbrica", "",
             "| Partición | Ajustes | Stuff+ | Location+ | Pitching+ |", "|---|---|---|---|---|"]
    for split in order:
        sub = h[h.split == split].set_index("model")
        if sub.empty:
            continue
        cells = []
        for model in MODEL_FILES:
            r = sub.loc[model]
            if split.startswith("leave_one_park_out"):
                cells.append(f"{_pct(r.skill)} (mín {_pct(r.lo)}, máx {_pct(r.hi)}; {int(r.parks_positive)}/{int(r.parks)} > 0)")
            else:
                cells.append(f"{_pct(r.skill)} [{_pct(r.lo)}, {_pct(r.hi)}]")
        lines.append(f"| {split} | {sub.iloc[0].settings} | " + " | ".join(cells) + " |")
    lines += ["", "Stuff+ puro no usa conteo ni ubicación (definición del reto), así que por lanzamiento no supera al modelo "
              "por conteo; su valor está en la estabilidad y la predicción a nivel pitcher (abajo). Pitching+ y Location+ "
              "sí lo superan en todas las particiones.", ""]

    bias = pd.read_csv(reports / "validation" / "official_full" / "altitude_bias.csv")
    pb = bias[(bias.split == "park_holdout") & (bias.altitude_category == "Extreme Altitude")].set_index("model")
    base = pb.loc["baseline", "bias_obs_minus_pred"]
    lines += ["## ¿Sirve la física? Sesgo en altitud extrema sin haberla visto", "",
              "Park holdout: se entrena SOLO con juegos sin altitud y de altitud media y se predicen los "
              f"{int(pb.loc['baseline', 'n']):,} lanzamientos de altitud extrema. Sesgo = carreras observadas − predichas por "
              "lanzamiento (positivo = el modelo subestima el daño). Fuente: `reports/validation/official_full/altitude_bias.csv`.",
              "", "| Modelo | Sesgo (carreras/lanzamiento) | ± ee | vs línea base |", "|---|---|---|---|"]
    for model in ["baseline", "Stuff+ physics neutral", "Stuff+ no density", "Stuff+", "Location+", "Pitching+"]:
        if model in pb.index:
            r = pb.loc[model]
            rel = "—" if model == "baseline" else f"{100 * (r.bias_obs_minus_pred / base - 1):+.0f} %"
            lines.append(f"| {model} | {r.bias_obs_minus_pred:+.4f} | {r.se:.4f} | {rel} |")
    with_rho, without = pb.loc["Stuff+", "bias_obs_minus_pred"], pb.loc["Stuff+ no density", "bias_obs_minus_pred"]
    lines += ["", f"Con la densidad del aire como variable, Stuff+ deja el {100 * with_rho / without:.0f} % del sesgo de la "
              f"misma arquitectura sin ella ({with_rho:+.4f} vs {without:+.4f}), extrapolando a un aire que nunca vio en "
              "entrenamiento.", ""]

    stab = pd.read_csv(reports / "validation" / "official_fast" / "stability.csv")
    pred = pd.read_csv(reports / "stuff_model" / "predictiveness.csv")
    ppred = pd.read_csv(reports / "pitching_model" / "predictiveness.csv")
    lines += ["## Estabilidad y predicción a nivel pitcher", "",
              "| Prueba | Stuff+ | Pitching+ | Resultados observados | Fuente |", "|---|---|---|---|---|"]
    for n in (50, 200):
        s, p = pred[pred.first_n == n].iloc[0], ppred[ppred.first_n == n].iloc[0]
        lines.append(f"| Primeros {n} lanzamientos → resto de la temporada (r) | {s.stuff_model:.3f} | {p.stuff_model:.3f} | "
                     f"{s.observed_rv:.3f} | `reports/{{stuff,pitching}}_model/predictiveness.csv` |")
    for check in ("year_stability_2024_2025", "year_stability_2025_2026"):
        rows = stab[(stab.check == check) & (stab.source == "pred")].set_index("model")
        if {"Stuff+", "Pitching+"} <= set(rows.index):
            lines.append(f"| Estabilidad {check[-9:].replace('_', '→')} (r, pitcher-temporada) | "
                         f"{rows.loc['Stuff+', 'correlation']:.3f} | {rows.loc['Pitching+', 'correlation']:.3f} | — | "
                         "`official_fast/stability.csv` |")
    lines += v1_to_v2(reports)
    lines += ["", "## Límites", "",
              "- Preparación transductiva: la identidad de lanzamiento, la densidad por juego, las referencias de arsenal y los "
              "valores de carrera LMB (RE, pesos lineales, valor esperado del batazo) se estiman una vez con todos los datos. "
              "Ningún paso usa el resultado de un lanzamiento como variable de ese lanzamiento, y todos los modelos se ajustan "
              "solo con entrenamiento; aun así las cifras son condicionales a esas entradas.",
              "- Leave-one-park-out y estabilidad año a año vienen de la corrida rápida (pocos árboles): son conservadoras.",
              "- Los parques son franquicias inferidas (HACK-003), no etiquetas verificadas de estadio.", ""]
    return "\n".join(lines), h


def v1_to_v2(reports: Path) -> list[str]:
    """The production change of HACK-057: Stuff+ v1 → v2 on the same splits, pitcher level, altitude and calibration."""
    sv = reports / "stuff_v2"
    if not (sv / "skill.csv").exists():
        return []
    skill = pd.read_csv(sv / "skill.csv").set_index(["split", "model"])
    pl = pd.read_csv(sv / "pitcher_level.csv").set_index("model")
    bias = pd.read_csv(sv / "altitude_bias.csv").set_index("model")
    alt = pd.read_csv(sv / "altitude.csv").set_index("model")
    v1, v2, v2f = "Stuff+ v1", "Stuff+ v2", "Stuff+ v2 (familia)"
    rows = []
    for split in ("pitcher_kfold", "season_holdout", "park_holdout"):
        if (split, v1) in skill.index and (split, v2) in skill.index:
            a, b = skill.loc[(split, v1)], skill.loc[(split, v2)]
            rows.append((f"Habilidad vs nulo, {split}", f"{_pct(a.skill_vs_baseline)} [{_pct(a.skill_lo)}, {_pct(a.skill_hi)}]",
                         f"{_pct(b.skill_vs_baseline)} [{_pct(b.skill_lo)}, {_pct(b.skill_hi)}]", "`stuff_v2/skill.csv`"))
    for col, label in (("first50_r", "Primeros 50 → resto (r)"), ("first200_r", "Primeros 200 → resto (r)"),
                       ("split_half_r", "Mitad contra mitad (r)")):
        rows.append((label, f"{pl.loc[v1, col]:.3f}", f"{pl.loc[v2f, col]:.3f}", "`stuff_v2/pitcher_level.csv`"))
    rows.append(("Sesgo en altitud extrema no vista (carreras/lanz.)", f"{bias.loc[v1, 'bias_obs_minus_pred']:+.4f}",
                 f"{bias.loc[v2, 'bias_obs_minus_pred']:+.4f}", "`stuff_v2/altitude_bias.csv`"))
    rows.append(("ΔStuff+ de liga en el aire del Harp Helú", f"{alt.loc[v1, 'league_delta']:+.1f}",
                 f"{alt.loc[v2f, 'league_delta']:+.1f}", "`stuff_v2/altitude.csv`"))
    prod = reports / "altitude_delta" / "delta_by_shape.csv"
    if prod.exists():
        r = pd.read_csv(prod).iloc[0]
        rows.append(("ΔStuff+ de liga en producción (v2 + temperatura)", "", f"{r.delta_stuff - r.relative_to_league:+.1f}",
                     "`altitude_delta/delta_by_shape.csv` (Δ − relativo a la liga)"))
    cal = reports / "calibration" / "decision.csv"
    if cal.exists():
        d = pd.read_csv(cal)
        chosen = d[d.method == "ELEGIDO"].set_index("model")["chosen"]
        rows.append(("Calibración elegida (regla de HACK-053)", str(chosen.get("stuff_v1", "none")),
                     str(chosen.get("stuff_v2", "none")), "`calibration/decision.csv`"))
    lines = ["", "## Stuff+ v1 → v2 (HACK-057, en producción)", "",
             "Desde HACK-057 el Stuff+ de producción es v2: valor del lanzamiento neutral al conteo (HACK-052) con calibración "
             "por temperatura (HACK-053); Location+ también usa temperatura y Pitching+ queda sin calibrar. Las filas de la "
             "tabla de arriba siguen siendo la corrida oficial de v1; estas comparan v1 y v2 en las mismas particiones. "
             "La regla R3 (ΔStuff+ de liga a ±1.5 de v1) no se cumple y el humano adoptó R4 (sesgo en altitud no vista).", "",
             "| Prueba | v1 | v2 | Fuente |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {src} |" for a, b, c, src in rows]
    return lines


def main() -> None:
    text, h = build()
    out = config.REPORTS_DIR / "validation"
    (out / "summary.md").write_text(text, encoding="utf-8")
    h.round(5).to_csv(out / "headline.csv", index=False)
    print(text)


if __name__ == "__main__":
    main()
