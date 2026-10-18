"""HACK-056: the pipeline's step list and runner. Synthetic only; the real steps are never executed here."""
from __future__ import annotations

import pytest

from analysis.pipeline import run as pipe
from analysis.pipeline.run import Step, check_order, run_pipeline, select

OK = ("-c", "print('ok')")
BAD = ("-c", "import sys; print('boom'); sys.exit(3)")


def fake(tmp_path, bad_at=None):
    marks = tmp_path / "marks"
    marks.mkdir(exist_ok=True)

    def step(name, deps=(), fail=False):
        code = BAD if fail else ("-c", f"open(r'{marks / name}', 'w').write('x')")
        return Step(name, code, deps=deps)

    return (step("a"), step("b", ("a",), fail=bad_at == "b"), step("c", ("b",)), step("d", ("c",))), marks


def test_real_steps_are_a_valid_topological_order():
    assert check_order(pipe.STEPS) == []
    names = [s.name for s in pipe.STEPS]
    assert len(names) == len(set(names))
    # the order promised by the task: targets before models, models before scores, scores before staff and memo
    pos = {n: i for i, n in enumerate(names)}
    assert pos["targets"] < pos["stuff_model"] < pos["altitude_delta"] < pos["score"] < pos["staff_audit"] < pos["memo"]
    assert pos["validation_summary"] > pos["validation_holdouts"]


def test_check_order_flags_problems():
    a, b = Step("a", OK), Step("b", OK, deps=("a",))
    assert check_order([a, b]) == []
    assert any("comes later" in p for p in check_order([b, a]))
    assert any("unknown dependency" in p for p in check_order([Step("x", OK, deps=("nope",))]))
    assert any("duplicate" in p for p in check_order([a, a]))


def test_every_non_optional_step_exists_on_disk():
    for s in pipe.STEPS:
        if not s.optional:
            assert (pipe.ROOT / s.path).is_file(), f"{s.name}: missing {s.path}"


def test_commands_use_real_entry_points():
    for s in pipe.STEPS:
        cmd = s.command("python")
        assert cmd[0] == "python"
        assert cmd[1] == "-m" or cmd[1].endswith(".py")


def test_dry_run_lists_every_step_and_runs_nothing(capsys, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("dry-run must not start a subprocess")

    monkeypatch.setattr(pipe.subprocess, "run", boom)
    assert pipe.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    for s in pipe.STEPS:
        assert s.name in out
        assert " ".join(s.command("python")) in out


def test_dry_run_marks_missing_optional_step(tmp_path):
    lines = []
    optional = Step("web", OK, path="analysis/export_web/run.py", optional=True)
    assert run_pipeline([optional], dry_run=True, root=tmp_path, out=lines.append) == 0
    assert any("skipped" in ln for ln in lines)


def test_selection_from_and_only():
    names = lambda sel: [s.name for s in sel]
    assert names(select(pipe.STEPS)) == [s.name for s in pipe.STEPS]
    assert names(select(pipe.STEPS, only="score")) == ["score"]
    tail = names(select(pipe.STEPS, from_step="score"))
    assert tail[0] == "score" and tail[-1] == pipe.STEPS[-1].name
    with pytest.raises(ValueError, match="unknown step"):
        select(pipe.STEPS, only="nope")
    with pytest.raises(ValueError, match="mutually exclusive"):
        select(pipe.STEPS, from_step="score", only="score")


def test_bad_selection_exits_2(capsys):
    assert pipe.main(["--from", "nope"]) == 2
    assert "unknown step" in capsys.readouterr().out


def test_runs_all_steps_in_order_and_writes_log(tmp_path):
    steps, marks = fake(tmp_path)
    lines = []
    assert run_pipeline(steps, log_dir=tmp_path / "logs", root=tmp_path, out=lines.append) == 0
    assert sorted(p.name for p in marks.iterdir()) == ["a", "b", "c", "d"]
    ok = [ln for ln in lines if " OK " in ln]
    assert len(ok) == 4 and all(" s" in ln for ln in ok)
    logs = list((tmp_path / "logs").glob("*.log"))
    assert len(logs) == 1 and "=== d" in logs[0].read_text()


def test_from_and_only_run_only_selected(tmp_path):
    steps, marks = fake(tmp_path)
    assert run_pipeline(steps, from_step="c", log_dir=tmp_path / "l1", root=tmp_path, out=lambda _: None) == 0
    assert sorted(p.name for p in marks.iterdir()) == ["c", "d"]
    for p in marks.iterdir():
        p.unlink()
    assert run_pipeline(steps, only="b", log_dir=tmp_path / "l2", root=tmp_path, out=lambda _: None) == 0
    assert [p.name for p in marks.iterdir()] == ["b"]


def test_failure_stops_the_run_and_names_the_step(tmp_path):
    steps, marks = fake(tmp_path, bad_at="b")
    lines = []
    code = run_pipeline(steps, log_dir=tmp_path / "logs", root=tmp_path, out=lines.append)
    assert code == 3
    assert [p.name for p in marks.iterdir()] == ["a"]  # c and d never ran
    text = "\n".join(lines)
    assert "FAIL" in text and "stopped at step 'b'" in text and "boom" in text
    assert "--from b" in text


def test_missing_optional_step_is_skipped_not_failed(tmp_path):
    steps, marks = fake(tmp_path)
    web = Step("web", OK, deps=("d",), path="analysis/export_web/run.py", optional=True)
    lines = []
    assert run_pipeline((*steps, web), log_dir=tmp_path / "logs", root=tmp_path, out=lines.append) == 0
    assert any("SKIP" in ln and "web" in ln for ln in lines)


def test_main_accepts_injected_steps(tmp_path, capsys):
    steps, marks = fake(tmp_path)
    assert pipe.main(["--dry-run", "--only", "b"], steps=steps) == 0
    out = capsys.readouterr().out
    assert "b" in out and "[ 1/1]" in out
    assert not list(marks.iterdir())


def test_validation_runs_before_altitude_and_names_before_web_export():
    pos = {s.name: i for i, s in enumerate(pipe.STEPS)}
    assert pos["validation_summary"] < pos["altitude_delta"] < pos["score"]
    assert pos["staff_audit"] < pos["roster_names"] < pos["web_export"]
    web = next(s for s in pipe.STEPS if s.name == "web_export")
    assert "roster_names" in web.deps
