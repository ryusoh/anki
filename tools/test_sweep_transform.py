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
