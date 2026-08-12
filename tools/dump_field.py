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
    python3 tools/dump_field.py --contains 'x' --out /tmp/fields  # full bytes

The live collection is locked while Anki runs, so it is copied to a temp
file first (WAL sidecars included, so recent writes are visible); nothing
is ever written to the real database. Long fields truncate in terminal
output — use --out to write full field bytes to files instead.
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


def snapshot_collection(collection: str) -> str:
    """Copy the collection (and its WAL sidecars) to a temp file.

    Reading the live file directly — even read-only — can hit "database is
    locked" while Anki runs, and a long-held connection can coincide with
    Anki's startup lock. Copying only the main file is not enough either:
    with Anki open, recent writes sit in the -wal sidecar, so a main-file-
    only copy silently reads a stale snapshot.
    """
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as tmp:
        tmp_path = tmp.name
    shutil.copyfile(collection, tmp_path)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(collection + suffix):
            shutil.copyfile(collection + suffix, tmp_path + suffix)
    return tmp_path


def remove_snapshot(tmp_path: str) -> None:
    """Delete a snapshot and any copied WAL sidecars."""
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(tmp_path + suffix):
            os.unlink(tmp_path + suffix)


def dump(collection: str, text: str, contains: bool, out: str | None = None) -> None:
    tmp_path = snapshot_collection(collection)
    try:
        con = sqlite3.connect(tmp_path)
        try:
            notes = find_notes(con, text, contains)
        finally:
            con.close()
        if not notes:
            print(f"No note matched {text!r} (try --contains).")
            return
        if out is not None:
            os.makedirs(out, exist_ok=True)
        for nid, fields in notes:
            print(f"=== note {nid}: {len(fields)} fields ===")
            for i, field in enumerate(fields):
                if out is not None:
                    path = os.path.join(out, f"{nid}_field{i}.html")
                    with open(path, "w") as f:
                        f.write(field)
                    print(f"--- field {i} ({len(field)} chars) -> {path}")
                else:
                    print(f"--- field {i} ({len(field)} chars) ---")
                    print(repr(field))
    finally:
        remove_snapshot(tmp_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("text", help="front-field text (or substring with --contains)")
    parser.add_argument(
        "--contains", action="store_true", help="match any field containing the text"
    )
    parser.add_argument(
        "--collection", default=None, help="path to collection.anki2 (default: newest profile)"
    )
    parser.add_argument(
        "--out",
        default=None,
        metavar="DIR",
        help="write full field bytes to DIR/<note_id>_field<N>.html (for long fields)",
    )
    args = parser.parse_args()
    dump(args.collection or default_collection(), args.text, args.contains, args.out)


if __name__ == "__main__":
    main()
