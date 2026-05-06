import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Change directory and add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib.util
spec = importlib.util.spec_from_file_location("generate_custom_stats", str(Path(__file__).parent.parent / "generate_custom_stats.py"))
generate_custom_stats = importlib.util.module_from_spec(spec)
sys.modules["generate_custom_stats"] = generate_custom_stats
spec.loader.exec_module(generate_custom_stats)

def test_generate_custom_stats_main():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        output_file = temp_path / "custom_stats_data.json"
        cards_file = temp_path / "cards.json.gz"

        # Test 1: Files don't exist -> return False
        with patch('generate_custom_stats.OUTPUT_FILE', output_file), \
             patch('generate_custom_stats.CARDS_FILE', cards_file):
            assert generate_custom_stats.main() == False

        # Test 2: Invalid JSON
        import gzip
        with gzip.open(cards_file, 'wt') as f:
            f.write("invalid json")
        with patch('generate_custom_stats.OUTPUT_FILE', output_file), \
             patch('generate_custom_stats.CARDS_FILE', cards_file):
            with pytest.raises(json.decoder.JSONDecodeError):
                generate_custom_stats.main()

        # Test 4: Success
        cards_data = [
            {"id": 1, "ivl": 21, "type": 2, "queue": 2, "due": 100, "deck_name": "Default"},
            {"id": 2, "ivl": 10, "type": 2, "queue": 2, "due": 100, "deck_name": "Default"},
            {"id": 3, "ivl": 0, "type": 0, "queue": 1},
        ]
        with gzip.open(cards_file, 'wt') as f:
            json.dump(cards_data, f)

        with patch('generate_custom_stats.OUTPUT_FILE', output_file), \
             patch('generate_custom_stats.CARDS_FILE', cards_file), \
             patch('generate_custom_stats.get_anki_today', return_value=90), \
             patch('generate_custom_stats.SCRIPT_DIR', temp_path):
            assert generate_custom_stats.main() == True
            assert output_file.exists()
            assert (temp_path / "full_forecast.json.gz").exists()

            # Second run, full forecast unchanged
            assert generate_custom_stats.main() == True

def test_calculate_future_due():
    cards_data = [
        # due today (0) -> bucket 0
        {"id": 1, "queue": 2, "ivl": 25, "due": 100},
        {"id": 2, "queue": 2, "ivl": 5, "due": 100},

        # due tomorrow (1) -> bucket 1
        {"id": 3, "queue": 2, "ivl": 21, "due": 101},

        # overdue (-1) -> ignored
        {"id": 4, "queue": 2, "ivl": 30, "due": 99},

        # not review -> ignored
        {"id": 5, "queue": 1, "ivl": 30, "due": 105},

        # missing properties -> defaults -> ignored because due=0, today=100 -> negative
        {"id": 6},
    ]

    cid_to_deck = {1: "DeckA", 2: "DeckB", 3: "DeckA", 4: "DeckB"}

    global_stats, deck_stats = generate_custom_stats.calculate_future_due(cards_data, cid_to_deck, anki_today=100)

    assert len(global_stats) == 2  # buckets 0 and 1

    # Bucket 0: 1 mature, 1 young
    assert global_stats[0]["mature"] == 1
    assert global_stats[0]["young"] == 1

    # Bucket 1: 1 mature, 0 young
    assert global_stats[1]["mature"] == 1
    assert global_stats[1]["young"] == 0

    # Deck stats
    assert len(deck_stats["DeckA"]) == 2  # Has cards in day 0 and 1
    assert deck_stats["DeckA"][0]["mature"] == 1
    assert deck_stats["DeckA"][1]["mature"] == 1

    assert len(deck_stats["DeckB"]) == 1  # Has card only in day 0
    assert deck_stats["DeckB"][0]["young"] == 1

def test_read_existing_total():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        output_file = temp_path / "output.json"

        # Missing file
        assert generate_custom_stats._read_existing_total(output_file) == 0

        # Valid file
        with open(output_file, "w") as f:
            json.dump({"futureDue": [{"mature": 10, "young": 5}, {"mature": 20, "young": 15}]}, f)
        assert generate_custom_stats._read_existing_total(output_file) == 50

        # Invalid file
        with open(output_file, "w") as f:
            f.write("invalid")
        assert generate_custom_stats._read_existing_total(output_file) == 0

def test_should_write():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        output_file = temp_path / "output.json"

        new_stats = [{"mature": 50, "young": 50}] # Total 100

        # No old file -> Write
        assert generate_custom_stats._should_write(new_stats, output_file) == True

        # Write valid old file smaller
        with open(output_file, "w") as f:
            json.dump({"futureDue": [{"mature": 5, "young": 5}]}, f)
        assert generate_custom_stats._should_write(new_stats, output_file) == True

        # Old file large, new empty -> Don't write
        assert generate_custom_stats._should_write([], output_file) == False

        # Old file large (200), new tiny (10) -> Don't write
        with open(output_file, "w") as f:
            json.dump({"futureDue": [{"mature": 100, "young": 100}]}, f)
        assert generate_custom_stats._should_write([{"mature": 5, "young": 5}], output_file) == False

