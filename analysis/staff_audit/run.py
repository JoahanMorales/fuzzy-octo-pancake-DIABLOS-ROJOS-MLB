"""python -m analysis.staff_audit.run [--scores PATH] [--shift 0.10]  (~2 min after HACK-016's scoring run).

Writes reports/staff_audit/ (aggregates only) and its README.md, built from those CSVs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from stuffplus import config, staff
from stuffplus.io import load_raw
from stuffplus.physics.constants import RHO_HARP_HELU
from stuffplus.schema import clean

OUT = config.REPORTS_DIR / "staff_audit"


def artifact(rel: str) -> Path:
    """``artifacts/<rel>`` of this checkout, else of the main checkout (uak worktrees share it)."""
    here = config.ARTIFACTS_DIR / rel
    main = config.main_checkout_root()
    if here.exists() or main is None:
        return here
    return main / "artifacts" / rel


def _f(x: float, nd: int = 1) -> str:
    return f"{x:+.{nd}f}"


def readme(t: dict[str, pd.DataFrame], franchises: list[int], rates: dict) -> str:
    p, mix, rot, rr, bp, rs = (t[k] for k in ("pitchers", "mix_runs", "rotation", "rotation_runs", "bullpen",
                                               "runs_saved"))
    q = t["params"].iloc[0]
    L = ["# Auditoría del staff candidato de los Diablos (HACK-032)", "",
         "Generado por `python -m analysis.staff_audit.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.", "",
         f"**Identificación inferida.** Los ids son anónimos. El staff \"Diablos\" son los pitchers de las dos franquicias con "
         f"el aire más ligero ({', '.join(map(str, franchises))}; `reports/park_id/franchise_rho.csv`). Los datos no separan "
         "con confianza CDMX de Puebla (`reports/park_id/harp_helu.md`), así que cada tabla se da **por franquicia** y nunca "
         "se juntan. Confirmar con el staff del club.", "",
         "**Dos sabores de Stuff+.** `stuff_plus` = neutral (nivel del mar, 100 = liga); `stuff_plus_harp_helu` = el mismo "
         f"lanzamiento en aire del Harp Helú (ρ = {RHO_HARP_HELU}); ΔCDMX = la diferencia. Las recomendaciones usan el modelo "
         "(todos los lanzamientos del pitcher); los splits casa/visita observados son pocos y van solo como control.", ""]
    for f in franchises:
        pf, mf, rf, bf = p[p.franchise == f], mix[mix.franchise == f], rot[rot.franchise == f], bp[bp.franchise == f]
        tot = rs[(rs.franchise == f) & (rs.component == "total")]
        L += [f"## Franquicia {f}", "",
              f"{len(pf)} pitchers con ≥ {int(q.min_pitches)} lanzamientos ({(pf.role == 'abridor').sum()} abridores, "
              f"{(pf.role == 'relevista').sum()} relevistas). Stuff+ neutral medio {pf.stuff_plus.mean():.1f}; en aire del "
              f"Harp Helú {pf.stuff_plus_harp_helu.mean():.1f} (ΔCDMX {_f(pf.delta_cdmx.mean())}).", "",
              f"Control de la física: Stuff+ neutral en casa − visita = {_f(pf.neutral_home_minus_road.mean(), 2)} (≈ 0 si la "
              f"traducción es correcta); Stuff+ en el aire real casa − visita = {_f(pf.own_air_home_minus_road.mean())} "
              "(el efecto del aire)."]
        if "hack018_observed_eb" in pf:
            c = pf[["delta_cdmx", "hack018_observed_eb"]].dropna()
            if len(c) >= 5:
                L += [f"Contra HACK-018 (`reports/pitcher_sensitivity/pitchers.csv`): la correlación entre el ΔCDMX del modelo "
                      f"y el delta observado del mismo pitcher es {c.delta_cdmx.corr(c.hack018_observed_eb):.2f} "
                      f"({len(c)} pitchers con delta observado)."]
        L += [""]
        if len(mf):
            top = mf.iloc[0]
            L += [f"**Mezcla en casa.** {len(mf)} de {len(pf)} pitchers tienen un lanzamiento claramente peor en aire del "
                  f"Harp Helú (≥ {q.min_gap:.0f} puntos de Stuff+ por debajo de su mejor lanzamiento con uso ≥ "
                  f"{100 * q.min_usage:.0f} %). Mover {100 * q['shift']:.0f} puntos de uso en casa (o todo el uso si es menor) "
                  f"al lanzamiento en el que apoyarse ahorra {mf.runs_saved_per_season.sum():.1f} carreras por temporada en "
                  f"total. El mayor caso: {top.pitcher_anon_id} ({top.role}), de *{top.cut_pitch}* ({top.cut_stuff_hh:.1f} en "
                  f"aire CDMX) a *{top.lean_pitch}* ({top.lean_stuff_hh:.1f}): {top.runs_saved_per_season:.2f} carreras. "
                  "Detalle: `staff_pitch_plan.csv`, `mix_runs.csv`.", ""]
        if len(rf):
            L += [f"**Rotación ({int(rf.season.iloc[0])}, {len(rf)} abridores con ≥ {int(q.min_starts)} aperturas).** "
                  "Orden en casa: " + ", ".join(rf.sort_values("home_order").pitcher_anon_id) + ". Orden de visita: "
                  + ", ".join(rf.sort_values("road_order").pitcher_anon_id) + "."]
            r = rr[rr.franchise == f]
            if len(r):
                r = r.iloc[0]
                L += ["El orden **no cambia** entre casa y visita: la resistencia a la altura no alcanza a reordenar a estos "
                      "abridores." if r.orders_spearman >= 0.999 else
                      f"Los órdenes difieren poco (Spearman {r.orders_spearman:.2f})."]
                L += [f"Lo que sí cambia es **a quién le tocan las aperturas en casa**: pasar aperturas en casa de "
                      f"{r.worst_resilience} (el menos resistente) a {r.best_resilience} (el más resistente; brecha "
                      f"{r.resilience_gap_points:.1f} puntos de Stuff+, {r.pitches_per_start:.0f} lanzamientos por apertura) "
                      f"vale {r.runs_per_swapped_start:.2f} carreras por apertura. Con a lo más una por serie en casa y el tope "
                      f"que permite la temporada ({r.swaps:.0f} cambios: aperturas en casa del primero y de visita del "
                      f"segundo; series de {int(q.games_per_series)} juegos supuestas) son {r.runs_saved_per_season:.2f} "
                      "carreras por temporada."]
            L += ["Detalle: `rotation.csv`, `rotation_runs.csv`.", ""]
        if len(bf):
            L += [f"**Bullpen.** {len(bf)} relevistas. Más valiosos en casa: "
                  + ", ".join(bf.sort_values("home_leverage_rank").pitcher_anon_id.head(3))
                  + ". Ventaja por lado del bateador **por encima de la normal de la liga** para su mano: "
                  f"{(bf.matchup == 'vs zurdos').sum()} vs zurdos, {(bf.matchup == 'vs derechos').sum()} vs derechos, "
                  f"{(bf.matchup == 'ambos lados').sum()} sin ventaja clara (diferencia ≥ {q.platoon_points:.1f} puntos de "
                  f"Pitching+ y ≥ {int(q.min_side)} lanzamientos por lado). Detalle: `bullpen.csv`.", ""]
        if len(tot):
            tt = tot.iloc[0]
            L += [f"**Total proyectado:** {tt.runs_per_season:.1f} carreras por temporada ≈ {tt.wins_per_season:.2f} victorias "
                  f"(a {rates['rpw_extreme']:.1f} carreras por victoria en altitud extrema, HACK-035).", ""]
    L += ["## Supuestos y límites", "",
          f"- Carreras por punto y lanzamiento: Stuff+ {rates['stuff']:.6f}, Pitching+ {rates['pitching']:.5f} "
          "(`reports/business_value/runs_per_point_direct.csv`, OOF directo). Victorias: `runs_per_win.csv`.",
          "- La mezcla supone que cada lanzamiento conserva su calidad al usarlo un poco más o menos y que los bateadores no "
          "se adaptan: es una estimación optimista de primer orden.",
          "- Valor en casa de un pitcher = valor neutral (Pitching+) + resistencia a la altura (ΔCDMX del pitcher − ΔCDMX de la "
          "liga, a la tasa de Stuff+). La asignación de aperturas solo cambia por esa resistencia: la calidad neutral es la "
          "misma en cualquier estadio.",
          "- \"Por temporada\" = con los juegos en casa que hay en los datos de cada temporada (cobertura parcial; ver abajo). "
          "Con un calendario completo las carreras serían proporcionalmente mayores.",
          "- Abridor = el pitcher con más lanzamientos en la primera entrada de su equipo en ese juego. Casa = su equipo "
          "inferido es el local del juego (HACK-003).",
          "- Muestras pequeñas en casa (juegos en casa por temporada: " + "; ".join(
              f"franquicia {f}: " + "/".join(str(int(n)) for n in g.sort_values("year").home_games)
              for f, g in t["home_games"].groupby("franchise")) + ", `home_games.csv`): por eso las recomendaciones usan "
          "el modelo y no los resultados en casa. Umbrales: `params.csv`.", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scores", type=Path, default=None)
    ap.add_argument("--shift", type=float, default=staff.PARAMS["shift"])
    args = ap.parse_args()
    scores = pd.read_parquet(args.scores or artifact("scores/pitch_scores.parquet"))
    raw = clean(load_raw())[staff.RAW_COLS]
    maps = {k: pd.read_parquet(artifact(f"{k}.parquet")) for k in ("park_map", "team_map")}
    rho = pd.read_csv(config.REPORTS_DIR / "park_id" / "franchise_rho.csv")
    franchises = staff.staff_franchises(rho)
    rates = staff.load_rates(config.REPORTS_DIR)
    d = staff.pitch_context(scores, raw, maps["team_map"], maps["park_map"])
    sens = pd.read_csv(config.REPORTS_DIR / "pitcher_sensitivity" / "pitchers.csv")
    t = staff.audit(d, franchises, rates, sens=sens, shift=args.shift)
    OUT.mkdir(parents=True, exist_ok=True)
    names = {"pitchers": "staff_pitchers", "pitch_plan": "staff_pitch_plan"}
    for k, df in t.items():
        df.round(5).to_csv(OUT / f"{names.get(k, k)}.csv", index=False)
    text = readme(t, franchises, rates)
    (OUT / "README.md").write_text(text, encoding="utf-8")
    print(f"Wrote {OUT} ({len(t)} tables + README.md)")


if __name__ == "__main__":
    main()
