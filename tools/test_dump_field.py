import contextlib
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from dump_field import find_notes, split_fields


def _db():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.executemany(
        "INSERT INTO notes (id, flds) VALUES (?, ?)",
        [
            (1, "anguish\x1f<div><i>severe pain</i></div>"),
            (2, "anguished\x1fpast tense of anguish"),
            (3, "front\x1fback mentions anguish in passing"),
        ],
    )
    return con


def test_split_fields_on_unit_separator():
    assert split_fields("a\x1fb\x1fc") == ["a", "b", "c"]


def test_find_notes_matches_front_field_exactly_by_default():
    with contextlib.closing(_db()) as con:
        notes = find_notes(con, "anguish")
    assert [nid for nid, _ in notes] == [1]
    assert notes[0][1][1] == "<div><i>severe pain</i></div>"


def test_find_notes_contains_matches_any_field():
    with contextlib.closing(_db()) as con:
        notes = find_notes(con, "anguish", contains=True)
    assert [nid for nid, _ in notes] == [1, 2, 3]


def test_default_collection_found(monkeypatch, tmp_path):
    import time

    from dump_field import default_collection

    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path))

    col_dir1 = tmp_path / "Library/Application Support/Anki2/User 1"
    col_dir1.mkdir(parents=True, exist_ok=True)
    f1 = col_dir1 / "collection.anki2"
    f1.write_text("dummy")

    time.sleep(0.01)

    col_dir2 = tmp_path / "Library/Application Support/Anki2/User 2"
    col_dir2.mkdir(parents=True, exist_ok=True)
    f2 = col_dir2 / "collection.anki2"
    f2.write_text("dummy2")

    assert default_collection() == str(f2)


def test_default_collection_not_found(monkeypatch, tmp_path):
    import pytest
    from dump_field import default_collection

    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path))
    with pytest.raises(SystemExit):
        default_collection()


def test_snapshot_collection(tmp_path):
    from dump_field import remove_snapshot, snapshot_collection

    col = tmp_path / "collection.anki2"
    col.write_text("db")
    wal = tmp_path / "collection.anki2-wal"
    wal.write_text("wal")

    snap = snapshot_collection(str(col))
    assert os.path.exists(snap)
    assert open(snap).read() == "db"
    assert os.path.exists(snap + "-wal")
    assert open(snap + "-wal").read() == "wal"
    assert not os.path.exists(snap + "-shm")

    remove_snapshot(snap)
    assert not os.path.exists(snap)
    assert not os.path.exists(snap + "-wal")


def test_dump_no_match(capsys, monkeypatch, tmp_path):
    from dump_field import dump

    col = tmp_path / "collection.anki2"
    with sqlite3.connect(col) as con:
        con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")

    dump(str(col), "missing", False)
    assert "No note matched 'missing'" in capsys.readouterr().out


def test_dump_match_print(capsys, monkeypatch, tmp_path):
    from dump_field import dump

    col = tmp_path / "collection.anki2"
    with sqlite3.connect(col) as con:
        con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
        con.execute("INSERT INTO notes (id, flds) VALUES (?, ?)", (1, "foo\x1fbar"))

    dump(str(col), "foo", False)
    out = capsys.readouterr().out
    assert "=== note 1: 2 fields ===" in out
    assert "--- field 0 (3 chars) ---" in out
    assert "'foo'" in out


def test_dump_match_out_dir(monkeypatch, tmp_path, capsys):
    from dump_field import dump

    col = tmp_path / "collection.anki2"
    with sqlite3.connect(col) as con:
        con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
        con.execute("INSERT INTO notes (id, flds) VALUES (?, ?)", (1, "foo\x1fbar"))

    out_dir = tmp_path / "out"
    dump(str(col), "foo", False, str(out_dir))
    out = capsys.readouterr().out

    assert os.path.exists(out_dir / "1_field0.html")
    assert (out_dir / "1_field0.html").read_text() == "foo"
    assert (out_dir / "1_field1.html").read_text() == "bar"
    assert "-> " in out


def test_main(monkeypatch, tmp_path, capsys):
    from dump_field import main

    col = tmp_path / "collection.anki2"
    with sqlite3.connect(col) as con:
        con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
        con.execute("INSERT INTO notes (id, flds) VALUES (?, ?)", (1, "foo\x1fbar"))

    monkeypatch.setattr("sys.argv", ["dump_field.py", "foo", "--collection", str(col)])
    main()
    out = capsys.readouterr().out
    assert "=== note 1: 2 fields ===" in out
