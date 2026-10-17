"""Pipeline step ``roster_names`` (HACK-056): put roster names into the leaderboard and staff CSVs.

    python -m analysis.pipeline.names            # no roster file = no-op
    python -m analysis.pipeline.names --dirs reports/leaderboards reports/staff_audit

Every CSV with a ``pitcher_anon_id`` column in those folders gets ``pitcher_name`` (and ``team`` / ``role`` when the
roster has them) through ``stuffplus.roster.apply_names``, so the web export, which reads these CSVs, shows names
without refitting anything. Idempotent: earlier name columns are dropped before mapping. Without a roster the CSVs
are left untouched.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from stuffplus import config
from stuffplus.roster import apply_names, load_roster

DIRS = ("reports/leaderboards", "reports/staff_audit")
ADDED = ("pitcher_name", "team_roster", "role_roster")


def name_csvs(dirs, roster: pd.DataFrame | None, root: Path | None = None) -> list[Path]:
    """Map names into every CSV with ``pitcher_anon_id`` under ``dirs``; returns the files rewritten."""
    if roster is None or roster.empty:
        return []
    root = root or config.repo_root()
    extra = roster.set_index("pitcher_anon_id")[["team", "role"]]
    done = []
    for d in dirs:
        for f in sorted((root / d).glob("*.csv")):
            df = pd.read_csv(f, dtype={"pitcher_anon_id": "string"})
            if "pitcher_anon_id" not in df:
                continue
            df = apply_names(df.drop(columns=[c for c in ADDED if c in df]), roster=roster)
            ids = df["pitcher_anon_id"].astype("string")
            for src, dst in (("team", "team_roster"), ("role", "role_roster")):
                vals = ids.map(extra[src]).fillna("")
                if (vals != "").any():
                    df[dst] = vals
            df.to_csv(f, index=False)
            done.append(f)
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dirs", nargs="+", default=list(DIRS))
    args = ap.parse_args(argv)
    roster = load_roster()
    files = name_csvs(args.dirs, roster)
    print(f"roster_names: {'no roster, nothing to do' if roster is None else f'{len(files)} CSV files named'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
