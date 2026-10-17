"""Tunneling por tiempo (HACK-061): ¿el punto de decisión a 150 ms del plato mejora Stuff+?

    python analysis/tunnel/run.py           # datos reales, 10-30 min
    python analysis/tunnel/run.py --fast    # 15 % de los pitchers, pocas rondas: solo para depurar (no es una decisión)

REGLA DE ADOPCION (fijada antes de correr; no se cambia después de ver resultados)
    Se compara `StuffModel(STUFF_FEATURES_INVARIANT + TUNNEL_FEATURES)` contra `StuffModel(STUFF_FEATURES_INVARIANT)`
    con los mismos pliegues por pitcher (`pitcher_group_kfold`), el mismo objetivo (rv_x) y el mismo null
    (media de rv_x por cuenta, `CountBaseline`). Se adopta SOLO si se cumplen las tres:
      1. el límite inferior del IC 95 % (bootstrap por pitcher) de la habilidad por lanzamiento del modelo con
         tunneling es >= la habilidad puntual del modelo base;
      2. para cada tamaño de muestra N de la prueba "primeros N lanzamientos -> resto de la temporada"
         (N = 50, 100, 200), la r a nivel pitcher-temporada con tunneling es >= la del base - 0.005;
      3. la confiabilidad split-half (juegos pares vs impares) con tunneling es >= la del base - 0.005.
    Cualquier otro resultado es "no adoptar". La adopción real pasa por HACK-057 (congelamiento 2026-10-20 12:00).

Chequeo de altitud: dentro del mismo pitch (pitcher x temporada x pitch_key), diferencia Extreme - No Altitude de la
separación en el punto de decisión, la del plato, el cociente de tunneling, la distancia del punto de decisión y el
tiempo de vuelo, con IC 95 % por bootstrap de pitchers. Las rectas principales se excluyen (valen 0 por construcción).

Reportes en reports/tunnel/ (solo agregados): metrics.csv, predictiveness.csv, reliability.csv, altitude_check.csv,
location_audit.csv, verdict.csv y README.md (generado de los CSV).
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stuffplus import config, evaluate, schema, splits  # noqa: E402
from stuffplus.altitude import STUFF_FEATURES_INVARIANT, within_pitcher_observed  # noqa: E402
from stuffplus.baseline import CountBaseline  # noqa: E402
from stuffplus.features.tunnel import DIAGNOSTICS, PARAMS, TUNNEL_FEATURES, add_tunnel_features  # noqa: E402
from stuffplus.models.stuff import StuffModel, matched_sample_predictiveness, split_half_reliability  # noqa: E402

REPORTS = config.REPORTS_DIR / "tunnel"
TOL = 0.005
SIZES = (50, 100, 200)
ALT_METRICS = ["tunnel_dec_sep_in", "tunnel_plate_sep_in", "tunnel_ratio_t", "tunnel_dec_y_ft", "tunnel_t_plate_s"]
ARSENAL_METRICS = ["decision_sep_vs_fb", "plate_sep_vs_fb", "tunnel_ratio"]
FRAME_COLUMNS = sorted(set(
    STUFF_FEATURES_INVARIANT + PARAMS + ["PitchCall", "rv", "rv_x", "pitcher_anon_id", "year", "game_anon_id", "pitch_key",
    "altitude_category", "PitcherThrows", "pitch_id", "primary_fb_id", "pitch_family", "PlateLocSide", "PlateLocHeight", "count"]
    + ARSENAL_METRICS))
LABELS = {
    "tunnel_dec_sep_in": "separación en la decisión (pulg)", "tunnel_plate_sep_in": "separación en el plato (pulg)",
    "tunnel_ratio_t": "cociente de tunneling (tiempo)", "tunnel_dec_y_ft": "distancia al plato del punto de decisión (ft)",
    "tunnel_t_plate_s": "tiempo de vuelo al plato (s)", "decision_sep_vs_fb": "arsenal.py: separación a 23.8 ft (ft)",
    "plate_sep_vs_fb": "arsenal.py: separación en el plato (ft)", "tunnel_ratio": "arsenal.py: cociente por distancia",
}


def _altitude_delta_run():
    spec = importlib.util.spec_from_file_location("alt_run", ROOT / "analysis" / "altitude_delta" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepare(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Desde datos limpios: marco de Stuff+ con pitch_id/pitch_family (altitude_delta) más rasgos de tunneling."""
    _, d = _altitude_delta_run().prepare(df_clean)
    return add_tunnel_features(d)


