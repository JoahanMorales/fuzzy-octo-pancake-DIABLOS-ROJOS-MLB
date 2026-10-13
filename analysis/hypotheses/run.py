"""HACK-009: contrasta H1–H4 con datos de la LMB. Escribe agregados en reports/hypotheses/ (nada por lanzamiento).

Uso: python analysis/hypotheses/run.py [--n-boot 2000] [--rebuild]
Pesado (build de targets ≈ 2 min, mapa de parques); la tabla preparada se cachea en artifacts/ (git-ignored).
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from stuffplus import hypotheses as H
from stuffplus import splits, targets
from stuffplus.config import ARTIFACTS_DIR, SEED
from stuffplus.features.identity import assign_pitch_id
from stuffplus.io import load_raw
from stuffplus.physics import aero, parks
from stuffplus.schema import clean

warnings.filterwarnings("ignore")
OUT = Path("reports/hypotheses")
RED, BLACK = "#B71C1C", "#111111"
NO, MED, EXT = H.NO_ALT, H.MED_ALT, H.EXT_ALT


def prepare(rebuild: bool = False) -> tuple[pd.DataFrame, dict]:
    cache = ARTIFACTS_DIR / "hypotheses_prepared.parquet"
    meta_path = ARTIFACTS_DIR / "hypotheses_meta.csv"
    if cache.exists() and meta_path.exists() and not rebuild:
        return pd.read_parquet(cache), pd.read_csv(meta_path).iloc[0].to_dict()
    raw = clean(load_raw())
    df, _, _ = targets.build(raw)  # sobre el orden original completo (la secuencia de PA no se rompe)
    df = assign_pitch_id(df)
    df = df[df["pitch_id"] >= 0].copy()
    rho_g = H.game_rho(df)
    maps = parks.load_maps(raw)
    park_rho_g, dropped = H.park_rho(rho_g, maps["park_map"])
    df["rho_game"] = df["game_anon_id"].map(rho_g)
    df["park_rho"] = df["game_anon_id"].map(park_rho_g)
    df = H.add_batted_ball_metrics(H.add_movement_metrics(df))
    df["spin_eff"] = aero.decompose(df, rho=df["rho_game"])["spin_eff"]
    df["_ps"] = df["pitcher_anon_id"].astype(str) + "_" + df["year"].astype(str)
    pm = maps["park_map"].drop_duplicates("game_anon_id").set_index("game_anon_id")["franchise"]
    df["park"] = df["game_anon_id"].map(pm)
    meta = {"games": int(rho_g.size), "games_without_park": int(dropped), "rows": int(len(df))}
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    pd.DataFrame([meta]).to_csv(meta_path, index=False)
    return df, meta


def row(h: str, metric: str, fam: str, contrast: str, direction: int, d: H.Estimate,
        s: H.Estimate | None = None, with_verdict: bool = True) -> dict:
    return dict(hypothesis=h, metric=metric, family=fam, contrast=contrast, direction=direction,
                delta=d.delta, lo=d.lo, hi=d.hi, slope_per_0p1_rho=getattr(s, "delta", np.nan),
                slope_lo=getattr(s, "lo", np.nan), slope_hi=getattr(s, "hi", np.nan), n_keys=d.n_keys,
                n_pitchers=d.n_pitchers, verdict=H.verdict(d, direction, s) if with_verdict else "info")


# ------------------------------------------------------------------ H1
def h1(df: pd.DataFrame, n_boot: int) -> list[dict]:
    rows = []
    specs = [("abs_ivb", -1), ("abs_hb", -1), ("total_break", -1), ("SpeedDrop", -1), ("InducedVertBreak", 0)]
    for fam in ["Four-Seam", "Sinker", "Cutter", "Slider", "Curveball", "Changeup", "Splitter"]:
        for metric, direction in specs:
            for b, label in ((EXT, "Extreme-No"), (MED, "Medium-No")):
                d = H.within_pitcher_delta(df, metric, fam, NO, b, n_boot=n_boot)
                s = H.dose_response(df, metric, "park_rho", fam, n_boot=n_boot) if b == EXT else None
                rows.append(row("H1", metric, fam, label, direction, d, s, with_verdict=direction != 0 and b == EXT))
    return rows


# ------------------------------------------------------------------ H2
def h2(df: pd.DataFrame, n_boot: int) -> list[dict]:
    rows = []
    for metric, direction in (("t_whiff", -1), ("t_chase", -1), ("rv_x", +1)):
        d = H.paired_did(df, metric, H.OFFSPEED, H.BREAKING, NO, EXT, min_n=15, n_boot=n_boot)
        rows.append(row("H2", metric, "CH+SPL minus SL+CB", "DiD Extreme-No", direction, d))
        for name, fams in (("CH+SPL", H.OFFSPEED), ("SL+CB", H.BREAKING)):
            sub = df[df["pitch_family"].isin(fams)]
            dd = H.within_pitcher_delta(sub, metric, None, NO, EXT, min_n=30, n_boot=n_boot, key_col="_ps")
            ss = H.dose_response(sub, metric, "park_rho", None, min_n=30, n_boot=n_boot, key_col="_ps")
            rows.append(row("H2", metric, name, "Extreme-No (info)", direction, dd, ss, with_verdict=False))
    # el mecanismo propuesto: el changeup pierde fade (|HB|) y quiebre
    for metric in ("abs_hb", "total_break"):
        d = H.within_pitcher_delta(df, metric, "Changeup", NO, EXT, n_boot=n_boot)
        rows.append(row("H2", metric, "Changeup", "Extreme-No (mecanismo, info)", -1, d,
                        H.dose_response(df, metric, "park_rho", "Changeup", n_boot=n_boot), with_verdict=False))
    return rows


# ------------------------------------------------------------------ H3
def h3(df: pd.DataFrame, n_boot: int) -> list[dict]:
    rows = []
    bip = df["hit_type"].notna() & df["hit_type"].ne("Bunt") & df["PitchCall"].astype(str).eq("InPlay")
    d = df.assign(rv_bip=df["rv_x"].where(bip), rv_fb=df["rv_x"].where(df["hit_type"].eq("FlyBall")),
                  rv_gb=df["rv_x"].where(df["hit_type"].eq("GroundBall")))
    for metric, direction in (("hr_fb", +1), ("fb_distance", +1), ("rv_fb", +1), ("rv_gb", +1), ("rv_bip", +1)):
        e = H.within_pitcher_delta(d, metric, None, NO, EXT, min_n=15, n_boot=n_boot, key_col="_ps")
        s = H.dose_response(d, metric, "park_rho", None, min_n=15, n_boot=n_boot, key_col="_ps")
        primary = metric in ("hr_fb", "fb_distance")
        rows.append(row("H3", metric, "todos", "Extreme-No (pitcher-temporada)", direction, e, s, with_verdict=primary))
    t = d[d["rv_fb"].notna() | d["rv_gb"].notna()].copy()
    t["pitch_family"] = np.where(t["rv_fb"].notna(), "FlyBall", "GroundBall")
    t["rv_x_bb"] = t["rv_x"]
    did = H.paired_did(t, "rv_x_bb", ("FlyBall",), ("GroundBall",), NO, EXT, min_n=15, n_boot=n_boot)
    rows.append(row("H3", "rv_x fly ball − rv_x rodado", "FB − GB", "DiD Extreme-No (pitcher-temporada)", +1, did))
    # moderación: GB% a nivel del mar (fijado antes del "tratamiento") -> Δ rv_x por bola en juego
    sea = d[d["altitude_category"].eq(NO) & d["gb_flag"].notna()].groupby("_ps")["gb_flag"].agg(["mean", "size"])
    sea = sea[sea["size"] >= 30]["mean"].rename("gb_sea")
    m = d.merge(sea, left_on="_ps", right_index=True, how="inner")
    est = H.moderated_delta(m, "rv_bip", "gb_sea", NO, EXT, min_n=30, n_boot=n_boot, per=0.1)
    rows.append(row("H3", "Δ rv_x por bola en juego vs GB% (por +10 pp)", "todos", "pendiente (Extreme-No)", -1, est))
    est_hr = H.moderated_delta(m, "hr_fb", "gb_sea", NO, EXT, min_n=15, n_boot=n_boot, per=0.1)
    rows.append(row("H3", "Δ HR/FB vs GB% (por +10 pp)", "todos", "pendiente (Extreme-No)", -1, est_hr, with_verdict=False))
    return rows


# ------------------------------------------------------------------ H4
def _wauc(inv: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    pos = np.bincount(inv, weights=w * y)
    neg = np.bincount(inv, weights=w * (1 - y))
    below = np.cumsum(neg) - neg
    return float((pos * (below + 0.5 * neg)).sum() / (pos.sum() * neg.sum()))


def h4(df: pd.DataFrame, n_boot: int) -> tuple[list[dict], pd.DataFrame]:
    from sklearn.ensemble import HistGradientBoostingClassifier

    s = df[df["t_whiff"].notna() & df["spin_eff"].notna()].reset_index(drop=True)
    s["fam_code"] = s["pitch_family"].astype("category").cat.codes
    y = s["t_whiff"].to_numpy(float)
    folds = splits.pitcher_folds(s).to_numpy()
    base = ["RelSpeed", "fam_code"]
    sets = {"spin": base + ["SpinRate"], "movement": base + ["InducedVertBreak", "hb_arm", "spin_eff"]}
    pred = {}
    for name, cols in sets.items():
        p = np.zeros(len(s))
        for k in np.unique(folds):
            tr, te = folds != k, folds == k
            m = HistGradientBoostingClassifier(max_iter=150, max_depth=4, learning_rate=0.08, random_state=SEED)
            m.fit(s.loc[tr, cols], y[tr])
            p[te] = m.predict_proba(s.loc[te, cols])[:, 1]
        pred[name] = p
    pit, pit_idx = np.unique(s["pitcher_anon_id"].to_numpy(), return_inverse=True)
    rng = np.random.default_rng(SEED)
    counts = rng.multinomial(len(pit), np.full(len(pit), 1 / len(pit)), size=n_boot).astype(float)
    env = s["altitude_category"].astype(str).to_numpy()
    stats, table = {}, []
    for e in (NO, MED, EXT):
        msk = env == e
        invs = {k: np.unique(pred[k][msk], return_inverse=True)[1] for k in pred}
        pt = {k: _wauc(invs[k], y[msk], np.ones(msk.sum())) for k in pred}
        boots = {k: np.array([_wauc(invs[k], y[msk], c[pit_idx[msk]]) for c in counts]) for k in pred}
        stats[e] = (pt, boots)
        table.append(dict(env=e, auc_spin=pt["spin"], auc_movement=pt["movement"], gain=pt["movement"] - pt["spin"],
                          n_swings=int(msk.sum())))
    gain = lambda e: (stats[e][0]["movement"] - stats[e][0]["spin"], stats[e][1]["movement"] - stats[e][1]["spin"])
    g_no, b_no = gain(NO)
    g_ext, b_ext = gain(EXT)
    did = g_ext - g_no
    lo, hi = H._ci(b_ext - b_no)
    est = H.Estimate(did, lo, hi, int(len(s)), len(pit))
    rows = [row("H4", "DiD ΔAUC(movimiento+spin_eff − SpinRate) Extreme-No", "todas (whiff|swing)", "OOF por pitcher",
                +1, est)]
    # R² de IVB explicado por SpinRate (+RelSpeed) en cuatro costuras, por ambiente
    ff = df[df["pitch_family"].eq("Four-Seam") & df["SpinRate"].notna()]
    r2 = {}
    for e in (NO, EXT):
        g = ff[ff["altitude_category"].astype(str).eq(e)]
        r2[e] = _r2_boot(g, n_boot)
    lo2, hi2 = H._ci(r2[EXT][1] - r2[NO][1])
    est2 = H.Estimate(r2[EXT][0] - r2[NO][0], lo2, hi2, int(len(ff)), ff["pitcher_anon_id"].nunique())
    rows.append(row("H4", "R² (IVB ~ SpinRate+RelSpeed) Extreme-No", "Four-Seam", "R² por ambiente", -1, est2))
    return rows, pd.DataFrame(table)


def _r2_boot(g: pd.DataFrame, n_boot: int) -> tuple[float, np.ndarray]:
    x = np.column_stack([np.ones(len(g)), g["SpinRate"].to_numpy(float), g["RelSpeed"].to_numpy(float)])
    yv = g["InducedVertBreak"].to_numpy(float)
    pit, idx = np.unique(g["pitcher_anon_id"].to_numpy(), return_inverse=True)

    def r2(w):
        sw = np.sqrt(w)
        beta, *_ = np.linalg.lstsq(x * sw[:, None], yv * sw, rcond=None)
        res = ((yv - x @ beta) ** 2 * w).sum()
        ybar = (yv * w).sum() / w.sum()
        return 1 - res / ((yv - ybar) ** 2 * w).sum()

    rng = np.random.default_rng(SEED)
    counts = rng.multinomial(len(pit), np.full(len(pit), 1 / len(pit)), size=min(n_boot, 400)).astype(float)
    return r2(np.ones(len(g))), np.array([r2(c[idx]) for c in counts])


# ------------------------------------------------------------------ figuras y resumen
def forest(res: pd.DataFrame, labels: list[str], title: str, fname: str, xlabel: str, shared: bool = True) -> None:
    """Δ con IC 95 %. ``shared=False`` da a cada fila su propio eje (métricas con escalas distintas)."""
    n = len(res)
    if shared:
        fig, ax = plt.subplots(figsize=(7.5, 0.45 * n + 1.5))
        y = np.arange(n)[::-1]
        ax.errorbar(res["delta"], y, xerr=[res["delta"] - res["lo"], res["hi"] - res["delta"]], fmt="o", color=RED,
                    ecolor=BLACK, capsize=3)
        ax.axvline(0, color="k", lw=0.7)
        ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8); ax.set_xlabel(xlabel)
    else:
        fig, axes = plt.subplots(n, 1, figsize=(7.5, 0.62 * n + 1.2))
        for ax, (_, r), lab in zip(np.atleast_1d(axes), res.iterrows(), labels):
            ax.errorbar([r["delta"]], [0], xerr=[[r["delta"] - r["lo"]], [r["hi"] - r["delta"]]], fmt="o", color=RED,
                        ecolor=BLACK, capsize=3)
            ax.axvline(0, color="k", lw=0.7)
            ax.set_yticks([0]); ax.set_yticklabels([lab], fontsize=7); ax.tick_params(axis="x", labelsize=7)
        np.atleast_1d(axes)[-1].set_xlabel(xlabel)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / fname, dpi=130); plt.close(fig)


def park_dose_figure(df: pd.DataFrame) -> None:
    """Pendiente agregada: movimiento de la recta (total_break), centrado por lanzamiento, contra la ρ̂ de cada parque."""
    ff = df[df["pitch_family"].eq("Four-Seam")].dropna(subset=["park_rho", "total_break"]).copy()
    ff["tb_c"] = ff["total_break"] - ff.groupby("pitch_key")["total_break"].transform("mean")
    p = ff.groupby("park").agg(rho=("park_rho", "first"), tb=("tb_c", "mean"), n=("tb_c", "size"))
    p = p[p["n"] >= 200]
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.scatter(p["rho"], p["tb"], s=p["n"] / 60, color=RED, alpha=0.7)
    b = np.polyfit(p["rho"], p["tb"], 1, w=np.sqrt(p["n"]))
    xs = np.linspace(p["rho"].min(), p["rho"].max(), 20)
    ax.plot(xs, np.polyval(b, xs), color=BLACK, lw=1)
    ax.set_xlabel("ρ̂ del parque (1 = nivel del mar)"); ax.set_ylabel("quiebre total, centrado por lanzamiento (in)")
    ax.set_title("H1 · Recta: quiebre vs densidad por parque")
    fig.tight_layout(); fig.savefig(OUT / "h1_dose_park.png", dpi=130); plt.close(fig)
    p.round(4).to_csv(OUT / "h1_dose_park.csv")


def write_summary(res: pd.DataFrame, auc: pd.DataFrame, meta: dict) -> None:
    def fmt(r) -> str:
        sl = "–" if not np.isfinite(r.slope_per_0p1_rho) else f"{r.slope_per_0p1_rho:+.3g} [{r.slope_lo:+.3g}, {r.slope_hi:+.3g}]"
        return (f"| {r.metric} | {r.family} | {r.contrast} | {r.delta:+.3g} [{r.lo:+.3g}, {r.hi:+.3g}] | {sl} | "
                f"{r.n_pitchers} / {r.n_keys} | {r.verdict} |")

    hdr = "| Métrica | Familia | Contraste | Δ [IC 95 %] | Pendiente por +0.1 ρ̂ [IC] | Pitchers / claves | Veredicto |\n|---|---|---|---|---|---|---|"
    lines = ["# Hipótesis H1–H4 con evidencia LMB (HACK-009)", "",
             "Diseño: comparación intra-lanzamiento (`pitch_key` de `pitch_id`, no `AutoPitchType`), IC 95 % bootstrap por **pitcher**, "
             "dosis-respuesta contra la ρ̂ del **parque** (mediana de sus juegos, misma escala que HACK-004). "
             "Regla de veredicto fijada de antemano (`stuffplus.hypotheses.verdict`): *Supported* = Δ e pendiente excluyen 0 en la "
             "dirección predicha; *Partially* = solo uno; *Rejected* = ninguno. Las filas «info» no entran al veredicto.",
             f"Juegos: {meta['games']}; sin parque identificado: {meta['games_without_park']}; lanzamientos con `pitch_id`: {meta['rows']}.", ""]
    titles = {
        "H1": "H1 · Pérdida de movimiento (magnitud) y de caída de velocidad en Extreme vs sin altitud",
        "H2": "H2 · Los lanzamientos de diferencial de velocidad (CH/SPL) se degradan más que los rompientes (SL/CB)",
        "H3": "H3 · Los rodados protegen: Δ HR/FB, distancia y xRV; moderación por GB% a nivel del mar",
        "H4": "H4 · El giro solo explica peor la efectividad en altura que movimiento + eficiencia de giro",
    }
    reading = {
        "H1": "Todas las familias pierden quiebre y caída de velocidad, con pendiente consistente contra la ρ̂ del parque (curva dosis-respuesta, `h1_dose_park.png`). "
              "Medido en magnitud: la curva *pierde* quiebre aunque su IVB (con signo) suba, porque cae menos. Coincide con HACK-004.",
        "H2": "No hay evidencia de que CH/SPL se degraden más que SL/CB: los IC de la diferencia de diferencias incluyen 0 (whiff, chase y xRV). "
              "El mecanismo sí está: el changeup pierde fade y quiebre total, pero los rompientes también pierden. Con tan pocos splitters, esta hipótesis tiene poca potencia para CH/SPL por separado.",
        "H3": "Las bolas al aire sí se vuelven más peligrosas en altura (HR/FB, distancia, xRV) y más que los rodados. "
              "Pero no hay evidencia de que los pitchers de más rodados *se protejan* más: la pendiente de Δ xRV contra GB% a nivel del mar incluye 0.",
        "H4": "Contraria a lo predicho: el movimiento aporta *menos* sobre SpinRate en altura (la ganancia de AUC baja) y SpinRate explica *más* del IVB entre pitchers en Extreme. "
              "Ver advertencias sobre SpinRate y spin_eff antes de interpretar.",
    }
    for h in ("H1", "H2", "H3", "H4"):
        sub = res[res["hypothesis"] == h]
        ver = H.overall_verdict(sub.loc[sub["verdict"] != "info", "verdict"])
        lines += [f"## {titles[h]}", "", f"**Veredicto global: {ver}**", "", reading[h], "", hdr] + [fmt(r) for r in sub.itertuples()] + [""]
    lines += ["### H4 · AUC fuera de muestra (whiff | swing, validación cruzada por pitcher)", "",
              "| env | AUC SpinRate | AUC movimiento+spin_eff | ganancia | swings |\n|---|---|---|---|---|\n"
              + "\n".join(f"| {r.env} | {r.auc_spin:.4f} | {r.auc_movement:.4f} | {r.gain:+.4f} | {r.n_swings} |" for r in auc.itertuples()), "",
              "## Advertencias", "",
              "- La eficiencia de giro usa ρ̂ por juego; queda una brecha de ~15 % entre No y Extreme sin explicar (Cl cae más que Cd, HACK-004): "
              "H4 no debe leerse como evidencia sobre spin_eff en sí.",
              "- `SpinRate` sube ~+17 rpm dentro del mismo lanzamiento en Extreme (medición o efecto real); por eso no entra en `pitch_id` (HACK-029).",
              "- `rv_x` valora las bolas en juego con altitud como rasgo (HACK-030): parte de su diferencia por altitud está en el modelo; "
              "HR/FB y distancia crudos son la evidencia primaria de H3.",
              "- Identidad de CDMX vs Puebla sin verificar (HACK-003); los parques se agrupan por franquicia inferida.",
              "- Los IC propagan solo el muestreo de pitchers, no la incertidumbre de ρ̂ ni de la identidad de lanzamiento."]
    (OUT / "summary.md").write_text("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--only", default="H1,H2,H3,H4")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    df, meta = prepare(a.rebuild)
    print("preparado:", meta, flush=True)
    todo, rows, auc = a.only.split(","), [], pd.DataFrame()
    if "H1" in todo:
        rows += h1(df, a.n_boot); park_dose_figure(df); print("H1 listo", flush=True)
    if "H2" in todo:
        rows += h2(df, a.n_boot); print("H2 listo", flush=True)
    if "H3" in todo:
        rows += h3(df, a.n_boot); print("H3 listo", flush=True)
    if "H4" in todo:
        r4, auc = h4(df, min(a.n_boot, 300)); rows += r4; auc.round(5).to_csv(OUT / "h4_auc.csv", index=False)
        print("H4 listo", flush=True)
    res = pd.DataFrame(rows)
    res.round(5).to_csv(OUT / "results.csv", index=False)
    for h, fname, xl in (("H1", "h1_break.png", "Δ Extreme − No"), ("H2", "h2_offspeed.png", "Δ / DiD Extreme − No"),
                         ("H3", "h3_groundballs.png", "Δ Extreme − No"), ("H4", "h4_spin.png", "Δ")):
        sub = res[(res["hypothesis"] == h)]
        if h == "H1":
            sub = sub[(sub["metric"] == "total_break") & (sub["contrast"] == "Extreme-No")]
        sub = sub.dropna(subset=["delta", "lo", "hi"])
        if len(sub):
            forest(sub, [f"{r.metric[:44]} · {r.family}" for r in sub.itertuples()], f"{h} · efecto de altitud (Extreme − No)", fname, xl,
                   shared=(h == "H1"))
    if a.only == "H1,H2,H3,H4":
        write_summary(res, auc, meta)


if __name__ == "__main__":
    main()
