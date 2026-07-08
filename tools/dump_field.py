"""Dump the real stored HTML of Anki note fields, straight from the collection.

Addon code that transforms field HTML must be developed against REAL field
bytes, not guesses — Anki fields mix `<br>` lines, leaf-`<div>`-per-line
paste, literal newlines-as-whitespace, and nested rich HTML, and guessing
the format mangles live cards (see docs/creating-an-addon.md, "Field HTML
reality"). This tool prints the exact bytes so a transform can be verified
before it ever runs inside Anki.

Usage (from the repo root):

    python3 tools/dump_field.py 'anguish'                 # front field == text
    python3 tools/dump_field.py --contains 'Raskolnikov'  # any field contains
    python3 tools/dump_field.py 'word' --collection /path/to/collection.anki2

The live collection is locked while Anki runs, so it is copied to a temp
file first; nothing is ever written to the real database.
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import sqlite3
import tempfile

FIELD_SEP = "\x1f"


def split_fields(flds: str) -> list:
    """Anki stores a note's fields as one string joined by U+001F."""
    return flds.split(FIELD_SEP)


def find_notes(con: sqlite3.Connection, text: str, contains: bool = False) -> list:
    """Return (note_id, fields) pairs matching `text`.

    Default: the first (front) field equals `text` exactly.
    With `contains`: any field contains `text`.
    """
    pattern = f"%{text}%"
    rows = con.execute("SELECT id, flds FROM notes WHERE flds LIKE ?", (pattern,)).fetchall()
    result = []
    for nid, flds in rows:
        fields = split_fields(flds)
        if contains or fields[0].strip() == text:
            result.append((nid, fields))
    return result


def default_collection() -> str:
    """The most recently modified collection.anki2 across Anki profiles."""
    home = os.path.expanduser("~")
    candidates = glob.glob(
        os.path.join(home, "Library/Application Support/Anki2/*/collection.anki2")
    )
    if not candidates:
        raise SystemExit("No collection.anki2 found; pass --collection.")
    return max(candidates, key=os.path.getmtime)


def dump(collection: str, text: str, contains: bool) -> None:
    # Copy first: the live database is locked while Anki is running.
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copyfile(collection, tmp_path)
        con = sqlite3.connect(tmp_path)
        try:
            notes = find_notes(con, text, contains)
        finally:
            con.close()
        if not notes:
            print(f"No note matched {text!r} (try --contains).")
            return
        for nid, fields in notes:
            print(f"=== note {nid}: {len(fields)} fields ===")
            for i, field in enumerate(fields):
                print(f"--- field {i} ({len(field)} chars) ---")
                print(repr(field))
    finally:
        os.unlink(tmp_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("text", help="front-field text (or substring with --contains)")
    parser.add_argument(
        "--contains", action="store_true", help="match any field containing the text"
    )
    parser.add_argument(
        "--collection", default=None, help="path to collection.anki2 (default: newest profile)"
    )
    args = parser.parse_args()
    dump(args.collection or default_collection(), args.text, args.contains)


if __name__ == "__main__":
    main()