def load_frame(fast: bool = False) -> pd.DataFrame:
    """Marco preparado en caché (artifacts/tuning/frame_pitching.parquet, local y fuera de git) o, si no, desde crudos."""
    for base in (config.repo_root(), config.main_checkout_root()):
        path = None if base is None else Path(base) / "artifacts" / "tuning" / "frame_pitching.parquet"
        if path is not None and path.exists():
            d = pd.read_parquet(path, columns=FRAME_COLUMNS)
            d = add_tunnel_features(d)
            break
    else:
        from stuffplus.io import load_raw

        d = prepare(schema.clean(load_raw()))
    if fast:
        ids = d["pitcher_anon_id"].astype(str)
        keep = pd.util.hash_array(ids.unique().astype(object)) % 100 < 15
        d = d[ids.isin(ids.unique()[keep])]
    return d.reset_index(drop=True)


def altitude_check(d: pd.DataFrame, n_boot: int, min_n: int) -> pd.DataFrame:
    """Extreme - No dentro del mismo pitch_key; por familia de pitch y combinado."""
    nonref = d[~d["tunnel_is_ref"] & d["tunnel_dec_sep_in"].notna()].copy()
    nonref["todos"] = "todos"
    cols = [c for c in ALT_METRICS + ARSENAL_METRICS if c in nonref]
    parts = []
    for by in ("todos", "pitch_family"):
        r = within_pitcher_observed(nonref, cols, by=by, min_n=min_n, n_boot=n_boot)
        parts.append(r.rename(columns={by: "group"}))
    out = pd.concat(parts, ignore_index=True)
    no_mean = nonref[nonref["altitude_category"].astype(str) == "No Altitude"][cols].mean()
    out["no_altitude_mean"] = out["metric"].map(no_mean)
    out["rel_change_pct"] = 100 * out["extreme_minus_no"] / out["no_altitude_mean"].abs()
    out["significant"] = (out["lo"] > 0) | (out["hi"] < 0)
    return out.rename(columns={"pitches_compared": "pitch_keys"})


def location_audit(d: pd.DataFrame) -> pd.DataFrame:
    """Los rasgos no deben ser ubicación disfrazada: correlación con la ubicación en el plato (global y dentro de familia)."""
    nonref = d[~d["tunnel_is_ref"] & d["tunnel_dec_sep_in"].notna()]
    sgn = np.where(nonref["PitcherThrows"].astype(str).str.startswith("L"), -1.0, 1.0)
    loc = pd.DataFrame({"PlateLocHeight": nonref["PlateLocHeight"].to_numpy(float),
                        "plate_x_arm": nonref["PlateLocSide"].to_numpy(float) * sgn}, index=nonref.index)
    rows = []
    for f in TUNNEL_FEATURES:
        for lc in loc:
            within = [nonref.loc[g.index, f].corr(loc.loc[g.index, lc]) for _, g in nonref.groupby("pitch_family") if len(g) > 50]
            rows.append({"feature": f, "location": lc, "r_global": nonref[f].corr(loc[lc]),
                         "r_within_family_max_abs": float(np.nanmax(np.abs(within))) if within else np.nan})
    return pd.DataFrame(rows)


