import io
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from query_collection import run_query


def _collection(tmp_path):
    db = tmp_path / "collection.anki2"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.execute("CREATE TABLE decks (id INTEGER PRIMARY KEY, name TEXT)")
    con.executemany(
        "INSERT INTO notes (id, flds) VALUES (?, ?)",
        [(1, "front\x1fback"), (2, "水\x1fwater")],
    )
    con.execute("INSERT INTO decks (id, name) VALUES (1, '言語\x1f日語')")
    con.commit()
    con.close()
    return str(db)


def test_run_query_prints_header_and_rows(tmp_path):
    db = _collection(tmp_path)
    out = io.StringIO()
    rows = run_query(db, "SELECT id, flds FROM notes ORDER BY id", out=out)
    assert rows == [(1, "front\x1fback"), (2, "水\x1fwater")]
    assert out.getvalue().splitlines()[0] == "id\tflds"
    assert "1\tfront\x1fback" in out.getvalue()


def test_run_query_handles_unicase_collation(tmp_path):
    db = _collection(tmp_path)
    out = io.StringIO()
    rows = run_query(db, "SELECT name FROM decks ORDER BY name COLLATE unicase", out=out)
    assert rows == [("言語\x1f日語",)]


def test_run_query_removes_snapshot(tmp_path):
    db = _collection(tmp_path)
    before = set(os.listdir(tmp_path))
    run_query(db, "SELECT 1", out=io.StringIO())
    assert set(os.listdir(tmp_path)) == before
