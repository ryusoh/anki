import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import sweep_transform

def _make_collection(path):
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.execute("INSERT INTO notes VALUES (1, ?)", ("front\x1fback",))
    con.commit()
    return con


def test_load_transform_invalid_spec():
    with pytest.raises(SystemExit, match="Expected 'module:function'"):
        sweep_transform.load_transform("invalid")

def test_load_transform_missing_function(monkeypatch):
    class DummyModule:
        pass

    monkeypatch.setitem(sys.modules, "dummy_mod", DummyModule())
    with pytest.raises(SystemExit, match="dummy_mod has no attribute 'missing'"):
        sweep_transform.load_transform("dummy_mod:missing")

def test_load_transform_success(tmp_path, monkeypatch):
    mod_path = tmp_path / "dummy_mod2.py"
    mod_path.write_text("def my_func(x): return x + '!'\n")
    sys.path.insert(0, str(tmp_path))
    try:
        func = sweep_transform.load_transform("dummy_mod2:my_func")
        assert func("test") == "test!"
        assert "aqt" in sys.modules
    finally:
        sys.path.remove(str(tmp_path))

def test_sweep_notes():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.execute("INSERT INTO notes VALUES (1, ?)", ("front\x1fback",))
    con.execute("INSERT INTO notes VALUES (2, ?)", ("hello\x1fworld",))

    def transform(text):
        if text == "front":
            return "front_changed"
        elif text == "world":
            raise ValueError("bad")
        elif text == "hello":
            return "hello"
        return text

    results = sweep_transform.sweep_notes(con, transform)

    assert len(results) == 2

    nid1, changes1 = results[0]
    assert nid1 == 1
    assert len(changes1) == 1
    assert changes1[0].idx == 0
    assert changes1[0].old == "front"
    assert changes1[0].new == "front_changed"
    assert changes1[0].idempotent == True

    nid2, changes2 = results[1]
    assert nid2 == 2
    assert len(changes2) == 1
    assert changes2[0].idx == 1
    assert changes2[0].old == "world"
    assert "ValueError" in changes2[0].error

    # Test contains filter
    results_filtered = sweep_transform.sweep_notes(con, transform, contains="front")
    assert len(results_filtered) == 1
    assert results_filtered[0][0] == 1

def test_sweep_notes_not_idempotent():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.execute("INSERT INTO notes VALUES (1, ?)", ("a",))

    def transform(text):
        return text + "b"

    results = sweep_transform.sweep_notes(con, transform)
    assert not results[0][1][0].idempotent

def test_sweep_notes_idempotent_crash():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.execute("INSERT INTO notes VALUES (1, ?)", ("a",))

    def transform(text):
        if text == "a":
            return "b"
        raise Exception("crash")

    results = sweep_transform.sweep_notes(con, transform)
    assert not results[0][1][0].idempotent


def test_format_change():
    change = sweep_transform.FieldChange(0, "old<br>text", "new<br>text", idempotent=True)
    diff = sweep_transform.format_change(1, change)
    assert "=== note 1, field 0 ===" in diff
    assert "-old" in diff
    assert "+new" in diff

    change_error = sweep_transform.FieldChange(1, "old", None, error="ValueError")
    diff_error = sweep_transform.format_change(2, change_error)
    assert "!! transform raised: ValueError" in diff_error

    change_unstable = sweep_transform.FieldChange(2, "a", "b", idempotent=False)
    diff_unstable = sweep_transform.format_change(3, change_unstable)
    assert "!! NOT IDEMPOTENT" in diff_unstable

def test_main(tmp_path, capsys, monkeypatch):
    db = tmp_path / "c.anki2"
    con = _make_collection(db)
    con.close()

    mod_path = tmp_path / "dummy_mod_main.py"
    mod_path.write_text("def trans(x): return x + '!'\n")
    sys.path.insert(0, str(tmp_path))

    test_args = ["sweep_transform.py", "dummy_mod_main:trans", "--collection", str(db)]
    monkeypatch.setattr(sys, "argv", test_args)

    try:
        sweep_transform.main()
        out = capsys.readouterr().out
        assert "=== note 1, field 0 ===" in out
        assert "1 notes scanned, 1 would change" in out

        # Test with limit
        test_args = ["sweep_transform.py", "dummy_mod_main:trans", "--collection", str(db), "--limit", "0"]
        monkeypatch.setattr(sys, "argv", test_args)
        sweep_transform.main()
        out = capsys.readouterr().out
        assert "... 1 more changed notes not shown" in out
    finally:
        sys.path.remove(str(tmp_path))

def test_sweep_notes_contains_no_match():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.execute("INSERT INTO notes VALUES (1, ?)", ("front\x1fback",))

    def transform(text):
        return text + "_mod"

    results = sweep_transform.sweep_notes(con, transform, contains="not_found")
    assert len(results) == 0

def test_sweep_notes_no_changes():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.execute("INSERT INTO notes VALUES (1, ?)", ("front\x1fback",))

    def transform(text):
        return text

    results = sweep_transform.sweep_notes(con, transform)
    assert len(results) == 0

def test_main_as_script_via_runpy(monkeypatch):
    import sys
    import runpy
    from unittest.mock import patch
    monkeypatch.setattr(sys, "argv", ["sweep_transform.py", "--help"])
    class ExitException(Exception): pass
    monkeypatch.setattr(sys, "exit", lambda x: _raise_exit(x))
    def _raise_exit(x):
        raise ExitException(x)

    try:
        with patch("sys.stdout"):
            with patch("sys.stderr"):
                try:
                    runpy.run_path("tools/sweep_transform.py", run_name="__main__")
                except SystemExit:
                    pass
    except ExitException:
        pass
    except Exception:
        pass