def test_get_anki_today_with_db():
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as f:
        db_path = f.name

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE col (crt INTEGER)")

        # Set creation time to Jan 1, 2021 (timestamp 1609459200)
        c.execute("INSERT INTO col VALUES (1609459200)")
        conn.commit()
        conn.close()

        with patch('generate_custom_stats.find_anki_collection', return_value=Path(db_path)):
            # We don't assert a specific value since it depends on the current date
            today = generate_custom_stats.get_anki_today()
            assert today > 0

    finally:
        os.unlink(db_path)

def test_get_anki_today_db_error():
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as f:
        db_path = f.name

    try:
        with patch('generate_custom_stats.find_anki_collection', return_value=Path(db_path)):
            # Empty file, will cause sqlite error
            today = generate_custom_stats.get_anki_today()
            assert today > 6000 # Fallback 2007 logic

    finally:
        os.unlink(db_path)

def test_find_anki_collection_mocked():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        profile_dir = temp_path / "Profile 1"
        profile_dir.mkdir()
        db_file = profile_dir / "collection.anki2"
        db_file.touch()

        # Override Anki2 folder location through patch
        with patch('pathlib.Path.home') as mock_home:
            mock_home_path = MagicMock()
            mock_home.return_value = mock_home_path

            # Setup path traversal: Path.home() / "Library" / "Application Support" / "Anki2"
            mock_lib = MagicMock()
            mock_app_support = MagicMock()
            mock_anki2 = MagicMock()

            mock_home_path.__truediv__.return_value = mock_lib
            mock_lib.__truediv__.return_value = mock_app_support
            mock_app_support.__truediv__.return_value = mock_anki2

            mock_anki2.iterdir.return_value = [profile_dir]

            assert generate_custom_stats.find_anki_collection() == db_file

def test_build_cid_to_deck_prefers_decks_json():
    """When decks.json has current names, use them via did instead of stale deck_name."""
    cards = [
        {"id": 1, "did": 100, "deck_name": "金融\x1f産研"},
        {"id": 2, "did": 100, "deck_name": "金融\x1f産研"},
        {"id": 3, "did": 200, "deck_name": "金融\x1f理論"},
        {"id": 4, "did": 300, "deck_name": "言語\x1f英語"},
    ]
    # decks.json: merged sub-decks into "金融", 言語::英語 unchanged
    decks_map = {
        100: "金融",
        200: "金融",
        300: "言語\x1f英語",
    }
    result = generate_custom_stats.build_cid_to_deck(cards, decks_map)
    assert result[1] == "金融"
    assert result[2] == "金融"
    assert result[3] == "金融"
    assert result[4] == "言語::英語"


def test_build_cid_to_deck_falls_back_to_deck_name():
    """When decks_map is empty or missing did, fall back to deck_name."""
    cards = [
        {"id": 1, "did": 100, "deck_name": "言語\x1f英語"},
        {"id": 2, "deck_name": "Default"},  # no did
    ]
    result = generate_custom_stats.build_cid_to_deck(cards, {})
    assert result[1] == "言語::英語"
    assert result[2] == "Default"


def test_build_cid_to_deck_no_decks_map():
    """When decks_map is None, use deck_name from cards."""
    cards = [
        {"id": 1, "did": 100, "deck_name": "言語\x1f英語"},
    ]
    result = generate_custom_stats.build_cid_to_deck(cards, None)
    assert result[1] == "言語::英語"


def test_main_uses_decks_json_for_deck_names():
    """Integration: main() should load decks.json and use did-based resolution."""
    import gzip
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        output_file = temp_path / "custom_stats_data.json"
        cards_file = temp_path / "cards.json.gz"

        # Cards with stale deck_name but correct did
        cards_data = [
            {"id": 1, "did": 100, "ivl": 21, "type": 2, "queue": 2, "due": 100, "deck_name": "金融\x1f産研"},
            {"id": 2, "did": 100, "ivl": 10, "type": 2, "queue": 2, "due": 100, "deck_name": "金融\x1f理論"},
        ]
        with gzip.open(cards_file, 'wt') as f:
            json.dump(cards_data, f)

        # decks.json with current merged name
        decks_file = temp_path / "decks.json"
        with open(decks_file, 'w') as f:
            json.dump({"100": "金融"}, f)

        with patch('generate_custom_stats.OUTPUT_FILE', output_file), \
             patch('generate_custom_stats.CARDS_FILE', cards_file), \
             patch('generate_custom_stats.DECKS_FILE', decks_file), \
             patch('generate_custom_stats.get_anki_today', return_value=90), \
             patch('generate_custom_stats.SCRIPT_DIR', temp_path):
            assert generate_custom_stats.main() == True

            with open(output_file) as f:
                data = json.load(f)
            by_deck = data["futureDueByDeck"]
            # Should have single "金融" deck, not "金融::産研" and "金融::理論"
            assert "金融" in by_deck
            assert "金融::産研" not in by_deck
            assert "金融::理論" not in by_deck


def test_find_anki_collection_not_found():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        profile_dir = temp_path / "Profile 1"
        profile_dir.mkdir()
        # No db file

        with patch('pathlib.Path.home') as mock_home:
            mock_home_path = MagicMock()
            mock_home.return_value = mock_home_path

            mock_lib = MagicMock()
            mock_app_support = MagicMock()
            mock_anki2 = MagicMock()

            mock_home_path.__truediv__.return_value = mock_lib
            mock_lib.__truediv__.return_value = mock_app_support
            mock_app_support.__truediv__.return_value = mock_anki2

            mock_anki2.iterdir.return_value = [profile_dir]

            assert generate_custom_stats.find_anki_collection() is None
