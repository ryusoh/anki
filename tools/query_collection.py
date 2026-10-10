"""Run an ad-hoc read-only SQL query against a snapshot of the Anki collection.

Hand-rolling the same preamble (copy collection + WAL sidecars to a temp
file, register a dummy ``unicase`` collation) in every recon script is
error-prone — skip the snapshot and you can wedge Anki's startup lock or
read stale data; skip the collation and SQLite dies with ``no such
collation sequence: unicase`` (see docs/creating-an-addon.md, "Offline
SQLite database queries"). This tool does both, runs one query, and prints
tab-separated rows. The query executes against the throwaway copy, never
the live database.

Usage (from the repo root):

    python3 tools/query_collection.py 'SELECT id, name FROM decks'
    python3 tools/query_collection.py 'SELECT count(*) FROM notes WHERE mid = 42'
    python3 tools/query_collection.py --collection /path/to/collection.anki2 'SELECT 1'

Modern-schema landmarks (25.02): decks and notetypes are their own tables
(the col JSON is gone), deck names use U+001F as the :: separator, note
fields live in notes.flds (U+001F-joined) with notes.csum the sha1[:8-hex]
checksum of the stripped first field.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from dump_field import default_collection, remove_snapshot, snapshot_collection


def connect_snapshot(collection: str) -> tuple:
    """Snapshot the collection and open it with a dummy unicase collation."""
    tmp_path = snapshot_collection(collection)
    con = sqlite3.connect(tmp_path)
    con.create_collation("unicase", lambda x, y: (x > y) - (x < y))
    return con, tmp_path


def run_query(collection: str, sql: str, out=None) -> list:
    """Run `sql` on a snapshot of `collection`; print and return the rows."""
    out = out if out is not None else sys.stdout
    con, tmp_path = connect_snapshot(collection)
    try:
        cur = con.execute(sql)
        rows = cur.fetchall()
        if cur.description:
            print("\t".join(col[0] for col in cur.description), file=out)
        for row in rows:
            print("\t".join("" if value is None else str(value) for value in row), file=out)
        return rows
    finally:
        con.close()
        remove_snapshot(tmp_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("sql", help="SQL to run against the snapshot")
    parser.add_argument(
        "--collection", default=None, help="path to collection.anki2 (default: newest profile)"
    )
    args = parser.parse_args()
    run_query(args.collection or default_collection(), args.sql)


if __name__ == "__main__":
    main()
