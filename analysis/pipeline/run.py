"""HACK-056: one command to retrain, rescore and regenerate every report, in dependency order.

    python -m analysis.pipeline.run                      # every step (hours; needs data/raw/stuff_model_df.parquet)
    python -m analysis.pipeline.run --dry-run            # print the order and the exact commands, run nothing
    python -m analysis.pipeline.run --from score         # resume from a step (that step and all after it)
    python -m analysis.pipeline.run --only staff_audit   # a single step

Every step is an entry point that already exists in the repo; the commands below are the ones their docstrings
and READMEs document. Each step runs from the repo root in its own subprocess, one status line per step with
the elapsed seconds, and the run stops at the first non-zero exit naming the step. The full output of every
step goes to ``artifacts/pipeline/<timestamp>.log`` (git-ignored).

A step whose entry point is not on disk yet and is flagged ``optional`` (the web export) is skipped, not failed.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "artifacts" / "pipeline"


@dataclass(frozen=True)
class Step:
    name: str
    argv: tuple[str, ...]  # arguments after the interpreter, e.g. ("-m", "stuffplus.targets")
    reads: str = ""        # inputs, for the dry-run listing
    writes: str = ""       # outputs, for the dry-run listing
    deps: tuple[str, ...] = ()  # steps whose outputs this one consumes (must come earlier in STEPS)
    path: str | None = None     # entry-point file relative to the repo root (existence check)
    optional: bool = False      # skip instead of fail when ``path`` does not exist

    def command(self, python: str | None = None) -> list[str]:
        return [python or sys.executable, *self.argv]

    def available(self, root: Path = ROOT) -> bool:
        return self.path is None or (root / self.path).exists()


def _mod(name: str, module: str, *args: str, **kw) -> Step:
    """A ``python -m module`` step; the entry-point file is derived from the module name."""
    return Step(name, ("-m", module, *args), path=module.replace(".", "/") + ".py", **kw)


def _script(name: str, rel: str, *args: str, **kw) -> Step:
    return Step(name, (rel, *args), path=rel, **kw)


RAW = "data/raw/stuff_model_df.parquet"
STEPS: tuple[Step, ...] = (
    _mod("targets", "stuffplus.targets", reads=RAW,
         writes="reports/targets/*.csv (run values, RE matrix, linear weights)"),
    _mod("baseline", "stuffplus.baseline", deps=("targets",), reads=RAW, writes="reports/baseline/baseline_metrics.csv"),
    _mod("park_id", "analysis.park_id.run", reads=RAW,
         writes="reports/park_id/*; artifacts/park_map.parquet, team_map.parquet (cache)"),
    _mod("physics", "analysis.physics.run", reads=RAW, writes="reports/physics/*"),
    _mod("stuff_model", "analysis.stuff_model.run", deps=("targets", "park_id", "physics"), reads=RAW,
         writes="artifacts/bundle (Stuff+); reports/stuff_model/*"),
    _mod("location_model", "analysis.location_model.run", deps=("stuff_model",), reads=RAW + "; artifacts/bundle",
         writes="artifacts/bundle (+Location+); reports/location_model/*"),
    _mod("pitching_model", "analysis.pitching_model.run", deps=("stuff_model", "location_model"),
         reads=RAW + "; artifacts/bundle", writes="artifacts/bundle (+Pitching+); reports/pitching_model/*"),
    _mod("altitude_delta", "analysis.altitude_delta.run", deps=("stuff_model", "physics"), reads=RAW,
         writes="reports/altitude_delta/*"),
    _mod("hypotheses", "analysis.hypotheses.run", deps=("targets", "park_id", "physics"), reads=RAW,
         writes="reports/hypotheses/* (H1-H4; the memo cites results.csv)"),
    _mod("validation_holdouts", "analysis.validation.run", "--splits", "holdouts", "--pitching-inner-k", "3",
         "--out", "reports/validation/official_full", deps=("stuff_model", "location_model", "pitching_model"),
         reads=RAW, writes="reports/validation/official_full/*"),
    _mod("validation_fast", "analysis.validation.run", "--fast", "--out", "reports/validation/official_fast",
         deps=("stuff_model", "location_model", "pitching_model"), reads=RAW,
         writes="reports/validation/official_fast/* (23 splits, stability)"),
    _mod("validation_summary", "stuffplus.validation.summary",
         deps=("stuff_model", "location_model", "pitching_model", "validation_holdouts", "validation_fast"),
         reads="reports/{stuff,location,pitching}_model/metrics.csv; reports/validation/official_*/",
         writes="reports/validation/summary.md, headline.csv"),
    _mod("score", "stuffplus.score", deps=("altitude_delta", "park_id"), reads=RAW,
         writes="artifacts/scores/pitch_scores.parquet; reports/leaderboards/*.csv"),
    _mod("pitcher_sensitivity", "analysis.pitcher_sensitivity.run", deps=("altitude_delta",), reads=RAW,
         writes="reports/pitcher_sensitivity/*"),
    _mod("ideal_profile", "analysis.ideal_profile.run", deps=("altitude_delta",), reads=RAW,
         writes="reports/ideal_profile/*"),
    _script("design_lab", "reports/design_lab/run.py", deps=("altitude_delta", "ideal_profile"), reads=RAW,
            writes="reports/design_lab/*"),
    _mod("business_value", "analysis.business_value.run", deps=("stuff_model", "pitching_model", "park_id"), reads=RAW,
         writes="reports/business_value/*"),
    _mod("staff_audit", "analysis.staff_audit.run", deps=("score", "pitcher_sensitivity", "park_id"),
         reads="artifacts/scores/pitch_scores.parquet; artifacts/*_map.parquet; reports/pitcher_sensitivity/",
         writes="reports/staff_audit/*"),
    _mod("cards", "stuffplus.cards", deps=("score", "pitcher_sensitivity", "altitude_delta", "park_id"),
         reads="reports/leaderboards, pitcher_sensitivity, altitude_delta; artifacts/team_map.parquet",
         writes="reports/cards/ (PNG/PDF pitcher cards, manifest.csv)"),
    # The memo reads only these CSV folders: altitude_delta, business_value, hypotheses, ideal_profile, location_model.
    _script("memo", "reports/recommendations/build_memo.py",
            deps=("altitude_delta", "hypotheses", "ideal_profile", "location_model", "business_value"),
            reads="reports/**/*.csv (no raw data)", writes="reports/recommendations/memo.md"),
    # Placeholder: a later task adds the exporter; until analysis/export_web exists the step is skipped.
    _mod("web_export", "analysis.export_web.run", deps=("score", "staff_audit", "memo"), optional=True,
         reads="reports/ and artifacts/ aggregates", writes="web data files (aggregates only)"),
)


def check_order(steps: Sequence[Step]) -> list[str]:
    """Problems with a step list: duplicate names, unknown dependencies, dependencies listed after their user."""
    problems, seen = [], set()
    names = [s.name for s in steps]
    for s in steps:
        if s.name in seen:
            problems.append(f"duplicate step {s.name}")
        for d in s.deps:
            if d not in names:
                problems.append(f"{s.name}: unknown dependency {d}")
            elif d not in seen:
                problems.append(f"{s.name}: dependency {d} comes later")
        seen.add(s.name)
    return problems


def select(steps: Sequence[Step], *, from_step: str | None = None, only: str | None = None) -> list[Step]:
    names = [s.name for s in steps]
    for label, value in (("--from", from_step), ("--only", only)):
        if value is not None and value not in names:
            raise ValueError(f"{label}: unknown step {value!r}; steps are: {', '.join(names)}")
    if from_step and only:
        raise ValueError("--from and --only are mutually exclusive")
    if only:
        return [s for s in steps if s.name == only]
    if from_step:
        return list(steps[names.index(from_step):])
    return list(steps)


def _fmt(cmd: Sequence[str]) -> str:
    return " ".join(cmd)


def _tail(path: Path, start: int, lines: int = 15) -> str:
    with open(path, "rb") as fh:
        fh.seek(start)
        text = fh.read().decode("utf-8", errors="replace")
    return "\n".join(text.splitlines()[-lines:])


def run_pipeline(steps: Sequence[Step] = STEPS, *, from_step: str | None = None, only: str | None = None,
                 dry_run: bool = False, log_dir: Path | None = None, root: Path = ROOT,
                 out: Callable[[str], None] = print, python: str | None = None) -> int:
    """Run (or list) the selected steps. Returns 0, 2 for a bad selection, or the failing step's exit code."""
    try:
        chosen = select(steps, from_step=from_step, only=only)
    except ValueError as exc:
        out(f"error: {exc}")
        return 2
    total = len(chosen)
    if dry_run:
        out(f"Pipeline (dry run): {total} of {len(steps)} steps, nothing is executed")
        for i, s in enumerate(chosen, 1):
            tag = "  [skipped: entry point not on disk]" if s.optional and not s.available(root) else ""
            out(f"[{i:>2}/{total}] {s.name}{tag}")
            out(f"        $ {_fmt(s.command('python'))}")
            if s.deps:
                out(f"        after: {', '.join(s.deps)}")
            if s.reads:
                out(f"        reads: {s.reads}")
            if s.writes:
                out(f"        writes: {s.writes}")
        return 0

    log_dir = Path(log_dir) if log_dir is not None else LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{datetime.now():%Y%m%d-%H%M%S}.log"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    t_all = time.perf_counter()
    out(f"Pipeline: {total} steps - log {log_path}")
    done = 0
    with open(log_path, "ab") as log:
        for i, s in enumerate(chosen, 1):
            head = f"[{i:>2}/{total}] {s.name:<22}"
            if s.optional and not s.available(root):
                out(f"{head} SKIP (missing {s.path})")
                log.write(f"=== {s.name}: skipped, missing {s.path}\n".encode())
                continue
            cmd = s.command(python)
            log.write(f"\n=== {s.name} - {datetime.now():%H:%M:%S} - {_fmt(cmd)}\n".encode())
            log.flush()
            start = log.tell()
            t0 = time.perf_counter()
            out(f"{head} running...")
            try:
                code = subprocess.run(cmd, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
            except OSError as exc:
                log.write(f"could not start: {exc}\n".encode())
                code = 127
            log.flush()
            dt = time.perf_counter() - t0
            if code != 0:
                out(f"{head} FAIL exit {code} after {dt:.1f} s")
                out(f"Pipeline stopped at step '{s.name}' ({done}/{total} done). Last output:")
                out(_tail(log_path, start))
                out(f"Resume with: python -m analysis.pipeline.run --from {s.name}   (full log: {log_path})")
                return code
            done += 1
            out(f"{head} OK   {dt:.1f} s")
    out(f"Pipeline done: {done}/{total} steps in {time.perf_counter() - t_all:.1f} s - log {log_path}")
    return 0


def main(argv: Sequence[str] | None = None, steps: Sequence[Step] | None = None) -> int:
    steps = steps or STEPS
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from", dest="from_step", metavar="STEP",
                    help="start at this step; steps: " + ", ".join(s.name for s in steps))
    ap.add_argument("--only", metavar="STEP", help="run just this step")
    ap.add_argument("--dry-run", action="store_true", help="print the order and commands, run nothing")
    args = ap.parse_args(argv)
    return run_pipeline(steps, from_step=args.from_step, only=args.only, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
