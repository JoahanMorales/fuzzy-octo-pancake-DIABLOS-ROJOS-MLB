"""HACK-003 on the real data: teams, home parks, franchises, Harp Helú candidate.

    python -m analysis.park_id.run

Writes aggregates only to reports/park_id/ (parks.csv, franchise_rho.csv, summary.txt). Row-level maps are
never committed: other tasks call ``stuffplus.physics.parks.load_maps()``, which rebuilds them from the raw
data (cached under git-ignored artifacts/). This script refreshes that cache.

rho_hat here is PROVISIONAL (local Cd-proxy of fastballs, relative to the No-altitude median). HACK-004's
``aero.game_density_index`` replaces it; park identification itself never uses it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stuffplus.config import ARTIFACTS_DIR, REPORTS_DIR
from stuffplus.io import load_raw
from stuffplus.physics.parks import (GAME, build_maps, candidate_staff, game_teams, link_franchises, park_table,
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
    # Decision rule (TASKS.md): if P(lowest < second) < 0.95 the candidate is NOT decisive, so report the two
    # lowest-rho franchises and pool them as the CDMX environment. Franchise identities are unverified.
    order = [int(f) for f in sorted(samples, key=lambda f: samples[f].mean())]
    top2 = order[:2]
    p_low = float((samples[order[0]] < samples[order[1]]).mean()) if len(order) >= 2 else float("nan")
    decisive = p_low >= 0.95
    chosen = order[:1] if decisive else top2
    pooled = games_all[games_all["franchise"].isin(chosen)]["rho"].dropna().to_numpy()
    boot = np.array([rng.choice(pooled, len(pooled)).mean() for _ in range(N_BOOT)])
    maps = build_maps(df)
    staff = candidate_staff(maps, chosen)
    staff_counts = staff.groupby(["season", "franchise"]).size().unstack(fill_value=0)
    gaps = pd.DataFrame(rows).set_index("franchise")["rho_mean"]
    md = [
        "# Harp Helú candidate (HACK-003)", "",
        f"- Extreme franchises (6): lowest rho_hat = {order[0]} ({gaps[order[0]]:.3f}) and {order[1]} ({gaps[order[1]]:.3f}).",
        f"- P(franchise {order[0]} lower than {order[1]}) = {p_low:.3f} (pooled game-level bootstrap, {N_BOOT} draws).",
        f"- Decisive (P >= 0.95): {'yes' if decisive else 'NO'}. "
        + ("Candidate: franchise " + str(order[0]) if decisive else
           f"Reporting the two lowest-density parks and pooling them: franchises {top2}."),
        f"- Pooled rho_hat of {chosen}: {boot.mean():.3f} (95% CI {np.quantile(boot, .025):.3f}-{np.quantile(boot, .975):.3f}, "
        f"{len(pooled)} games). Provisional proxy; HACK-004 replaces it.",
        f"- Theoretical gap Harp Helú (2,240 m) vs Puebla (2,135 m): ~1.2 % pressure; observed gap "
        f"{abs(gaps[order[0]] - gaps[order[1]]) * 100:.1f} % of rho.",
        "- Franchise identity (CDMX vs Puebla) is NOT verified from the data: ids are anonymous. Confirm with Diablos staff.",
        "- Coverage caveat: the lowest-rho franchise has few home games in the dataset "
        + str(games_all[games_all["franchise"] == order[0]].groupby("season").size().to_dict()) + " (home games per season).",
        "", "## Candidate staff (pitchers per season; ids via `candidate_staff(load_maps(), franchises)`)", "",
        "```", staff_counts.to_string(), "```",
    ]
    (OUT / "harp_helu.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    (OUT / "summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    for name, frame in maps.items():
        frame.to_parquet(ARTIFACTS_DIR / f"{name}.parquet", index=False)


if __name__ == "__main__":
    main()
