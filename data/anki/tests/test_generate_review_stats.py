import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
from datetime import datetime

# Change directory and add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib.util
spec = importlib.util.spec_from_file_location("generate_review_stats", str(Path(__file__).parent.parent / "generate_review_stats.py"))
generate_review_stats = importlib.util.module_from_spec(spec)
sys.modules["generate_review_stats"] = generate_review_stats
spec.loader.exec_module(generate_review_stats)

def test_generate_review_stats_empty():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        reviews_dir = temp_path / "reviews"
        reviews_dir.mkdir()

        # Test with no files
        with patch('generate_review_stats.REVIEWS_DIR', reviews_dir):
            with patch('generate_review_stats.OUTPUT_FILE', temp_path / "output.json"):
                # No reviews should return False
                assert generate_review_stats.main() == False
                assert not (temp_path / "output.json").exists()

def test_aggregate_reviews():
    # Write some sample data to a gzip file
    import gzip

    review_data = [
        # Mature, good
        {"id": 1609459200000, "cid": 1, "type": 1, "lastIvl": 21, "ivl": 30, "ease": 3, "time": 1000},
        # Young, easy
        {"id": 1609459200000 + 86400000, "cid": 1, "type": 1, "lastIvl": 1, "ivl": 3, "ease": 4, "time": 2000},
        # Learn, again
        {"id": 1609459200000 + 86400000*25, "cid": 1, "type": 0, "lastIvl": 0, "ivl": 0, "ease": 1, "time": 3000},
        # Relearn, hard
        {"id": 1609459200000 + 86400000*26, "cid": 1, "type": 2, "lastIvl": 30, "ivl": 10, "ease": 2, "time": 4000},
        # Filtered, good
        {"id": 1609459200000 + 86400000*27, "cid": 2, "type": 3, "lastIvl": 0, "ivl": 0, "ease": 3, "time": 5000},
    ]

    cards_data = [
        {"id": 1, "deck_name": "Default\x1fSubdeck"},
        # No cid 2 to test "Unknown"
    ]

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)

        reviews_dir = temp_path / "reviews"
        reviews_dir.mkdir()

        # Save reviews
        file_path = reviews_dir / "2021-01.json.gz"
        with gzip.open(file_path, 'wt') as f:
            json.dump(review_data, f)

        # Save cards map
        cards_file = temp_path / "cards.json.gz"
        with gzip.open(cards_file, 'wt') as f:
            json.dump(cards_data, f)

        with patch('generate_review_stats.REVIEWS_DIR', reviews_dir):
            with patch('generate_review_stats.CARDS_FILE', cards_file):
                global_stats, deck_stats = generate_review_stats.aggregate_reviews()

                assert global_stats is not None
                assert len(global_stats) == 5

                assert "Default::Subdeck" in deck_stats
                assert "Unknown" in deck_stats

                assert len(deck_stats["Default::Subdeck"]) == 4
                assert len(deck_stats["Unknown"]) == 1

def test_aggregate_reviews_no_cards_file():
    import gzip
    review_data = [{"id": 1609459200000, "cid": 1, "type": 1, "lastIvl": 21, "ivl": 30, "ease": 3, "time": 1000}]

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        reviews_dir = temp_path / "reviews"
        reviews_dir.mkdir()

        with gzip.open(reviews_dir / "2021-01.json.gz", 'wt') as f:
            json.dump(review_data, f)

        cards_file = temp_path / "cards.json.gz" # does not exist

        with patch('generate_review_stats.REVIEWS_DIR', reviews_dir):
            with patch('generate_review_stats.CARDS_FILE', cards_file):
                global_stats, deck_stats = generate_review_stats.aggregate_reviews()

                assert "Unknown" in deck_stats
                assert len(deck_stats["Unknown"]) == 1

def test_read_existing_review_total():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        output_file = temp_path / "output.json"

        # Empty missing file
        assert generate_review_stats._read_existing_review_total(output_file) == 0

        # Valid file
        with open(output_file, "w") as f:
            json.dump({"reviews": [{"count": 10}, {"count": 5}]}, f)
        assert generate_review_stats._read_existing_review_total(output_file) == 15

        # Invalid file
        with open(output_file, "w") as f:
            f.write("invalid json")
        assert generate_review_stats._read_existing_review_total(output_file) == 0

def test_should_write_reviews():
    new_reviews = [{"count": 10}, {"count": 10}] # Total 20

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        output_file = temp_path / "output.json"

        # No old file -> Write
        assert generate_review_stats._should_write_reviews(new_reviews, output_file) == True

        # Valid old file smaller -> Write
        with open(output_file, "w") as f:
            json.dump({"reviews": [{"count": 10}]}, f)
        assert generate_review_stats._should_write_reviews(new_reviews, output_file) == True

        # Old file large, new file empty -> Don't write
        assert generate_review_stats._should_write_reviews([], output_file) == False

        # Old file large (200), new file tiny (10) -> Don't write
        with open(output_file, "w") as f:
            json.dump({"reviews": [{"count": 200}]}, f)
        assert generate_review_stats._should_write_reviews([{"count": 10}], output_file) == False

def test_main_full_workflow():
    import gzip
    review_data = [{"id": 1609459200000, "cid": 1, "type": 1, "lastIvl": 21, "ivl": 30, "ease": 3, "time": 1000, "retention": 1}]

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        reviews_dir = temp_path / "reviews"
        reviews_dir.mkdir()
        output_file = temp_path / "output.json"

        with gzip.open(reviews_dir / "2021-01.json.gz", 'wt') as f:
            json.dump(review_data, f)

        with patch('generate_review_stats.REVIEWS_DIR', reviews_dir), \
             patch('generate_review_stats.OUTPUT_FILE', output_file), \
             patch('generate_review_stats.CARDS_FILE', temp_path / "cards.json.gz"):

            assert generate_review_stats.main() == True
            assert output_file.exists()

            with open(output_file) as f:
                data = json.load(f)
                assert len(data["reviews"]) == 1

def test_main_fail_open():
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        reviews_dir = temp_path / "reviews"
        reviews_dir.mkdir()
        output_file = temp_path / "output.json"

        # Create valid old file
        with open(output_file, "w") as f:
            json.dump({"reviews": [{"count": 100}]}, f)

        # Test 1: No new reviews
        with patch('generate_review_stats.REVIEWS_DIR', reviews_dir), \
             patch('generate_review_stats.OUTPUT_FILE', output_file):
            assert generate_review_stats.main() == True # True because fail open

        # Test 2: Suspiciously small reviews (1 review)
        import gzip
        with gzip.open(reviews_dir / "2021-01.json.gz", 'wt') as f:
            json.dump([{"id": 1609459200000, "cid": 1, "type": 1, "lastIvl": 21, "ivl": 30, "ease": 3, "time": 1000}], f)

        with patch('generate_review_stats.REVIEWS_DIR', reviews_dir), \
             patch('generate_review_stats.OUTPUT_FILE', output_file), \
             patch('generate_review_stats.CARDS_FILE', temp_path / "cards.json.gz"):
            assert generate_review_stats.main() == True