def adoption_verdict(metrics: pd.DataFrame, pred: pd.DataFrame, rel: pd.DataFrame) -> pd.DataFrame:
    """Aplica la regla fijada en el docstring. `metrics` trae model in {base, tunnel}; `pred`, `rel` traen r_base/r_tunnel."""
    m = metrics.set_index("model")
    c1 = float(m.loc["tunnel", "skill_lo"]) >= float(m.loc["base", "skill_vs_baseline"])
    rows = [{"criterio": "1. habilidad: IC inferior del tunnel >= habilidad del base",
             "tunnel": float(m.loc["tunnel", "skill_lo"]), "referencia": float(m.loc["base", "skill_vs_baseline"]),
             "umbral": 0.0, "cumple": bool(c1)}]
    for _, r in pred.iterrows():
        rows.append({"criterio": f"2. r primeros {int(r.first_n)} -> resto >= base - {TOL}", "tunnel": float(r.r_tunnel),
                     "referencia": float(r.r_base), "umbral": -TOL, "cumple": bool(r.r_tunnel >= r.r_base - TOL)})
    rows.append({"criterio": f"3. split-half >= base - {TOL}", "tunnel": float(rel["r_tunnel"].iloc[0]),
                 "referencia": float(rel["r_base"].iloc[0]), "umbral": -TOL,
                 "cumple": bool(rel["r_tunnel"].iloc[0] >= rel["r_base"].iloc[0] - TOL)})
    out = pd.DataFrame(rows)
    out["adoptar"] = bool(out["cumple"].all())
    return out


def run(d: pd.DataFrame, fast: bool = False, out_dir: Path | None = None) -> dict:
    rounds = dict(class_rounds=60, contact_rounds=40) if fast else {}
    n_boot = 100 if fast else 300
    folds = list(splits.pitcher_group_kfold(d))
    feats_tun = list(STUFF_FEATURES_INVARIANT) + TUNNEL_FEATURES
    schema.assert_no_target_leak(feats_tun, allow_location=False)
    oof_base = StuffModel(features=list(STUFF_FEATURES_INVARIANT), **rounds).oof(d, folds)["xrv"].to_numpy(float)
    oof_tun = StuffModel(features=feats_tun, **rounds).oof(d, folds)["xrv"].to_numpy(float)
    null = evaluate.oof_predict(d, lambda tr, te: CountBaseline().fit(tr, ["rv_x"]).predict(te, "rv_x"), folds)
    metrics = evaluate.compare({"baseline": null, "base": oof_base, "tunnel": oof_tun}, d["rv_x"],
                               groups=d["pitcher_anon_id"], n_boot=n_boot)
    d = d.assign(xrv_base=oof_base, xrv_tunnel=oof_tun)
    sizes = (25, 50) if fast else SIZES
    rest_min = 40 if fast else 300
    pb = matched_sample_predictiveness(d, "xrv_base", sizes=sizes, rest_min=rest_min)
    pt = matched_sample_predictiveness(d, "xrv_tunnel", sizes=sizes, rest_min=rest_min)
    pred = pd.DataFrame({"first_n": pb["first_n"], "pitcher_seasons": pb["pitcher_seasons"], "r_base": pb["stuff_model"],
                         "r_tunnel": pt["stuff_model"], "r_observed_rv": pb["observed_rv"]})
    min_n = 30 if fast else 150
    sb, st = split_half_reliability(d, "xrv_base", min_n=min_n), split_half_reliability(d, "xrv_tunnel", min_n=min_n)
    rel = pd.DataFrame([{"pairs": sb["pairs"], "r_base": sb["stuff_model"], "r_tunnel": st["stuff_model"],
                         "r_observed_rv": sb["observed_rv"]}])
    verdict = adoption_verdict(metrics, pred, rel)
    alt = altitude_check(d, n_boot=100 if fast else 500, min_n=10 if fast else 30)
    audit = location_audit(d)
    res = {"metrics": metrics, "predictiveness": pred, "reliability": rel, "altitude_check": alt,
           "location_audit": audit, "verdict": verdict, "pitches": len(d), "pitchers": int(d["pitcher_anon_id"].nunique()),
           "fast": fast}
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        metrics.round(5).to_csv(out_dir / "metrics.csv", index=False)
        pred.round(4).to_csv(out_dir / "predictiveness.csv", index=False)
        rel.round(4).to_csv(out_dir / "reliability.csv", index=False)
        alt.round(4).to_csv(out_dir / "altitude_check.csv", index=False)
        audit.round(4).to_csv(out_dir / "location_audit.csv", index=False)
        verdict.round(5).to_csv(out_dir / "verdict.csv", index=False)
        pd.DataFrame([{"pitches": res["pitches"], "pitchers": res["pitchers"], "fast": fast}]).to_csv(out_dir / "run_info.csv", index=False)
        write_readme(out_dir)
    return res


