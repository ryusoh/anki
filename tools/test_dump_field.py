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
    notes = find_notes(_db(), "anguish")
    assert [nid for nid, _ in notes] == [1]
    assert notes[0][1][1] == "<div><i>severe pain</i></div>"


def test_find_notes_contains_matches_any_field():
    notes = find_notes(_db(), "anguish", contains=True)
    assert [nid for nid, _ in notes] == [1, 2, 3]
