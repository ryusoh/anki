import gzip
import json
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

# Load the extensionless fetch script as a module.
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
fetch = SourceFileLoader("fetch", str(SCRIPT_DIR.parent / "fetch")).load_module()


def _make_review(review_id, cid=1):
    """Return a minimal review dict; id is milliseconds since epoch."""
    return {'id': review_id, 'cid': cid, 'ease': 3, 'ivl': 1,
            'lastIvl': 0, 'factor': 0, 'time': 0, 'type': 0}


def test_partitioned_reviews_are_staged():
    """Reviews in two months create two monthly files, no monolith."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = Path(tmpdir) / "collection"
        collection_dir.mkdir(parents=True)

        # January and February 2021
        jan_id = int(1609459200000)  # 2021-01-01 00:00:00 UTC
        feb_id = int(1612137600000)  # 2021-02-01 00:00:00 UTC
        data = {
            'reviews': [
                _make_review(jan_id, cid=1),
                _make_review(jan_id + 86400000, cid=2),
                _make_review(feb_id, cid=3),
            ],
            'cards': [],
            'decks': {},
            'notetypes': [],
        }

        changed_files, collection_hashes = fetch._stage_collection_files(
            data, [], collection_dir, {}, verbose=False
        )

        assert (collection_dir / "reviews" / "2021-01.json.gz").exists()
        assert (collection_dir / "reviews" / "2021-02.json.gz").exists()
        assert not (collection_dir / "reviews.json.gz").exists()

        with gzip.open(collection_dir / "reviews" / "2021-01.json.gz", 'rt', encoding='utf-8') as f:
            assert len(json.load(f)) == 2
        with gzip.open(collection_dir / "reviews" / "2021-02.json.gz", 'rt', encoding='utf-8') as f:
            assert len(json.load(f)) == 1

        assert "collection/reviews/2021-01.json.gz" in collection_hashes
        assert "collection/reviews/2021-02.json.gz" in collection_hashes
        assert "collection/reviews.json.gz" not in collection_hashes

        assert "collection/reviews/2021-01.json.gz" in changed_files
        assert "collection/reviews/2021-02.json.gz" in changed_files
        assert "collection/reviews.json.gz" not in changed_files


def test_only_changed_month_is_re_staged():
    """Pre-seeding one month hash and changing the other uploads only the other."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = Path(tmpdir) / "collection"
        collection_dir.mkdir(parents=True)

        jan_id = int(1609459200000)
        feb_id = int(1612137600000)
        reviews = [
            _make_review(jan_id, cid=1),
            _make_review(feb_id, cid=2),
        ]

        # First staging to populate files and capture hashes
        _, hashes = fetch._stage_collection_files(
            {'reviews': reviews, 'cards': [], 'decks': {}, 'notetypes': []},
            [], collection_dir, {}, verbose=False
        )

        old_hash_map = {
            "collection/reviews/2021-01.json.gz": hashes["collection/reviews/2021-01.json.gz"],
        }

        # Modify only February review
        changed_reviews = [
            _make_review(jan_id, cid=1),
            _make_review(feb_id, cid=99),
        ]

        changed_files, collection_hashes = fetch._stage_collection_files(
            {'reviews': changed_reviews, 'cards': [], 'decks': {}, 'notetypes': []},
            [], collection_dir, old_hash_map, verbose=False
        )

        assert "collection/reviews/2021-02.json.gz" in changed_files
        assert "collection/reviews/2021-01.json.gz" not in changed_files
        assert "collection/reviews.json.gz" not in changed_files
        assert "collection/reviews/2021-01.json.gz" in collection_hashes
        assert "collection/reviews/2021-02.json.gz" in collection_hashes


def test_empty_reviews_creates_no_monthly_files():
    """An empty review list leaves the reviews directory empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = Path(tmpdir) / "collection"
        collection_dir.mkdir(parents=True)

        changed_files, collection_hashes = fetch._stage_collection_files(
            {'reviews': [], 'cards': [], 'decks': {}, 'notetypes': []},
            [], collection_dir, {}, verbose=False
        )

        reviews_dir = collection_dir / "reviews"
        assert reviews_dir.exists()
        assert list(reviews_dir.glob("*.json.gz")) == []
        assert "collection/reviews.json.gz" not in collection_hashes
        assert not any(k.startswith("collection/reviews/") for k in collection_hashes)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, '-v']))
