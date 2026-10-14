"""python -m analysis.staff_audit.run [--scores PATH] [--shift 0.10]  (~2 min after HACK-016's scoring run).

Writes reports/staff_audit/ (aggregates only) and its README.md, built from those CSVs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from stuffplus import config, staff
from stuffplus.io import load_raw
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


def readme(t: dict[str, pd.DataFrame], franchises: list[int], rates: dict, shift: float) -> str:
    p, plan, mix, rot, rr, bp, rs = (t[k] for k in ("pitchers", "pitch_plan", "mix_runs", "rotation", "rotation_runs",
                                                     "bullpen", "runs_saved"))
    L = ["# Auditoría del staff candidato de los Diablos (HACK-032)", "",
         "Generado por `python -m analysis.staff_audit.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.", "",
         f"**Identificación inferida.** Los ids son anónimos. El staff \"Diablos\" son los pitchers de las dos franquicias con "
         f"el aire más ligero ({', '.join(map(str, franchises))}; `reports/park_id/franchise_rho.csv`). HACK-003 no separa CDMX "
         "de Puebla (P = 0.83), así que cada tabla se da **por franquicia** y nunca se juntan. Confirmar con el staff del club.", "",
         "**Dos sabores de Stuff+.** `stuff_plus` = neutral (nivel del mar, 100 = liga); `stuff_plus_harp_helu` = el mismo "
         "lanzamiento en aire del Harp Helú (ρ 0.819); ΔCDMX = la diferencia. Las recomendaciones usan el modelo (todos los "
         "lanzamientos del pitcher); los splits casa/visita observados son pocos y van solo como control.", ""]
    for f in franchises:
        pf, mf, rf, bf = p[p.franchise == f], mix[mix.franchise == f], rot[rot.franchise == f], bp[bp.franchise == f]
        tot = rs[(rs.franchise == f) & (rs.component == "total")]
        L += [f"## Franquicia {f}", "",
              f"{len(pf)} pitchers con ≥ 200 lanzamientos ({(pf.role == 'abridor').sum()} abridores, "
              f"{(pf.role == 'relevista').sum()} relevistas). Stuff+ neutral medio {pf.stuff_plus.mean():.1f}; en aire del "
              f"Harp Helú {pf.stuff_plus_harp_helu.mean():.1f} (ΔCDMX {_f(pf.delta_cdmx.mean())}).", "",
              f"Control de la física: Stuff+ neutral en casa − visita = {_f(pf.neutral_home_minus_road.mean(), 2)} (≈ 0 si la "
              f"traducción es correcta); Stuff+ en el aire real casa − visita = {_f(pf.own_air_home_minus_road.mean())} "
              "(el efecto del aire).", ""]
        if len(mf):
            top = mf.iloc[0]
            L += [f"**Mezcla en casa.** {len(mf)} de {len(pf)} pitchers tienen un lanzamiento claramente peor en aire del "
                  "Harp Helú (≥ 5 puntos de Stuff+ por debajo de su mejor lanzamiento con uso ≥ 5 %). Mover "
                  f"{100 * shift:.0f} puntos de uso (o todo el uso si es menor) al lanzamiento en el que apoyarse ahorra "
                  f"{mf.runs_saved_per_season.sum():.1f} carreras por temporada en total. El mayor caso: {top.pitcher_anon_id} "
                  f"({top.role}), de *{top.cut_pitch}* ({top.cut_stuff_hh:.1f} en aire CDMX) a *{top.lean_pitch}* "
                  f"({top.lean_stuff_hh:.1f}): {top.runs_saved_per_season:.2f} carreras. Detalle: `staff_pitch_plan.csv`, "
                  "`mix_runs.csv`.", ""]
        if len(rf):
            r = rr[rr.franchise == f]
            L += [f"**Rotación ({int(rf.season.iloc[0])}, {len(rf)} abridores con ≥ 5 aperturas).** Orden en casa: "
                  + ", ".join(rf.sort_values("home_order").pitcher_anon_id) + ". Orden de visita: "
                  + ", ".join(rf.sort_values("road_order").pitcher_anon_id) + "."]
            if len(r):
                r = r.iloc[0]
                L += [f"Correlación de Spearman entre los dos órdenes: {r.orders_spearman:.2f}. Dar una apertura por serie en casa "
                      f"al abridor más resistente a la altura en lugar del menos resistente (brecha "
                      f"{r.resilience_gap_points:.1f} puntos de Stuff+, {r.pitches_per_start:.0f} lanzamientos por apertura, "
                      f"{r.home_series:.0f} series en casa de {int(r.home_games)} juegos, supuesto de 3 juegos por serie) ahorra "
                      f"{r.runs_saved_per_season:.2f} carreras por temporada."]
            L += ["Detalle: `rotation.csv`, `rotation_runs.csv`.", ""]
        if len(bf):
            L += [f"**Bullpen.** {len(bf)} relevistas. Más valiosos en casa: "
                  + ", ".join(bf.sort_values("home_leverage_rank").pitcher_anon_id.head(3))
                  + f". Emparejamientos por lado: {(bf.matchup == 'vs zurdos').sum()} vs zurdos, "
                  f"{(bf.matchup == 'vs derechos').sum()} vs derechos, {(bf.matchup == 'ambos lados').sum()} sin ventaja clara "
                  "(Pitching+ por lado, diferencia ≥ 1.5 puntos y ≥ 100 lanzamientos por lado). Detalle: `bullpen.csv`.", ""]
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
          "liga, a la tasa de Stuff+). La rotación solo cambia por esa resistencia: la calidad neutral es la misma en "
          "cualquier estadio.",
          "- \"Por temporada\" = con los juegos en casa que hay en los datos de cada temporada (cobertura parcial; ver abajo). "
          "Con un calendario completo las carreras serían proporcionalmente mayores.",
          "- Abridor = el pitcher con más lanzamientos en la primera entrada de su equipo en ese juego. Casa = su equipo "
          "inferido es el local del juego (HACK-003).",
          "- Muestras pequeñas en casa (juegos en casa por temporada: " + "; ".join(
              f"franquicia {f}: " + "/".join(str(int(n)) for n in g.sort_values("year").home_games)
              for f, g in t["home_games"].groupby("franchise")) + ", `home_games.csv`): por eso las recomendaciones usan "
          "el modelo y no los resultados en casa.", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scores", type=Path, default=None)
    ap.add_argument("--shift", type=float, default=0.10)
    args = ap.parse_args()
    scores = pd.read_parquet(args.scores or artifact("scores/pitch_scores.parquet"))
    raw = clean(load_raw())[staff.RAW_COLS]
    maps = {k: pd.read_parquet(artifact(f"{k}.parquet")) for k in ("park_map", "team_map")}
    rho = pd.read_csv(config.REPORTS_DIR / "park_id" / "franchise_rho.csv")
    franchises = staff.staff_franchises(rho)
    rates = staff.load_rates(config.REPORTS_DIR)
    d = staff.pitch_context(scores, raw, maps["team_map"], maps["park_map"])
    t = staff.audit(d, franchises, rates, shift=args.shift)
    OUT.mkdir(parents=True, exist_ok=True)
    names = {"pitchers": "staff_pitchers", "pitch_plan": "staff_pitch_plan"}
    for k, df in t.items():
        df.round(5).to_csv(OUT / f"{names.get(k, k)}.csv", index=False)
    text = readme(t, franchises, rates, args.shift)
    (OUT / "README.md").write_text(text, encoding="utf-8")
    print(f"Wrote {OUT} ({len(t)} tables + README.md)")


if __name__ == "__main__":
    main()
