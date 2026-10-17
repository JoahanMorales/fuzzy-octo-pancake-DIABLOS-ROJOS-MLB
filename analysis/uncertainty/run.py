"""python -m analysis.uncertainty.run [--fast]  (HACK-055, ~15 min).

1. Shift: how different is Extreme altitude for the model's inputs (air density excluded)? Density-ratio classifier
   AUC and effective sample size of the importance weights.
2. Weighted CV: from No + Medium altitude games only, estimate the Extreme-altitude skill (importance-weighted
   pitcher k-fold) and compare with the real park holdout (train No + Medium, predict Extreme).
3. Conformal intervals for a pitcher's run value (first half of a season → second half), 90 % target coverage on
   held-out pitchers, plain and density-ratio weighted, overall and for pitchers who pitch mostly at altitude.
4. Conformal intervals for each pitcher's observed ΔStuff+ in thin air (HACK-018 model delta → observed delta).
Writes reports/uncertainty/ (aggregates) and its README from the CSVs.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from stuffplus import config, splits
from stuffplus import uncertainty as un
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.baseline import CountBaseline
from stuffplus.models.location import LocationModel
from stuffplus.models.stuff import StuffModel

OUT = config.REPORTS_DIR / "uncertainty"
EXT = "Extreme Altitude"
ALPHA = 0.1
SEED = 2240


def _main_path(*parts):
    main = config.main_checkout_root()
    return (main if main else config.repo_root()).joinpath(*parts)


def load_frame() -> pd.DataFrame:
    cache = _main_path("artifacts", "tuning", "frame_pitching.parquet")
    if cache.exists():
        return pd.read_parquet(cache)
    from analysis.altitude_delta.run import prepare
    from stuffplus.io import load_raw
    from stuffplus.models.pitching import build_features
    from stuffplus.schema import clean

    return build_features(prepare(clean(load_raw()))[1])


def shift_and_weighted_cv(d: pd.DataFrame, rounds: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    tgt = (d.altitude_category.astype(str) == EXT).to_numpy()
    feats = [f for f in STUFF_FEATURES_INVARIANT if f != "rho"]
    w, diag = un.density_ratio(d, feats, tgt, rounds=60 if rounds else 200)
    shift = pd.DataFrame([dict(features="física del lanzamiento (sin ρ)", **diag)])
    src = d[~tgt].reset_index(drop=True)
    ws = w[~tgt]
    tgt_df = d[tgt]
    rows = []
    models = {"Stuff+": lambda: StuffModel(features=list(STUFF_FEATURES_INVARIANT), **rounds),
              "Location+": lambda: LocationModel(**rounds)}
    for name, factory in models.items():
        pred, base = np.full(len(src), np.nan), np.full(len(src), np.nan)
        for tr, te in splits.pitcher_group_kfold(src):
            base[te] = CountBaseline().fit(src.iloc[tr], ["rv_x"]).predict(src.iloc[te], "rv_x")
            pred[te] = factory().fit(src.iloc[tr]).predict_xrv(src.iloc[te])
        y = src.rv_x.to_numpy(float)
        m = factory().fit(src)
        b_t = CountBaseline().fit(src, ["rv_x"]).predict(tgt_df, "rv_x")
        p_t = m.predict_xrv(tgt_df)
        rows.append(dict(model=name, source_cv_skill=un.weighted_skill(y, pred, base),
                         weighted_cv_estimate=un.weighted_skill(y, pred, base, ws),
                         actual_extreme_holdout=un.weighted_skill(tgt_df.rv_x.to_numpy(float), p_t, b_t)))
    return shift, pd.DataFrame(rows)


def pitcher_halves(d: pd.DataFrame, min_pitches: int = 300) -> pd.DataFrame:
    """Per pitcher-season: OOF Pitching+ and Stuff+ in the first half of its games, observed rv_x per 100 pitches in
    the second half, and the share of second-half pitches thrown at Extreme altitude."""
    scores = pd.read_parquet(_main_path("artifacts", "scores", "pitch_scores.parquet"),
                             columns=["PitchUID", "stuff_plus", "pitching_plus"])
    f = d[["PitchUID", "pitcher_anon_id", "year", "game_anon_id", "rv_x", "altitude_category"]].merge(scores, on="PitchUID")
    f["g"] = f.groupby(["pitcher_anon_id", "year"]).game_anon_id.transform(lambda s: pd.factorize(s)[0])
    f["n_g"] = f.groupby(["pitcher_anon_id", "year"]).g.transform("max") + 1
    f["half"] = (f.g >= f.n_g / 2).astype(int)
    key = ["pitcher_anon_id", "year"]
    first = f[f.half == 0].groupby(key).agg(pitching=("pitching_plus", "mean"), stuff=("stuff_plus", "mean"), n1=("rv_x", "size"))
    second = f[f.half == 1].groupby(key).agg(rv100=("rv_x", lambda x: 100 * x.mean()), n2=("rv_x", "size"),
                                             ext_share=("altitude_category", lambda x: (x.astype(str) == EXT).mean()))
    t = first.join(second, how="inner").reset_index()
    return t[(t.n1 + t.n2) >= min_pitches].reset_index(drop=True)


def conformal_pitchers(t: pd.DataFrame, predictor: str) -> dict:
    rng = np.random.default_rng(SEED)
    pitchers = t.pitcher_anon_id.unique()
    cal_ids = set(rng.choice(pitchers, len(pitchers) // 2, replace=False))
    cal, tst = t[t.pitcher_anon_id.isin(cal_ids)], t[~t.pitcher_anon_id.isin(cal_ids)]
    b = np.polyfit(cal[predictor], cal.rv100, 1)
    pred = lambda x: np.polyval(b, x)
    r_cal = cal.rv100 - pred(cal[predictor])
    hw = un.split_conformal(r_cal, ALPHA)
    alt = tst.ext_share >= 0.5
    # weighted: pitcher-level density ratio for "mostly at altitude", from the calibration set's own features
    is_alt = (cal.ext_share >= 0.5).to_numpy()
    p_alt = is_alt.mean()
    w_cal = np.where(is_alt, (1 - p_alt) / max(p_alt, 1e-6), 1.0)
    hw_w = un.split_conformal(r_cal, ALPHA, w_cal=w_cal, w_test=np.full(int(alt.sum()), w_cal.max()))
    return dict(predictor=predictor, pitcher_seasons_cal=len(cal), pitcher_seasons_test=len(tst),
                slope=float(b[0]), half_width_rv100=hw, coverage_all=un.coverage(tst.rv100, pred(tst[predictor]), hw),
                coverage_altitude=un.coverage(tst.rv100[alt], pred(tst[predictor][alt]), hw), n_altitude=int(alt.sum()),
                half_width_altitude_weighted=float(np.median(hw_w)) if len(hw_w) else np.nan,
                coverage_altitude_weighted=un.coverage(tst.rv100[alt], pred(tst[predictor][alt]), hw_w) if len(hw_w) else np.nan)


def conformal_delta() -> dict:
    p = pd.read_csv(config.REPORTS_DIR / "pitcher_sensitivity" / "pitchers.csv")
    p = p.dropna(subset=["delta_stuff", "observed_delta"])
    rng = np.random.default_rng(SEED)
    ids = p.pitcher_anon_id.unique()
    cal_ids = set(rng.choice(ids, len(ids) // 2, replace=False))
    cal, tst = p[p.pitcher_anon_id.isin(cal_ids)], p[~p.pitcher_anon_id.isin(cal_ids)]
    b = np.polyfit(cal.delta_stuff, cal.observed_delta, 1)
    hw = un.split_conformal(cal.observed_delta - np.polyval(b, cal.delta_stuff), ALPHA)
    return dict(pitcher_seasons_cal=len(cal), pitcher_seasons_test=len(tst), slope=float(b[0]), intercept=float(b[1]),
                half_width_points=hw, coverage=un.coverage(tst.observed_delta, np.polyval(b, tst.delta_stuff), hw),
                corr_model_observed=float(np.corrcoef(p.delta_stuff, p.observed_delta)[0, 1]))


def readme(shift, wcv, conf, delta) -> str:
    s = shift.iloc[0]
    L = ["# Incertidumbre bajo cambio de entorno (HACK-055)", "",
         "Generado por `python -m analysis.uncertainty.run` desde los CSV de esta carpeta; ninguna cifra se escribió a mano.", "",
         "## ¿Qué tan distinta es la altitud extrema para el modelo? (`shift.csv`)", "",
         f"Un clasificador que intenta distinguir lanzamientos de altitud extrema por su física (sin la densidad del aire) "
         f"logra AUC {s.auc:.3f} (0.5 = indistinguibles). El tamaño efectivo de muestra de los pesos de importancia es "
         f"{100 * s.ess_share:.0f} % de los {int(s.n_source):,} lanzamientos de origen: hay solapamiento suficiente para "
         "ponderar (Shimodaira 2000).", "",
         "## Validación ponderada contra el holdout real (`weighted_cv.csv`)", "",
         "Solo con juegos sin altitud y de altitud media: la habilidad sobre el modelo nulo en validación por pitcher, la "
         "misma ponderada para parecerse a la altitud extrema, y la habilidad real al predecir la altitud extrema.", "",
         "| Modelo | Validación de origen | Estimación ponderada | Holdout real en altitud extrema |", "|---|---|---|---|"]
    for _, r in wcv.iterrows():
        L.append(f"| {r.model} | {100 * r.source_cv_skill:+.2f} % | {100 * r.weighted_cv_estimate:+.2f} % | "
                 f"{100 * r.actual_extreme_holdout:+.2f} % |")
    L += ["", "## Intervalos conformales para un pitcher (`conformal_pitchers.csv`)", "",
          "Con la primera mitad de los juegos de una temporada se predice el valor de carreras por cada 100 lanzamientos en "
          "la segunda mitad. Intervalos al 90 % (Angelopoulos y Bates 2021), calibrados con la mitad de los pitchers y "
          "evaluados en la otra mitad. La versión ponderada (Tibshirani et al. 2019) sube el peso de los pitchers que "
          "lanzan sobre todo en altura.", "",
          "| Predictor | ± carreras / 100 lanz. | Cobertura (todos) | Cobertura (sobre todo en altura) | Ponderado: ± | Ponderado: cobertura |",
          "|---|---|---|---|---|---|"]
    for _, r in conf.iterrows():
        L.append(f"| {r.predictor} | {r.half_width_rv100:.2f} | {100 * r.coverage_all:.1f} % | "
                 f"{100 * r.coverage_altitude:.1f} % (n = {int(r.n_altitude)}) | {r.half_width_altitude_weighted:.2f} | "
                 f"{100 * r.coverage_altitude_weighted:.1f} % |")
    dl = delta.iloc[0]
    L += ["", "## Intervalo para el ΔStuff+ en altura de cada pitcher (`conformal_delta.csv`)", "",
          f"El ΔStuff+ del modelo y el observado (mismos lanzamientos en altitud extrema contra sin altitud, HACK-018) "
          f"correlacionan {dl.corr_model_observed:.2f}. Para predecir el observado de un pitcher nuevo, el intervalo al 90 % "
          f"mide ±{dl.half_width_points:.1f} puntos (cobertura en pitchers de prueba {100 * dl.coverage:.1f} %). El delta "
          "observado de un solo pitcher es ruidoso: el modelo da la expectativa y este intervalo dice cuánto puede "
          "desviarse un caso individual.", "",
          "## Límites",
          "- Los pesos de importancia usan la física del lanzamiento; la identidad del parque es inferida (HACK-003).",
          "- La versión ponderada a nivel pitcher usa un solo indicador (lanza sobre todo en altura).", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    rounds = dict(class_rounds=15, contact_rounds=10) if args.fast else {}
    d = load_frame().reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    shift, wcv = shift_and_weighted_cv(d, rounds)
    shift.round(4).to_csv(OUT / "shift.csv", index=False)
    wcv.round(6).to_csv(OUT / "weighted_cv.csv", index=False)
    halves = pitcher_halves(d)
    conf = pd.DataFrame([conformal_pitchers(halves, "pitching"), conformal_pitchers(halves, "stuff")])
    conf.round(4).to_csv(OUT / "conformal_pitchers.csv", index=False)
    delta = pd.DataFrame([conformal_delta()])
    delta.round(4).to_csv(OUT / "conformal_delta.csv", index=False)
    (OUT / "README.md").write_text(readme(shift, wcv, conf, delta), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
