"""HACK-056: optional roster drop-in. Synthetic ids only."""
from __future__ import annotations

import pandas as pd
import pytest

from stuffplus import roster

CSV = "pitcher_anon_id,name,team,role\n101,Ana Perez,Diablos,SP\n102,Beto Ruiz,Diablos,RP\n103,,Tigres,SP\n"


@pytest.fixture
def roster_file(tmp_path, monkeypatch):
    p = tmp_path / "roster.csv"
    p.write_text(CSV, encoding="utf-8")
    monkeypatch.setenv(roster.ENV_VAR, str(p))
    return p


def frame():
    return pd.DataFrame({"pitcher_anon_id": [101, 102, 103, 999, 101], "x": range(5)})


def test_absent_file_returns_none_and_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv(roster.ENV_VAR, str(tmp_path / "nope.csv"))
    assert roster.load_roster() is None
    out = roster.apply_names(frame())
    assert out["pitcher_name"].tolist() == ["101", "102", "103", "999", "101"]


def test_default_path_is_data_roster_csv(monkeypatch):
    monkeypatch.delenv(roster.ENV_VAR, raising=False)
    assert roster.roster_path().parts[-2:] == ("data", "roster.csv")


def test_names_applied_and_missing_ids_fall_back(roster_file):
    df = frame()
    out = roster.apply_names(df)
    assert out["pitcher_name"].tolist() == ["Ana Perez", "Beto Ruiz", "103", "999", "Ana Perez"]  # blank name and unknown id
    assert len(out) == len(df) and out["x"].tolist() == list(range(5))  # order and rows untouched
    assert "pitcher_name" not in df  # input not mutated


def test_load_roster_columns_and_dedupe(tmp_path, monkeypatch):
    p = tmp_path / "r.csv"
    p.write_text("pitcher_anon_id,name\n1,A\n1,B\n2,C\n", encoding="utf-8")
    monkeypatch.setenv(roster.ENV_VAR, str(p))
    r = roster.load_roster()
    assert list(r.columns) == roster.COLUMNS
    assert r.set_index("pitcher_anon_id")["name"].to_dict() == {"1": "B", "2": "C"}


def test_pitcher_id_alias_and_bad_header(tmp_path):
    ok = tmp_path / "a.csv"
    ok.write_text("pitcher_id,name,team,role\n7,Zeta,X,SP\n", encoding="utf-8")
    assert roster.load_roster(ok).pitcher_anon_id.tolist() == ["7"]
    bad = tmp_path / "b.csv"
    bad.write_text("who,what\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        roster.load_roster(bad)


def test_env_override_beats_default_and_custom_column(tmp_path, monkeypatch):
    p = tmp_path / "other.csv"
    p.write_text("pitcher_anon_id,name,team,role\nabc,Cy,T,SP\n", encoding="utf-8")
    monkeypatch.setenv(roster.ENV_VAR, str(p))
    assert roster.roster_path() == p
    df = pd.DataFrame({"pid": ["abc", "zzz"]})
    assert roster.apply_names(df, col="pid")["pitcher_name"].tolist() == ["Cy", "zzz"]


def test_explicit_roster_argument(roster_file):
    r = pd.DataFrame({"pitcher_anon_id": ["101"], "name": ["Solo"], "team": [""], "role": [""]})
    assert roster.apply_names(frame(), roster=r)["pitcher_name"].tolist() == ["Solo", "102", "103", "999", "Solo"]


def test_roster_names_step_names_board_csvs_and_is_idempotent(tmp_path, roster_file):
    from analysis.pipeline.names import name_csvs

    board = tmp_path / "reports" / "leaderboards"
    board.mkdir(parents=True)
    pd.DataFrame({"pitcher_anon_id": ["101", "103", "999"], "stuff_plus": [110, 95, 100]}).to_csv(board / "b.csv", index=False)
    pd.DataFrame({"park": ["x"]}).to_csv(board / "parks.csv", index=False)  # no id column: untouched
    r = roster.load_roster()
    for _ in range(2):
        files = name_csvs(["reports/leaderboards"], r, root=tmp_path)
    assert [f.name for f in files] == ["b.csv"]
    out = pd.read_csv(board / "b.csv", dtype=str)
    assert out["pitcher_name"].tolist() == ["Ana Perez", "103", "999"]
    assert out["team_roster"].fillna("").tolist() == ["Diablos", "Tigres", ""]
    assert list(out.columns).count("pitcher_name") == 1
    assert name_csvs(["reports/leaderboards"], None, root=tmp_path) == []
