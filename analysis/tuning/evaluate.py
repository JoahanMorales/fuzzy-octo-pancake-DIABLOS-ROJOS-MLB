"""Before/after for HACK-028: production boosters vs the settings in reports/tuning/chosen.json.

    python -m analysis.tuning.evaluate [--parts kfold altitude holdouts pitching_kfold]

kfold          Stuff+ and Location+, pitcher 5-fold OOF on all seasons (the folds of reports/stuff_model): outcome
               log-loss, xRV skill vs the count baseline, calibration slope, first-N → rest of season, split-half.
altitude       Stuff+ fit on all data, every pitch scored at sea level and in Harp Helú air: league ΔStuff+ and by
               shape (the C3 story must survive tuning).
holdouts       season holdout (2024–25 → 2026) and park holdout (No + Medium → Extreme) for all three models
               through the HACK-014 suite (skill + altitude bias).
pitching_kfold Pitching+ pitcher 5-fold OOF + nested combination (the headline +3.88 %).
Writes reports/tuning/before_after_*.csv. Pitch-level predictions stay in memory.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from analysis.tuning.run import OUT, load_frame
from stuffplus import evaluate, splits
from stuffplus.altitude import STUFF_FEATURES_INVARIANT, physics_translator
from stuffplus.baseline import CountBaseline
from stuffplus.features.shapes import fit_shapes
from stuffplus.models import tuning
from stuffplus.models.location import LocationModel
from stuffplus.models.stuff import OUTCOMES, StuffModel, matched_sample_predictiveness, outcome_class, split_half_reliability
from stuffplus.physics.constants import RHO_HARP_HELU
from stuffplus.scale import PlusScaler

PARTS = ("kfold", "altitude", "holdouts", "pitching_kfold")


def settings(chosen: dict, prefix: str) -> tuning.TunedSettings:
    o, c = chosen[f"{prefix}_outcome"], chosen[f"{prefix}_contact"]
    return tuning.TunedSettings(class_params=o["params"], class_rounds=o["rounds"],
                                contact_params=c["params"], contact_rounds=c["rounds"])


def target_rounds(chosen: dict) -> dict[str, int]:
    return {k[len("target_"):]: v["rounds"] for k, v in chosen.items() if k.startswith("target_")}


def models(chosen: dict) -> dict:
    """name -> (factory, is_location). Production = the classes as the integrated pipeline builds them."""
    st, lo = settings(chosen, "stuff"), settings(chosen, "location")
    return {
        "Stuff+": (lambda: StuffModel(features=list(STUFF_FEATURES_INVARIANT)), False),
        "Stuff+ ajustado": (lambda: tuning.TunedStuffModel(features=list(STUFF_FEATURES_INVARIANT), settings=st), False),
        "Location+": (lambda: LocationModel(), True),
        "Location+ ajustado": (lambda: tuning.TunedLocationModel(settings=lo), True),
    }


def _slope(y: np.ndarray, p: np.ndarray) -> float:
    """OLS slope of the outcome on the prediction (1 = calibrated spread; < 1 = predictions too spread out)."""
    ok = np.isfinite(y) & np.isfinite(p)
    return float(np.polyfit(p[ok], y[ok], 1)[0])


def kfold(d: pd.DataFrame, chosen: dict) -> pd.DataFrame:
    folds = list(splits.pitcher_group_kfold(d))
    y = outcome_class(d).to_numpy()
    rows, preds = [], {"baseline": np.full(len(d), np.nan)}
    for tr, te in folds:
        preds["baseline"][te] = CountBaseline().fit(d.iloc[tr], ["rv_x"]).predict(d.iloc[te], "rv_x")
    for name, (factory, is_loc) in models(chosen).items():
        P = np.full((len(d), len(OUTCOMES)), np.nan)
        xrv = np.full(len(d), np.nan)
        for tr, te in folds:
            m = factory().fit(d.iloc[tr])
            comp = m.predict_components(d.iloc[te])
            P[te] = comp[[f"p_{o}" for o in OUTCOMES]].to_numpy()
            xrv[te] = comp["xrv"].to_numpy()
        preds[name] = xrv
        ok = y >= 0
        ll = float(-np.log(np.clip(P[ok][np.arange(ok.sum()), y[ok]], 1e-9, 1)).mean())
        frame = d.assign(_p=xrv)
        pr = matched_sample_predictiveness(frame, "_p", sizes=(50, 200)).set_index("first_n")
        sh = split_half_reliability(frame, "_p")
        rows.append(dict(model=name, outcome_logloss=ll, calibration_slope=_slope(d.rv_x.to_numpy(float), xrv),
                         first50_r=pr.loc[50, "stuff_model"], first200_r=pr.loc[200, "stuff_model"],
                         split_half_r=sh["stuff_model"]))
    skill = evaluate.compare(preds, d.rv_x.to_numpy(float), groups=d.pitcher_anon_id.to_numpy(), n_boot=200)
    out = pd.DataFrame(rows).merge(skill[["model", "skill_vs_baseline", "skill_lo", "skill_hi"]], on="model")
    prior = np.bincount(y[y >= 0], minlength=len(OUTCOMES)) / (y >= 0).sum()
    out["prior_logloss"] = float(-np.log(prior[y[y >= 0]]).mean())
    return out


def altitude(d: pd.DataFrame, chosen: dict) -> pd.DataFrame:
    shape_model, _ = fit_shapes(d)
    translate = physics_translator(shape_model)
    st = settings(chosen, "stuff")
    rows = []
    for name, m in (("Stuff+", StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=translate)),
                    ("Stuff+ ajustado", tuning.TunedStuffModel(features=list(STUFF_FEATURES_INVARIANT),
                                                               translate=translate, settings=st))):
        m.fit(d)
        sea = m.predict_at_rho(d, 1.0)["xrv"].to_numpy()
        hh = m.predict_at_rho(d, RHO_HARP_HELU)["xrv"].to_numpy()
        sc = PlusScaler().fit(d.assign(x=sea), "x")
        delta = sc.transform(d.assign(x=hh), "x").to_numpy() - sc.transform(d.assign(x=sea), "x").to_numpy()
        by = pd.Series(delta).groupby(d["shape"].astype(str).to_numpy()).agg(["mean", "size"])
        by = by[by["size"] >= 200]["mean"]
        rows.append(dict(model=name, league_delta=float(delta.mean()), best_shape=by.idxmax(), best_delta=by.max(),
                         worst_shape=by.idxmin(), worst_delta=by.min(),
                         **{f"delta_{k}": v for k, v in by.items()}))
    return pd.DataFrame(rows)


def holdouts(d: pd.DataFrame, chosen: dict) -> dict[str, pd.DataFrame]:
    from stuffplus.validation.models import PitchingEstimator
    from stuffplus.validation.run_all import ModelSpec, run_all

    specs = {name: ModelSpec(f) for name, (f, _) in models(chosen).items()}
    specs["Pitching+"] = ModelSpec(lambda: PitchingEstimator(inner_k=3))
    specs["Pitching+ ajustado"] = ModelSpec(lambda: tuning.TunedPitchingEstimator(
        settings(chosen, "pitching"), target_rounds(chosen), inner_k=3))
    return run_all(d, OUT / "holdouts", demo_data=False, models=specs, only={"season_holdout", "park_holdout"})


def pitching_kfold(d: pd.DataFrame, chosen: dict) -> pd.DataFrame:
    from stuffplus.models.pitching import combine, run_oof

    folds = list(splits.pitcher_group_kfold(d))
    y = d.rv_x.to_numpy(float)
    base = np.full(len(d), np.nan)
    for tr, te in folds:
        base[te] = CountBaseline().fit(d.iloc[tr], ["rv_x"]).predict(d.iloc[te], "rv_x")
    prod = combine(run_oof(d, folds), y, folds)["combined"]
    tuned = combine(tuning.run_oof(d, folds, settings(chosen, "pitching"), target_rounds(chosen)), y, folds)["combined"]
    preds = {"baseline": base, "Pitching+": np.asarray(prod, float), "Pitching+ ajustado": np.asarray(tuned, float)}
    out = evaluate.compare(preds, y, groups=d.pitcher_anon_id.to_numpy(), n_boot=200)
    for name in ("Pitching+", "Pitching+ ajustado"):
        frame = d.assign(_p=preds[name])
        pr = matched_sample_predictiveness(frame, "_p", sizes=(50, 200)).set_index("first_n")
        out.loc[out.model == name, ["first50_r", "first200_r", "split_half_r", "calibration_slope"]] = [
            pr.loc[50, "stuff_model"], pr.loc[200, "stuff_model"], split_half_reliability(frame, "_p")["stuff_model"],
            _slope(y, preds[name])]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parts", nargs="*", choices=PARTS, default=list(PARTS))
    args = ap.parse_args()
    chosen = json.loads((OUT / "chosen.json").read_text())
    d = load_frame()
    for part in args.parts:
        if part == "kfold":
            kfold(d, chosen).round(6).to_csv(OUT / "before_after_kfold.csv", index=False)
        elif part == "altitude":
            altitude(d, chosen).round(4).to_csv(OUT / "before_after_altitude.csv", index=False)
        elif part == "holdouts":
            holdouts(d, chosen)
        else:
            pitching_kfold(d, chosen).round(6).to_csv(OUT / "before_after_pitching_kfold.csv", index=False)
        print("done", part, flush=True)


if __name__ == "__main__":
    main()