def _f(x, n=3, sign=False):
    return f"{x:+.{n}f}" if sign else f"{x:.{n}f}"


def write_readme(out_dir: Path) -> str:
    """README.md en español; cada número sale de los CSV de `out_dir`."""
    m = pd.read_csv(out_dir / "metrics.csv").set_index("model")
    pred = pd.read_csv(out_dir / "predictiveness.csv")
    rel = pd.read_csv(out_dir / "reliability.csv").iloc[0]
    alt = pd.read_csv(out_dir / "altitude_check.csv")
    aud = pd.read_csv(out_dir / "location_audit.csv")
    ver = pd.read_csv(out_dir / "verdict.csv")
    info = pd.read_csv(out_dir / "run_info.csv").iloc[0]
    adopt = bool(ver["adoptar"].iloc[0])
    L = ["# Tunneling por tiempo (HACK-061)", ""]
    if bool(info["fast"]):
        L += ["> Corrida rápida de depuración con una muestra de pitchers: NO es una decisión.", ""]
    L += [
        "El punto de decisión del bateador se fija en el **tiempo**: 150 ms antes de que la pelota llegue al frente del plato "
        "(17/12 ft), resuelto con el ajuste de aceleración constante de 9 parámetros de cada lanzamiento. En aire delgado la "
        "pelota llega antes, así que esos 150 ms corresponden a otra distancia. La separación se mide contra la recta "
        "principal del mismo pitcher y temporada, en ese punto y en el plato, y el cociente de tunneling es "
        "separación en el plato / separación en la decisión. Son rasgos físicos: nunca usan resultados.", "",
        "Para que no sean ubicación disfrazada, se comparan trayectorias promedio por tipo de pitch y juego (no lanzamientos "
        "sueltos) contra la recta principal construida igual. Ver la auditoría de ubicación abajo.", "",
        f"Datos: {int(info['pitches']):,} lanzamientos de {int(info['pitchers']):,} pitchers.", "",
        "## Regla de adopción (fijada antes de correr)", "",
        "Se adopta solo si se cumplen las tres: (1) el límite inferior del IC 95 % de la habilidad por lanzamiento con "
        f"tunneling es mayor o igual a la habilidad del modelo base; (2) la r de pitcher-temporada de \"primeros N lanzamientos "
        f"al resto\" (N = {', '.join(str(int(n)) for n in pred['first_n'])}) no baja más de {TOL} contra la base; "
        f"(3) la confiabilidad split-half no baja más de {TOL} contra la base.", "",
        "## Antes y después (pliegues por pitcher, objetivo rv_x)", "",
        "| Modelo | RMSE | Habilidad vs null | IC 95 % |", "|---|---|---|---|"]
    names = {"baseline": "Null: media de rv_x por cuenta", "base": "Stuff+ base (rasgos invariantes)",
             "tunnel": "Stuff+ con tunneling por tiempo"}
    for k in ("baseline", "base", "tunnel"):
        r = m.loc[k]
        ci = "" if k == "baseline" else f"{_f(100 * r.skill_lo, 3)} % a {_f(100 * r.skill_hi, 3)} %"
        sk = "" if k == "baseline" else f"{_f(100 * r.skill_vs_baseline, 3)} %"
        L.append(f"| {names[k]} | {_f(r.rmse, 5)} | {sk} | {ci} |")
    L += ["", "| N primeros lanzamientos | Pitcher-temporadas | r base | r con tunneling | Diferencia |", "|---|---|---|---|---|"]
    for _, r in pred.iterrows():
        L.append(f"| {int(r.first_n)} | {int(r.pitcher_seasons):,} | {_f(r.r_base)} | {_f(r.r_tunnel)} | {_f(r.r_tunnel - r.r_base, 3, True)} |")
    L += ["", f"Split-half ({int(rel.pairs):,} pitcher-temporadas): base {_f(rel.r_base)}, con tunneling {_f(rel.r_tunnel)} "
          f"(diferencia {_f(rel.r_tunnel - rel.r_base, 3, True)}).", "",
          "## Veredicto", "", "| Criterio | Con tunneling | Referencia | Cumple |", "|---|---|---|---|"]
    for _, r in ver.iterrows():
        L.append(f"| {r['criterio']} | {_f(r.tunnel, 4)} | {_f(r.referencia, 4)} | {'sí' if r.cumple else 'no'} |")
    L += ["", f"**{'Adoptar: se cumplen los tres criterios.' if adopt else 'No adoptar: al menos un criterio falla.'}** "
          "La adopción real pasa por HACK-057 (congelamiento 2026-10-20 12:00).", "",
          "## Chequeo de altitud (mismo pitch, Extreme menos No Altitude)", "",
          "Diferencia dentro del mismo pitcher x temporada x pitch_key, sin las rectas principales, con IC 95 % por bootstrap de "
          "pitchers. Los renglones `arsenal.py` son el tunneling por distancia ya existente, para comparar.", "",
          "| Métrica | Pitches comparados (pitcher x temporada x tipo) | Extreme menos No | IC 95 % | Cambio relativo | Distinto de 0 |", "|---|---|---|---|---|---|"]
    pooled = alt[alt["group"] == "todos"]
    for _, r in pooled.iterrows():
        d3 = 4 if abs(r.extreme_minus_no) < 0.1 else 3
        L.append(f"| {LABELS.get(r.metric, r.metric)} | {int(r.pitch_keys):,} | {_f(r.extreme_minus_no, d3, True)} | "
                 f"{_f(r.lo, d3, True)} a {_f(r.hi, d3, True)} | {_f(r.rel_change_pct, 1, True)} % | {'sí' if r.significant else 'no'} |")
    fam = alt[(alt["group"] != "todos") & (alt["metric"] == "tunnel_ratio_t") & alt["lo"].notna()]
    if len(fam):
        L += ["", "Cociente de tunneling por familia de pitch:", "", "| Familia | Pitches comparados | Extreme menos No | IC 95 % |", "|---|---|---|---|"]
        for _, r in fam.sort_values("group").iterrows():
            L.append(f"| {r['group']} | {int(r.pitch_keys):,} | {_f(r.extreme_minus_no, 3, True)} | {_f(r.lo, 3, True)} a {_f(r.hi, 3, True)} |")
    top = aud.assign(a=aud.r_global.abs()).sort_values("a", ascending=False).iloc[0]
    L += ["", "## Auditoría de ubicación", "",
          "Los rasgos de Stuff+ no pueden codificar hacia dónde se apuntó. Correlación de cada rasgo con la altura y el lado (en "
          "marco del brazo) en el plato, en lanzamientos que no son la recta principal:", "",
          "| Rasgo | r con altura | r con lado | máx. de r absoluta dentro de familia |", "|---|---|---|---|"]
    for f in TUNNEL_FEATURES:
        h = aud[(aud.feature == f) & (aud.location == "PlateLocHeight")].iloc[0]
        s = aud[(aud.feature == f) & (aud.location == "plate_x_arm")].iloc[0]
        L.append(f"| {f} | {_f(h.r_global, 2, True)} | {_f(s.r_global, 2, True)} | {_f(max(h.r_within_family_max_abs, s.r_within_family_max_abs), 2)} |")
    L += ["", f"La correlación global más alta es {_f(abs(top.r_global), 2)} ({top.feature} con {top.location}); parte viene de que cada "
          "tipo de pitch se ubica en una zona distinta (el modelo ya conoce la familia del pitch).", "",
          "## Reproducir", "", "```", "python analysis/tunnel/run.py", "```", ""]
    text = "\n".join(L)
    (out_dir / "README.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--out", default=None, help="carpeta de salida (por defecto reports/tunnel)")
    args = ap.parse_args()
    out = Path(args.out) if args.out else REPORTS
    res = run(load_frame(fast=args.fast), fast=args.fast, out_dir=out)
    print(res["metrics"][["model", "rmse", "skill_vs_baseline", "skill_lo", "skill_hi"]].round(5).to_string(index=False))
    print(res["predictiveness"].round(3).to_string(index=False))
    print(res["reliability"].round(3).to_string(index=False))
    print(res["altitude_check"][res["altitude_check"]["group"] == "todos"].round(4).to_string(index=False))
    print(res["verdict"].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
