import contextlib
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from sweep_transform import format_change, load_transform, sweep_notes


def _db():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
    con.executemany(
        "INSERT INTO notes (id, flds) VALUES (?, ?)",
        [
            (1, "front\x1f<div>foo here</div>"),
            (2, "other\x1f<div>nothing to do</div>"),
            (3, "both\x1ffoo<br>and foo again"),
        ],
    )
    return con


def test_sweep_reports_only_changed_notes():
    with contextlib.closing(_db()) as con:
        results = sweep_notes(con, lambda s: s.replace("foo", "bar"))
    assert [nid for nid, _ in results] == [1, 3]
    nid, changes = results[0]
    assert changes[0].idx == 1
    assert changes[0].old == "<div>foo here</div>"
    assert changes[0].new == "<div>bar here</div>"
    assert changes[0].idempotent


def test_sweep_contains_filter_scopes_notes():
    with contextlib.closing(_db()) as con:
        results = sweep_notes(con, lambda s: s.replace("foo", "bar"), contains="again")
    assert [nid for nid, _ in results] == [3]


def test_sweep_flags_non_idempotent_transform():
    with contextlib.closing(_db()) as con:
        results = sweep_notes(con, lambda s: s + "x" if "foo" in s else s)
    assert results
    assert all(not c.idempotent for _, changes in results for c in changes)


def test_sweep_reports_transform_errors_as_findings():
    def boom(s):
        if "foo" in s:
            raise ValueError("bad html")
        return s

    with contextlib.closing(_db()) as con:
        results = sweep_notes(con, boom)
    assert [nid for nid, _ in results] == [1, 3]
    change = results[0][1][0]
    assert change.error and "bad html" in change.error
    assert "transform raised" in format_change(1, change)


def test_format_change_diffs_segments():
    with contextlib.closing(_db()) as con:
        results = sweep_notes(con, lambda s: s.replace("foo", "bar"))
    out = format_change(*[(nid, cs[0]) for nid, cs in results][0])
    assert "-<div>foo here</div>" in out
    assert "+<div>bar here</div>" in out
    assert "NOT IDEMPOTENT" not in out


def test_load_transform_imports_real_addon_function():
    # End-to-end: loads an addon module that imports aqt (mocked by the tool)
    fn = load_transform("auto_mathjax:_convert_dollar_to_mathjax")
    assert fn("$x^2$") == "\\(x^2\\)"


def test_load_transform_invalid_spec():
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        load_transform("invalid_spec")
    assert "Expected 'module:function', got" in str(excinfo.value)


def test_load_transform_missing_function():
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        load_transform("sys:missing_func_name")
    assert "sys has no attribute" in str(excinfo.value)


def test_sweep_notes_exception_in_idempotency_check():
    def transform(s):
        if s == "<div>foo here</div>":
            return "bar"
        if s == "bar":
            raise ValueError("boom")
        return s

    with contextlib.closing(_db()) as con:
        results = sweep_notes(con, transform)

    nid, changes = results[0]
    assert nid == 1
    assert changes[0].idx == 1
    assert not changes[0].idempotent


def test_format_change_not_idempotent():
    from sweep_transform import FieldChange

    change = FieldChange(idx=0, old="old", new="new", idempotent=False)
    out = format_change(1, change)
    assert "NOT IDEMPOTENT: transform(transform(field)) != transform(field)" in out


def test_main(monkeypatch, tmp_path, capsys):
    from sweep_transform import main

    col = tmp_path / "collection.anki2"
    with sqlite3.connect(col) as con:
        con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
        con.execute("INSERT INTO notes (id, flds) VALUES (?, ?)", (1, "foo\x1fbar"))

    monkeypatch.setattr("sweep_transform.snapshot_collection", lambda c: str(col))
    monkeypatch.setattr("sweep_transform.remove_snapshot", lambda c: None)
    monkeypatch.setattr(
        "sys.argv",
        ["sweep_transform.py", "sys:exit", "--collection", str(col)],
    )
    monkeypatch.setattr(
        "sweep_transform.load_transform",
        lambda x: (lambda s: s.replace("foo", "bar")),
    )

    main()
    out = capsys.readouterr().out
    assert "=== note 1, field 0 ===" in out
    assert "-foo" in out
    assert "+bar" in out
    assert "1 notes scanned, 1 would change" in out


def test_main_with_limit(monkeypatch, tmp_path, capsys):
    from sweep_transform import main

    col = tmp_path / "collection.anki2"
    with sqlite3.connect(col) as con:
        con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT)")
        con.execute("INSERT INTO notes (id, flds) VALUES (?, ?)", (1, "foo\x1fbar"))
        con.execute("INSERT INTO notes (id, flds) VALUES (?, ?)", (2, "foo2\x1fbar"))

    monkeypatch.setattr("sweep_transform.snapshot_collection", lambda c: str(col))
    monkeypatch.setattr("sweep_transform.remove_snapshot", lambda c: None)
    monkeypatch.setattr(
        "sys.argv",
        ["sweep_transform.py", "sys:exit", "--collection", str(col), "--limit", "1"],
    )
    monkeypatch.setattr(
        "sweep_transform.load_transform",
        lambda x: (lambda s: s.replace("foo", "bar")),
    )

    main()
    out = capsys.readouterr().out
    assert "... 1 more changed notes not shown (raise --limit)" in out
