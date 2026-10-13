"""HACK-003 on the real data: teams, home parks, franchises, Harp Helú candidate.

    python -m analysis.park_id.run

Writes aggregates only to reports/park_id/ (parks.csv, franchise_rho.csv, summary.txt) and ID mappings to
artifacts/ (park_map.parquet, team_map.parquet; git-ignored). No pitch-level rows leave this script.

rho_hat here is PROVISIONAL (local Cd-proxy of fastballs, relative to the No-altitude median). HACK-004's
``aero.game_density_index`` replaces it; park identification itself never uses it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stuffplus.config import ARTIFACTS_DIR, REPORTS_DIR
from stuffplus.io import load_raw
from stuffplus.physics.parks import (GAME, game_teams, link_franchises, park_table,
                                     pitcher_teams, tune_resolution)
from stuffplus.schema import clean

OUT = REPORTS_DIR / "park_id"
N_BOOT = 2000
SEED = 2240


def provisional_rho(df: pd.DataFrame) -> pd.Series:
    """Per game: median drag coefficient proxy of fastballs / median over 'No Altitude' games."""
    fb = df[df["is_fastball"].astype(bool)]
    v = fb[["vx0", "vy0", "vz0"]].to_numpy(float)
    a = fb[["ax0", "ay0", "az0"]].to_numpy(float)
    speed = np.linalg.norm(v, axis=1)
    drag = -(a * v).sum(axis=1) / speed  # deceleration along the velocity
    cd = pd.Series(drag / speed**2, index=fb.index)
    per_game = cd.groupby(fb[GAME]).median()
    sea = fb.groupby(GAME, observed=True)["altitude_category"].first().astype(str).str.startswith("No")
    return per_game / per_game[sea.reindex(per_game.index).fillna(False)].median()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df = clean(load_raw())
    rho = provisional_rho(df)
    seasons = sorted(df["year"].unique())
    bmaps, parks, gmaps, tmaps, resolutions = {}, [], [], [], {}
    for yr in seasons:
        sub = df[df["year"] == yr]
        res, bt = tune_resolution(sub)
        resolutions[yr] = res
        games = game_teams(sub, bt)
        tbl = park_table(sub, games, rho)
        tbl.insert(0, "season", yr)
        bmaps[yr], parks = bt, parks + [tbl]
        g = games.assign(season=yr)
        gmaps.append(g.reset_index())
        tmaps.append(pd.concat([bt.dropna().rename("team_id").reset_index().assign(role="batter"),
                                pitcher_teams(sub, bt).reset_index().assign(role="pitcher")]).assign(season=yr))
    parks = pd.concat(parks, ignore_index=True)
    links = link_franchises(bmaps)
    parks = parks.merge(links, on=["season", "team_id"])

    # runs per game by home park would need targets (HACK-030); left out of this table on purpose.
    parks.to_csv(OUT / "parks.csv", index=False)

    # Harp Helú candidate: pooled bootstrap of game-level rho_hat per Extreme franchise.
    games_all = pd.concat(gmaps, ignore_index=True).merge(links, left_on=["season", "home_team"],
                                                          right_on=["season", "team_id"])
    games_all["rho"] = games_all[GAME].map(rho)
    extreme = parks[parks["bucket"].astype(str).str.startswith("Extreme")]["franchise"].unique()
    rng = np.random.default_rng(SEED)
    samples = {}
    for f in extreme:
        x = games_all.loc[games_all["franchise"] == f, "rho"].dropna().to_numpy()
        samples[f] = np.array([rng.choice(x, len(x)).mean() for _ in range(N_BOOT)])
    rows = [{"franchise": f, "games": int(games_all.loc[games_all["franchise"] == f, "rho"].notna().sum()),
             "rho_mean": s.mean(), "ci_lo": np.quantile(s, 0.025), "ci_hi": np.quantile(s, 0.975)}
            for f, s in samples.items()]
    pd.DataFrame(rows).sort_values("rho_mean").to_csv(OUT / "franchise_rho.csv", index=False)

    lines = [f"seasons: {[int(y) for y in seasons]} louvain resolution: { {int(y): r for y, r in resolutions.items()} }"]
    for yr in seasons:
        p = parks[parks["season"] == yr]
        lines.append(f"{yr}: teams={len(p)} median_home_games={p['home_games'].median():.0f} "
                     f"min_purity={p['purity'].min():.2f} buckets={p['bucket'].astype(str).value_counts().to_dict()}")
    if len(samples) >= 2:
        order = sorted(samples, key=lambda f: samples[f].mean())
        a, b = order[0], order[1]
        lines.append(f"P(franchise {a} lower rho than {b}) = {(samples[a] < samples[b]).mean():.3f}")
    (OUT / "summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    pd.concat(gmaps, ignore_index=True).to_parquet(ARTIFACTS_DIR / "park_map.parquet", index=False)
    pd.concat(tmaps, ignore_index=True).to_parquet(ARTIFACTS_DIR / "team_map.parquet", index=False)


if __name__ == "__main__":
    main()
