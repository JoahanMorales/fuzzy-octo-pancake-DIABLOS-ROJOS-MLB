"""HACK-033: laboratorio de diseño. Ganancia de Stuff+ de cada ajuste en el aire del Harp Helú frente al nivel del mar.

    python reports/design_lab/run.py          # datos reales, ~15-25 min (entrena el modelo de HACK-015 y puntúa ~10 M de filas)
    python reports/design_lab/run.py --fast   # ajustes rápidos para depurar

Escribe agregados en reports/design_lab/ (nada por lanzamiento; los pitchers van anonimizados):
  tweak_summary.csv           por ajuste: ganancia de arsenal en el Harp Helú y a nivel del mar, diferencia (valor extra en CDMX), IC por pitcher
  tweak_gains_by_family.csv   por ajuste × familia: ganancia del lanzamiento y del arsenal, % de pitcher-temporadas donde es admisible
  new_pitch_summary.csv       por lanzamiento nuevo (splitter, sinker, sweeper): admisibilidad y ganancia de arsenal con uso supuesto del 10 %
  development_plan_top3.csv   top 3 ajustes por pitcher-temporada (≥ 300 lanzamientos, admisibles y sobre el piso de ruido)
  forest_tweaks.png, README.md
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

from stuffplus import config, design_lab as D, profile, schema  # noqa: E402
from stuffplus.config import SEED  # noqa: E402
from stuffplus.physics.constants import RHO_HARP_HELU  # noqa: E402

OUT = config.REPORTS_DIR / "design_lab"
MIN_PITCHES = 300  # pitcher-temporadas que entran al plan (nota de joahan-1 en HACK-018)
MIN_FAMILY = 100  # lanzamientos de una familia en la temporada para ajustarla
SAMPLE_PER_PS = 300
NEW_SHAPES = {"splitter": ("Splitter", "splitter"), "sinker": ("Sinker", None), "sweeper": ("Slider", "sweeper")}
RED, BLACK = "#D71920", "#111111"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / name.split("__")[0] / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(fast: bool):
    from stuffplus.io import load_raw

    alt = _load("altitude_delta__run")
    ideal = _load("ideal_profile__run")
    shape_model, d = alt.prepare(schema.clean(load_raw()))
    model, scaler = ideal.fit(d, shape_model, fast)
    return d, model, scaler


def pitcher_info(sea: pd.DataFrame) -> pd.DataFrame:
    """Rasgos de salida y de la recta principal por pitcher-temporada (nivel del mar)."""
    fb = sea[sea["pitch_family"].astype(str).isin(D.FASTBALL_FAMILIES)]
    g = fb.groupby(D.PITCHER_SEASON, observed=True)
    info = pd.DataFrame({"fb_velo": g["RelSpeed"].mean(), "fb_ivb": g["InducedVertBreak"].mean(), "fb_hb": g["hb_arm"].mean()})
    allg = sea.groupby(D.PITCHER_SEASON, observed=True)
    for c in ("arm_angle", "Extension", "RelHeight", "rel_side_arm", "is_rhp"):
        info[c] = allg[c].mean()
    info["is_rhp"] = info["is_rhp"].round().astype(int)
    info["n"] = allg.size()
    return info.dropna()


def run(d: pd.DataFrame, model, scaler, fast: bool = False) -> dict:
    sea = profile.to_sea_level(model, d)
    sea["shape"] = d["shape"].astype(str)
    info = pitcher_info(sea)
    elig = info[info["n"] >= MIN_PITCHES].index
    key = pd.MultiIndex.from_frame(sea[D.PITCHER_SEASON])
    sea = sea[key.isin(elig)]
    cap = 60 if fast else SAMPLE_PER_PS
    S = sea.sample(frac=1.0, random_state=SEED).groupby(D.PITCHER_SEASON, observed=True).head(cap).reset_index(drop=True)
    slopes = D.slot_movement_slopes(sea)
    axis_sign = D.estimate_axis_sign(sea)

    def score(frame: pd.DataFrame) -> dict:
        return {"hh": profile.stuff_plus_at(model, scaler, frame, RHO_HARP_HELU), "sea": profile.stuff_plus_at(model, scaler, frame, 1.0)}

    base = pd.DataFrame(score(S), index=S.index)
    cents = profile.centroids(sea, min_n=MIN_FAMILY)
    cents = cents.merge(info[["fb_velo", "fb_ivb", "fb_hb"]], left_on=D.PITCHER_SEASON, right_index=True, how="left")
    fams = sorted(cents["pitch_family"].astype(str).unique())

    # --- ajustes sobre lanzamientos existentes
    rows = []
    for tw in D.TWEAKS:
        for fam in fams:
            mask_s = S["pitch_family"].astype(str).eq(fam)
            c_f = cents[cents["pitch_family"].astype(str).eq(fam)].reset_index(drop=True)
            if mask_s.sum() < 50 or len(c_f) < 30:
                continue
            gains = D.tweak_gain(S, mask_s, tw, score, slopes, axis_sign, base=base)
            arsenal = D.usage_weighted_gain(gains, S)
            own = gains[mask_s].join(S[D.PITCHER_SEASON]).groupby(D.PITCHER_SEASON, observed=True)[["hh", "sea", "diff"]].mean()
            c_after = D.apply_tweak(c_f.assign(rho=1.0), pd.Series(True, index=c_f.index), tw, slopes, axis_sign)
            adm = D.admissible(c_after, c_f)
            c_f = c_f.assign(admissible=adm).set_index(D.PITCHER_SEASON)
            j = c_f[["admissible"]].join(arsenal.add_prefix("ars_"), how="inner").join(own.add_prefix("own_"), how="inner")
            j["tweak"], j["label"], j["family"] = tw.key, tw.label, fam
            rows.append(j.reset_index())
    plan = pd.concat(rows, ignore_index=True)
    plan["pitcher_id"] = plan["pitcher_anon_id"].astype(str) + "_" + plan["year"].astype(str)

    # --- lanzamientos nuevos (splitter / sinker / sweeper) con perfil de pitchers comparables
    sc = sea.copy()
    c_shape = (sc.groupby(D.PITCHER_SEASON + ["shape"], observed=True)[profile.PROFILE_FEATURES + D.DIFF_FEATURES + ["is_rhp"]].mean()
               .join(sc.groupby(D.PITCHER_SEASON + ["shape"], observed=True).size().rename("n")).reset_index())
    c_shape = c_shape[c_shape["n"] >= 50].merge(info[["fb_velo"]], left_on=D.PITCHER_SEASON, right_index=True, how="inner")
    c_shape["is_rhp"] = c_shape["is_rhp"].round().astype(int)
    fam_of = sc.groupby("shape")["pitch_family"].agg(lambda s: s.astype(str).mode().iat[0]).to_dict()
    arsenal_mean = S.assign(**{"_hh": base["hh"], "_sea": base["sea"]}).groupby(D.PITCHER_SEASON, observed=True)[["_hh", "_sea"]].mean()
    new_rows, meta = [], []
    for name, (fam_new, shape_new) in NEW_SHAPES.items():
        shapes = [shape_new] if shape_new else [s for s, f in fam_of.items() if f == fam_new]
        has = c_shape[c_shape["shape"].isin(shapes)].set_index(D.PITCHER_SEASON).index
        ref = c_shape[c_shape["shape"].isin(shapes)]
        for ps, p in info.loc[elig].iterrows():
            if ps in has:
                continue
            comp = D.comparable_profile(ref.assign(arm_angle=ref["arm_angle"]), p, pd.Series(True, index=ref.index))
            if comp is None:
                meta.append(dict(pitcher_anon_id=ps[0], year=ps[1], new_pitch=name, admissible=False))
                continue
            r = D.new_pitch_row(p, comp)
            r["ivb_diff_fb"] = r["InducedVertBreak"] - p["fb_ivb"]
            r["hb_diff_fb"] = r["hb_arm"] - p["fb_hb"]
            r["velo_diff_fb"] = r["RelSpeed"] - p["fb_velo"]
            r["pitch_family"], r["pitcher_anon_id"], r["year"], r["new_pitch"] = fam_new, ps[0], ps[1], name
            new_rows.append(r)
    N = pd.DataFrame(new_rows).reset_index(drop=True)
    if len(N):
        num = [c for c in profile.PROFILE_FEATURES + D.DIFF_FEATURES + ["is_rhp", "rho", "year"] if c in N]
        N[num] = N[num].astype(float)
        sc_new = pd.DataFrame(score(N), index=N.index)
        N = N.join(sc_new.add_prefix("s_"))
        N = N.merge(arsenal_mean, left_on=D.PITCHER_SEASON, right_index=True, how="inner")
        N["ars_hh"] = [D.arsenal_delta_with_new_pitch(a, b) for a, b in zip(N["s_hh"], N["_hh"])]
        N["ars_sea"] = [D.arsenal_delta_with_new_pitch(a, b) for a, b in zip(N["s_sea"], N["_sea"])]
        N["ars_diff"] = N["ars_hh"] - N["ars_sea"]
        N["admissible"] = True
    return {"plan": plan, "new": N, "new_meta": pd.DataFrame(meta), "S": S, "slopes": slopes, "axis_sign": axis_sign, "elig": len(elig),
            "n_rows": len(S)}


def tables(res: dict, n_boot: int) -> dict:
    plan, N = res["plan"], res["new"]
    fam_rows, sum_rows = [], []
    for (tw, fam), g in plan.groupby(["tweak", "family"]):
        a = g[g["admissible"]]
        if len(a) < 5:
            fam_rows.append(dict(tweak=tw, family=fam, pitcher_seasons=len(g), admissible_share=float(g["admissible"].mean())))
            continue
        m = {c: D.cluster_mean_ci(a[c], a["pitcher_anon_id"], n_boot=n_boot) for c in ("ars_hh", "ars_sea", "ars_diff", "own_hh")}
        fam_rows.append(dict(tweak=tw, label=g["label"].iloc[0], family=fam, pitcher_seasons=len(g), admissible_share=float(g["admissible"].mean()),
                             pitch_gain_hh=float(a["own_hh"].mean()), pitch_gain_sea=float(a["own_sea"].mean()),
                             arsenal_gain_hh=m["ars_hh"][0], arsenal_hh_lo=m["ars_hh"][1], arsenal_hh_hi=m["ars_hh"][2],
                             arsenal_gain_sea=m["ars_sea"][0], arsenal_diff=m["ars_diff"][0], diff_lo=m["ars_diff"][1], diff_hi=m["ars_diff"][2]))
    for tw, g in plan.groupby("tweak"):
        a = g[g["admissible"]]
        m = {c: D.cluster_mean_ci(a[c], a["pitcher_anon_id"], n_boot=n_boot) for c in ("ars_hh", "ars_sea", "ars_diff")}
        sum_rows.append(dict(tweak=tw, label=g["label"].iloc[0], pitcher_season_family_pairs=len(g), admissible_share=float(g["admissible"].mean()),
                             arsenal_gain_hh=m["ars_hh"][0], hh_lo=m["ars_hh"][1], hh_hi=m["ars_hh"][2], arsenal_gain_sea=m["ars_sea"][0],
                             arsenal_diff=m["ars_diff"][0], diff_lo=m["ars_diff"][1], diff_hi=m["ars_diff"][2],
                             share_above_noise=float((a["ars_hh"] >= D.NOISE_FLOOR).mean())))
    new_rows = []
    meta = res["new_meta"]
    for name in NEW_SHAPES:
        g = N[N["new_pitch"] == name] if len(N) else N
        k = len(meta[meta["new_pitch"] == name]) if len(meta) else 0
        tot = len(g) + k
        if len(g) < 5:
            new_rows.append(dict(new_pitch=name, candidates=tot, admissible_share=len(g) / max(tot, 1)))
            continue
        m = {c: D.cluster_mean_ci(g[c], g["pitcher_anon_id"], n_boot=n_boot) for c in ("ars_hh", "ars_sea", "ars_diff")}
        new_rows.append(dict(new_pitch=name, candidates=tot, admissible_share=len(g) / max(tot, 1), usage_assumed=D.NEW_PITCH_USAGE,
                             arsenal_gain_hh=m["ars_hh"][0], hh_lo=m["ars_hh"][1], hh_hi=m["ars_hh"][2], arsenal_gain_sea=m["ars_sea"][0],
                             arsenal_diff=m["ars_diff"][0], diff_lo=m["ars_diff"][1], diff_hi=m["ars_diff"][2],
                             share_positive=float((g["ars_hh"] > 0).mean())))
    # plan top-3: ajustes existentes + lanzamientos nuevos, por pitcher-temporada
    exist = plan.assign(gain_hh=plan["ars_hh"], gain_sea=plan["ars_sea"], diff=plan["ars_diff"], what=plan["label"] + " · " + plan["family"])
    cols = ["pitcher_id", "what", "gain_hh", "gain_sea", "diff", "admissible"]
    parts = [exist[cols]]
    if len(N):
        nn = N.assign(pitcher_id=N["pitcher_anon_id"].astype(str) + "_" + N["year"].astype(str), what="agregar " + N["new_pitch"],
                      gain_hh=N["ars_hh"], gain_sea=N["ars_sea"], diff=N["ars_diff"])
        parts.append(nn[cols])
    allp = pd.concat(parts, ignore_index=True)
    top = D.rank_top3(allp).rename(columns={"what": "ajuste"})[["pitcher_id", "rank", "ajuste", "gain_hh", "gain_sea", "diff"]]
    return {"by_family": pd.DataFrame(fam_rows), "summary": pd.DataFrame(sum_rows), "new": pd.DataFrame(new_rows), "top3": top}


def write(t: dict, res: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t["summary"].round(4).to_csv(OUT / "tweak_summary.csv", index=False)
    t["by_family"].round(4).to_csv(OUT / "tweak_gains_by_family.csv", index=False)
    t["new"].round(4).to_csv(OUT / "new_pitch_summary.csv", index=False)
    t["top3"].round(3).to_csv(OUT / "development_plan_top3.csv", index=False)
    pd.DataFrame([{"eligible_pitcher_seasons": res["elig"], "sampled_pitches": res["n_rows"], "axis_sign": res["axis_sign"]}]).to_csv(OUT / "run_meta.csv", index=False)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = t["summary"].sort_values("arsenal_gain_hh")
    fig, ax = plt.subplots(figsize=(7.5, 0.55 * len(s) + 1.6))
    y = np.arange(len(s))
    ax.barh(y - 0.18, s["arsenal_gain_hh"], 0.34, color=RED, label="Harp Helú (2,240 m)")
    ax.barh(y + 0.18, s["arsenal_gain_sea"], 0.34, color=BLACK, label="nivel del mar")
    ax.errorbar(s["arsenal_gain_hh"], y - 0.18, xerr=[s["arsenal_gain_hh"] - s["hh_lo"], s["hh_hi"] - s["arsenal_gain_hh"]], fmt="none", ecolor="#999", capsize=3)
    ax.set_yticks(y, s["label"], fontsize=8)
    ax.axvline(0, color="k", lw=0.7)
    ax.set_xlabel("ganancia de Stuff+ del arsenal (puntos), IC 95 % por pitcher en el Harp Helú")
    ax.legend(fontsize=8)
    ax.set_title("¿Qué ajuste gana más en el aire del Harp Helú?", fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / "forest_tweaks.png", dpi=130); plt.close(fig)
    (OUT / "README.md").write_text(readme(t, res), encoding="utf-8")


def _tbl(df: pd.DataFrame, cols: list[str], fmt: str = "{:.3g}") -> str:
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols)
    body = ["| " + " | ".join(("–" if pd.isna(v) else fmt.format(v)) if isinstance(v, (float, np.floating)) else str(v) for v in r) + " |"
            for r in df[cols].itertuples(index=False)]
    return "\n".join([head] + body)


def readme(t: dict, res: dict) -> str:
    s = t["summary"].sort_values("arsenal_gain_hh", ascending=False)
    n = t["new"]
    top = s.iloc[0]
    rp_path = config.REPORTS_DIR / "business_value" / "runs_per_point_direct.csv"
    noise_runs = ""
    if rp_path.exists():
        rp = pd.read_csv(rp_path).query("escala == 'Stuff+' and objetivo == 'rv_x'")
        if len(rp):
            noise_runs = f"; ≈ {D.NOISE_FLOOR * float(rp['carreras_por_punto_lanzamiento'].iloc[0]):.1e} carreras por lanzamiento con `business_value/runs_per_point_direct.csv`"
    most_cdmx = s.sort_values("arsenal_diff", ascending=False).iloc[0]
    lines = [
        "# Laboratorio de diseño de lanzamientos (HACK-033)", "",
        f"Para cada pitcher-temporada con ≥ {MIN_PITCHES} lanzamientos ({res['elig']:,}; {res['n_rows']:,} lanzamientos muestreados, ≤ {SAMPLE_PER_PS} por temporada) se aplica un ajuste *coherente* al "
        "movimiento a nivel del mar y se puntúa con el modelo de HACK-015 (identidad `pitch_family`, traslado físico) en el aire del Harp Helú (`RHO_HARP_HELU`) y a nivel del mar. "
        "La **ganancia de arsenal** es el cambio medio de Stuff+ de todos los lanzamientos del pitcher (el ajuste a una familia puede mover las diferencias contra la recta de las demás). "
        "La **diferencia** = ganancia en el Harp Helú − ganancia a nivel del mar: cuánto más (o menos) vale el ajuste en CDMX.", "",
        "## Qué ajuste gana más en CDMX (`tweak_summary.csv`)", "",
        _tbl(s, ["label", "arsenal_gain_hh", "hh_lo", "hh_hi", "arsenal_gain_sea", "arsenal_diff", "admissible_share", "share_above_noise"]), "",
        f"**Mayor ganancia en el Harp Helú:** {top['label']} ({top['arsenal_gain_hh']:+.3f} puntos de Stuff+ de arsenal [{top['hh_lo']:+.3f}, {top['hh_hi']:+.3f}]). "
        f"**Vale más en CDMX que a nivel del mar:** {most_cdmx['label']} (diferencia {most_cdmx['arsenal_diff']:+.3f} [{most_cdmx['diff_lo']:+.3f}, {most_cdmx['diff_hi']:+.3f}]). "
        f"Piso de ruido: una ganancia < {D.NOISE_FLOOR} puntos no entra al plan (convención{noise_runs}).", "",
        "## Lanzamiento nuevo (`new_pitch_summary.csv`)", "",
        f"Se agrega un splitter, un sinker o un sweeper con el perfil mediano de pitchers *comparables* (misma mano, velocidad de recta ±2.5 mph y ángulo de brazo ±12°; ≥ 8 comparables), "
        f"con la salida del propio pitcher y un uso **supuesto** del {D.NEW_PITCH_USAGE:.0%} tomado proporcionalmente de los demás. Δ de arsenal = uso × (Stuff+ del lanzamiento nuevo − Stuff+ medio del arsenal); puede ser negativo.", "",
        _tbl(n, [c for c in ["new_pitch", "candidates", "admissible_share", "arsenal_gain_hh", "hh_lo", "hh_hi", "arsenal_gain_sea", "arsenal_diff", "share_positive"] if c in n]), "",
        "## Cómo se acota a lo observado", "",
        "- **Casco de datos:** un ajuste es admisible solo si el perfil resultante (centroide pitcher-temporada-familia) cae en la parte densa de los perfiles observados de esa familia (kNN, `profile.knn_in_hull`); "
        "fuera de ahí los árboles son planos y mostrarían ceros falsos. `admissible_share` dice en qué fracción de pitcher-temporadas aplica cada ajuste.",
        f"- **Eje de giro:** rotar el eje ±5° rota el vector (IVB, HB lado del brazo) el mismo ángulo con la magnitud intacta; el sentido ({'+' if res['axis_sign'] > 0 else '−'}) se estimó de los datos.",
        "- **Eficiencia de giro +5 %:** supuesto físico (movimiento × 1.05, `SpinRate` fijo); la eficiencia no es un rasgo del modelo y la brecha de ~15 % entre altitudes (HACK-004) sigue sin explicarse.",
        "- **Slot más bajo (−5°):** `RelHeight` sigue la geometría de `arm_angle` con la salida lateral fija; el movimiento cambia según la pendiente observada entre pitchers con distinto slot, por familia, controlando velocidad y giro (asociación, no causa).",
        "- **Diferencias contra la recta:** un ajuste a la recta mueve las diferencias (velocidad, IVB, HB) de los secundarios del mismo pitcher-temporada.", "",
        "## Plan de desarrollo (`development_plan_top3.csv`)", "",
        f"Top 3 ajustes por pitcher-temporada, solo admisibles y ≥ {D.NOISE_FLOOR} puntos; ids anonimizados y sin filas por lanzamiento.", "",
        "## Límites", "",
        "- La ganancia es una diferencia del modelo (Stuff+ puro, sin ubicación ni conteo), no un efecto causal medido: cambiar un lanzamiento en la vida real mueve más de lo que el modelo ve.",
        "- Escalas transductivas (identidad, densidad, valores de carrera) y modelo entrenado con todos los datos: las ganancias son en muestra del modelo; los IC solo propagan el muestreo de pitchers.",
        "- La identidad de CDMX frente a Puebla sigue sin verificar (HACK-003); el aire del Harp Helú es ρ̂ = `RHO_HARP_HELU`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--readme-only", action="store_true", help="regenera README.md desde los CSV ya escritos (sin reentrenar)")
    args = ap.parse_args()
    if args.readme_only:
        m = pd.read_csv(OUT / "run_meta.csv").iloc[0]
        t = {"summary": pd.read_csv(OUT / "tweak_summary.csv"), "new": pd.read_csv(OUT / "new_pitch_summary.csv")}
        res = {"elig": int(m["eligible_pitcher_seasons"]), "n_rows": int(m["sampled_pitches"]), "axis_sign": float(m["axis_sign"])}
        (OUT / "README.md").write_text(readme(t, res), encoding="utf-8")
        return
    d, model, scaler = build(args.fast)
    res = run(d, model, scaler, fast=args.fast)
    t = tables(res, n_boot=100 if args.fast else 400)
    write(t, res)
    print(t["summary"].round(3).to_string(index=False))
    print(t["new"].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
