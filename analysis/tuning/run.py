"""python -m analysis.tuning.run --stage search|evaluate  (HACK-028).

search   (~30 min): 2024–25 only, 3 pitcher-grouped folds. For every booster of Stuff+, Location+ and Pitching+:
         the production setting (fixed rounds) vs a small regularization grid with the round count picked on
         inner validation pitchers. Writes reports/tuning/search_*.csv, search_summary.csv and chosen.json.
evaluate (hours): before/after with the chosen settings (see ``analysis/tuning/evaluate.py``).
The prepared pitch-level frame is cached in the git-ignored artifacts/tuning/ of the main checkout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from stuffplus import config, splits
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.models import multitarget as mt
from stuffplus.models import tuning
from stuffplus.models.location import LOCATION_FEATURES
from stuffplus.models.pitching import PITCHING_FEATURES, batter_table, build_features, with_batter
from stuffplus.models.stuff import CLASS_PARAMS, CONTACT_PARAMS

OUT = config.REPORTS_DIR / "tuning"
PROD_WIDE = {"learning_rate": 0.08, "num_leaves": 127, "min_data_in_leaf": 300}  # Location+/Pitching+ outcome


def artifacts() -> Path:
    main = config.main_checkout_root()
    return (main / "artifacts" if main else config.ARTIFACTS_DIR) / "tuning"


def load_frame() -> pd.DataFrame:
    """Altitude-delta preparation (pitch_family, shape, rho) + Pitching+ features, cached (git-ignored)."""
    path = artifacts() / "frame_pitching.parquet"
    if path.exists():
        return pd.read_parquet(path)
    from analysis.altitude_delta.run import prepare
    from stuffplus.io import load_raw
    from stuffplus.schema import clean

    _, d = prepare(clean(load_raw()))
    d = build_features(d)
    path.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(path, index=False)
    return d


def _with_batter(train: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    tab, mu = batter_table(train)  # batter quality from the training fold only
    return with_batter(d, tab, mu)


def search_plan() -> list[dict]:
    lr = 0.05
    narrow = tuning.grid({"learning_rate": [lr], "num_leaves": [15, 31, 63], "min_data_in_leaf": [500, 3000],
                          "lambda_l2": [1.0, 10.0]})
    wide = tuning.grid({"learning_rate": [lr], "num_leaves": [63, 127], "min_data_in_leaf": [300, 1500]})
    contact = tuning.grid({"learning_rate": [lr], "num_leaves": [15, 31], "min_data_in_leaf": [1000, 3000]})
    prod_contact = (CONTACT_PARAMS, 200)
    plan = [
        dict(name="stuff_outcome", features=STUFF_FEATURES_INVARIANT, kind="outcome", configs=narrow,
             production=(CLASS_PARAMS, 300), allow_location=False),
        dict(name="stuff_contact", features=STUFF_FEATURES_INVARIANT, kind="contact", configs=contact,
             production=prod_contact, allow_location=False),
        dict(name="location_outcome", features=LOCATION_FEATURES, kind="outcome", configs=wide,
             production=(PROD_WIDE, 300), allow_location=True),
        dict(name="location_contact", features=LOCATION_FEATURES, kind="contact", configs=contact,
             production=prod_contact, allow_location=True),
        dict(name="pitching_outcome", features=PITCHING_FEATURES, kind="outcome", configs=wide,
             production=(PROD_WIDE, 300), allow_location=True, prepare=_with_batter),
        dict(name="pitching_contact", features=PITCHING_FEATURES, kind="contact", configs=contact,
             production=prod_contact, allow_location=True, prepare=_with_batter),
    ]
    target_params = {k: v for k, v in mt.CLASS_PARAMS.items() if k != "objective"}
    for t in mt.TARGETS:  # same params, only the round count is searched
        plan.append(dict(name=f"target_{t}", features=PITCHING_FEATURES, kind=t, configs=[target_params],
                         production=(target_params, 200), allow_location=True, prepare=_with_batter))
    return plan


def run_search(only: set[str] | None = None) -> dict:
    d = load_frame()
    d = d[d.year < 2026].reset_index(drop=True)  # never the 2026 season holdout
    folds = list(splits.pitcher_group_kfold(d, k=3))
    OUT.mkdir(parents=True, exist_ok=True)
    chosen_path = OUT / "chosen.json"
    chosen = json.loads(chosen_path.read_text()) if chosen_path.exists() else {}
    summaries = []
    for job in search_plan():
        if only and job["name"] not in only:
            continue
        res = tuning.search(d, job["features"], job["configs"], folds, kind=job["kind"],
                            production=job["production"], allow_location=job["allow_location"],
                            prepare=job.get("prepare"), max_rounds=3000)
        res.to_csv(OUT / f"search_{job['name']}.csv", index=False)
        s = tuning.summarize(res).assign(booster=job["name"])
        summaries.append(s)
        params, rounds = tuning.pick(s)
        prod = s[s.config == "production"].iloc[0]
        best = s[s.config != "production"].iloc[0]
        chosen[job["name"]] = dict(params=params, rounds=rounds, test_loss=float(best.test_loss),
                                   production_loss=float(prod.test_loss), production_rounds=int(job["production"][1]))
        print(job["name"], chosen[job["name"]], flush=True)
        chosen_path.write_text(json.dumps(chosen, indent=2) + "\n")
    if summaries:
        new = pd.concat(summaries, ignore_index=True)
        old_path = OUT / "search_summary.csv"
        if old_path.exists():
            old = pd.read_csv(old_path)
            new = pd.concat([old[~old.booster.isin(set(new.booster))], new], ignore_index=True)
        new.round(6).to_csv(old_path, index=False)
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["search", "evaluate"], default="search")
    ap.add_argument("--only", nargs="*", help="search: booster names (e.g. stuff_outcome)")
    args = ap.parse_args()
    if args.stage == "search":
        run_search(set(args.only) if args.only else None)
    else:
        from analysis.tuning.evaluate import main as evaluate
        evaluate()


if __name__ == "__main__":
    main()
