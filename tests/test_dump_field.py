"""Tests for tools/dump_field.py collection access helpers."""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import dump_field  # noqa: E402


def _make_collection(path):
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.execute("INSERT INTO notes VALUES (1, ?)", ("front\x1fback",))
    con.commit()
    return con


def test_find_notes_exact_front_match(tmp_path):
    con = _make_collection(tmp_path / "c.anki2")
    con.execute("INSERT INTO notes VALUES (2, ?)", ("frontline\x1fother",))
    con.commit()
    assert [nid for nid, _ in dump_field.find_notes(con, "front")] == [1]
    con.close()


def test_find_notes_contains_any_field(tmp_path):
    con = _make_collection(tmp_path / "c.anki2")
    matches = dump_field.find_notes(con, "back", contains=True)
    assert [nid for nid, _ in matches] == [1]
    con.close()


def test_snapshot_includes_uncheckpointed_wal_rows(tmp_path):
    """Rows still in the -wal sidecar (Anki running) must be visible.

    Copying only the main collection file silently reads a stale snapshot;
    the snapshot must include the -wal/-shm sidecars.
    """
    db = tmp_path / "collection.anki2"
    con = _make_collection(db)
    con.execute("PRAGMA wal_autocheckpoint=0")
    con.execute("INSERT INTO notes VALUES (2, ?)", ("new\x1frow",))
    con.commit()
    assert os.path.exists(str(db) + "-wal")

    snap = dump_field.snapshot_collection(str(db))
    try:
        count = sqlite3.connect(snap).execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    finally:
        dump_field.remove_snapshot(snap)
        con.close()
    assert count == 2


def test_remove_snapshot_cleans_sidecars(tmp_path):
    db = tmp_path / "collection.anki2"
    con = _make_collection(db)
    con.execute("PRAGMA wal_autocheckpoint=0")
    con.execute("INSERT INTO notes VALUES (2, ?)", ("new\x1frow",))
    con.commit()
    snap = dump_field.snapshot_collection(str(db))
    con.close()
    assert os.path.exists(snap + "-wal")
    dump_field.remove_snapshot(snap)
    assert not os.path.exists(snap)
    assert not os.path.exists(snap + "-wal")


def test_dump_out_writes_full_field_bytes(tmp_path, capsys):
    db = tmp_path / "c.anki2"
    con = _make_collection(db)
    con.close()
    out = tmp_path / "fields"
    dump_field.dump(str(db), "front", contains=False, out=str(out))
    assert (out / "1_field0.html").read_text() == "front"
    assert (out / "1_field1.html").read_text() == "back"
    assert "1_field0.html" in capsys.readouterr().out


def test_dump_no_match_message(tmp_path, capsys):
    db = tmp_path / "c.anki2"
    con = _make_collection(db)
    con.close()
    dump_field.dump(str(db), "absent", contains=False)
    assert "No note matched" in capsys.readouterr().out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
