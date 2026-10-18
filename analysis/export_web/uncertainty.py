"""Stuff+ interval half-width by number of pitches and by air (HACK-069): split conformal on pitcher-seasons.

    python -m analysis.export_web.uncertainty   # needs artifacts/scores/pitch_scores.parquet (python -m stuffplus.score)

reports/uncertainty (HACK-055) gives one global width per predictor; the web needs the width for the sample size
of each leaderboard row. For each flavour (Stuff+ neutral, Stuff+ en CDMX) and each n, draw n pitches of a
pitcher-season and score |mean of the n − mean of the rest of the season| (the rest stands in for the pitcher's
value, so the band is slightly conservative). Pitcher-seasons are split in half: the calibration half gives the
90 % split-conformal half-width (stuffplus.uncertainty.split_conformal), the test half its coverage, also on the
altitude-heavy pitcher-seasons (≥ 50 % of pitches in Extreme Altitude; empty with fewer than MIN_SEASONS of them).
The band is calibrated on pitcher-season means, so the pages show it only for season values, not per pitch type. Writes the aggregate table
``analysis/export_web/uncertainty_by_n.csv`` that the real export turns into ``real/uncertainty.json``.
The band describes the raw n-pitch mean; leaderboard values are shrunk toward 100, so it is an upper bound there.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus import config
from stuffplus.uncertainty import coverage, split_conformal

OUT = Path(__file__).with_name("uncertainty_by_n.csv")
FLAVOURS = {"stuff_plus": "neutral", "stuff_plus_harp_helu": "harp_helu"}
N_PITCHES = (25, 50, 100, 200, 300, 500, 800)
MIN_REST = 200
DRAWS = 5
ALPHA = 0.1
MIN_SEASONS = 30  # pitcher-seasons per half; fewer gives an unreliable quantile (n = 800 had 4)
KEY = ["pitcher_anon_id", "year"]


def scores_by_n(d: pd.DataFrame, col: str, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """One row per (pitcher-season, draw): |mean of n random pitches − mean of the rest|."""
    rows = []
    for key, g in d.groupby(KEY, sort=True):
        x = g[col].to_numpy(float)
        x = x[np.isfinite(x)]
        if len(x) < n + max(n, MIN_REST):
            continue
        alt = float(g["extreme"].mean())
        total = x.sum()
        for _ in range(DRAWS):
            idx = rng.choice(len(x), size=n, replace=False)
            s = x[idx].sum()
            rows.append((*key, abs(s / n - (total - s) / (len(x) - n)), alt))
    return pd.DataFrame(rows, columns=[*KEY, "score", "share_extreme"])


def table(d: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    d = d.assign(extreme=d["altitude_category"].astype(str).eq("Extreme Altitude"))
    keys = d[KEY].drop_duplicates().sort_values(KEY).reset_index(drop=True)
    cal = set(map(tuple, keys.sample(frac=0.5, random_state=seed)[KEY].itertuples(index=False)))
    out = []
    for col, air in FLAVOURS.items():
        for n in N_PITCHES:
            s = scores_by_n(d, col, n, np.random.default_rng(seed + n))
            if s.empty:
                continue
            is_cal = np.array([(p, y) in cal for p, y in zip(s.pitcher_anon_id, s.year)])
            c, t = s[is_cal], s[~is_cal]
            if min(c[KEY].drop_duplicates().shape[0], t[KEY].drop_duplicates().shape[0]) < MIN_SEASONS:
                continue
            hw = split_conformal(c.score.to_numpy(), alpha=ALPHA)
            alt = t[t.share_extreme >= 0.5]
            out.append(dict(air=air, n_pitches=n, half_width=round(float(hw), 3),
                            coverage=round(coverage(t.score.to_numpy(), 0.0, hw), 4),
                            coverage_altitude=(round(coverage(alt.score.to_numpy(), 0.0, hw), 4)
                                               if alt[KEY].drop_duplicates().shape[0] >= MIN_SEASONS else np.nan),
                            pitcher_seasons_cal=int(c[KEY].drop_duplicates().shape[0]),
                            pitcher_seasons_test=int(t[KEY].drop_duplicates().shape[0]),
                            n_altitude_test=int(alt[KEY].drop_duplicates().shape[0])))
    return pd.DataFrame(out)


def main() -> None:
    d = pd.read_parquet(config.ARTIFACTS_DIR / "scores" / "pitch_scores.parquet",
                        columns=[*KEY, "altitude_category", *FLAVOURS])
    t = table(d)
    t.to_csv(OUT, index=False)
    print(t.to_string(index=False))


if __name__ == "__main__":
    main()
