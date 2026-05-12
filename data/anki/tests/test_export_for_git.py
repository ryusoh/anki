import pytest
import sqlite3
import tempfile
import json
import gzip
from pathlib import Path
from unittest.mock import patch

from data.anki.export_for_git import fetch_and_anonymize, export_for_git

def setup_mock_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("CREATE TABLE cards (id INTEGER, nid INTEGER, did INTEGER, ord INTEGER, type INTEGER, queue INTEGER, due INTEGER, ivl INTEGER, factor INTEGER, reps INTEGER, lapses INTEGER, flags INTEGER)")
    cur.execute("CREATE TABLE revlog (id INTEGER, cid INTEGER, ease INTEGER, ivl INTEGER, lastIvl INTEGER, factor INTEGER, time INTEGER, type INTEGER)")
    cur.execute("CREATE TABLE decks (id INTEGER, name TEXT)")
    cur.execute("CREATE TABLE notetypes (id INTEGER, name TEXT)")
    cur.execute("CREATE TABLE notes (id INTEGER, mid INTEGER, mod INTEGER, usn INTEGER, sfld TEXT, csum INTEGER, flags INTEGER)")

    # Insert some dummy data
    cur.execute("INSERT INTO decks VALUES (1, 'Default')")
    cur.execute("INSERT INTO notetypes VALUES (1, 'Basic')")
    cur.execute("INSERT INTO cards VALUES (1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0)")
    cur.execute("INSERT INTO revlog VALUES (1609459200000, 1, 3, 1, 0, 0, 1000, 1)") # 2021-01-01
    cur.execute("INSERT INTO notes VALUES (1, 1, 0, 0, 'dummy', 0, 0)")

    conn.commit()
    conn.close()

def test_fetch_and_anonymize():
    with tempfile.TemporaryDirectory() as tempdir:
        db_path = Path(tempdir) / "collection.anki2"
        setup_mock_db(db_path)

        data = fetch_and_anonymize(db_path)

        assert len(data['cards']) == 1
        assert len(data['reviews']) == 1
        assert len(data['decks']) == 1
        assert len(data['notetypes']) == 1
        assert len(data['notes']) == 1

        assert data['decks'][1] == 'Default'

def test_export_for_git():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        db_path = temp_path / "collection.anki2"
        setup_mock_db(db_path)

        with patch('data.anki.export_for_git.SOURCE_DB', db_path), \
             patch('data.anki.export_for_git.OUTPUT_DIR', temp_path):
            export_for_git()

        # Check files are created
        assert (temp_path / "cards.json.gz").exists()
        assert (temp_path / "decks.json").exists()
        assert (temp_path / "reviews" / "2021-01.json.gz").exists()

        # Check content
        with open(temp_path / "decks.json") as f:
            decks = json.load(f)
            assert decks["1"] == "Default"

        with gzip.open(temp_path / "cards.json.gz", "rt") as f:
            cards = json.load(f)
            assert len(cards) == 1

        with gzip.open(temp_path / "reviews" / "2021-01.json.gz", "rt") as f:
            reviews = json.load(f)
            assert len(reviews) == 1
