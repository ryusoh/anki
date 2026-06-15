"""Tests for the fail-open mechanism in generate_custom_stats.py and
generate_review_stats.py.

Ensures that stale/broken data generation does not overwrite valid old data.
"""

import json
import sys
from pathlib import Path

# Add parent to sys.path so we can import the modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_custom_stats import _read_existing_total, _should_write
from generate_review_stats import _read_existing_review_total, _should_write_reviews

# =====================================================================
# Helpers
# =====================================================================


def _make_stats(mature_vals, young_vals=None):
    """Helper: build a futureDue list from mature/young value lists."""
    if young_vals is None:
        young_vals = [0] * len(mature_vals)
    return [
        {"day": i, "mature": m, "young": y}
        for i, (m, y) in enumerate(zip(mature_vals, young_vals))
    ]


def _write_json(path, stats):
    """Helper: write a futureDue JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"futureDue": stats}, indent=2), encoding="utf-8")


def _make_review_entries(counts):
    """Helper: build a reviews list from count values."""
    return [
        {
            "date": f"2026-01-{i + 1:02d}",
            "count": c,
            "time": c * 10,
            "mature": 0,
            "young": 0,
            "again": 0,
            "hard": 0,
            "good": c,
            "easy": 0,
            "learn": 0,
            "review": c,
            "relearn": 0,
            "filtered": 0,
            "retention": 0.9,
        }
        for i, c in enumerate(counts)
    ]


def _write_review_json(path, reviews):
    """Helper: write a reviews JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"reviews": reviews}, indent=2), encoding="utf-8")


# =====================================================================
# _read_existing_total (futureDue)
# =====================================================================


def test_read_total_missing_file(tmp_path):
    assert _read_existing_total(tmp_path / "nope.json") == 0


def test_read_total_corrupt_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json at all", encoding="utf-8")
    assert _read_existing_total(bad) == 0


def test_read_total_valid(tmp_path):
    f = tmp_path / "stats.json"
    _write_json(f, _make_stats([10, 20], [3, 5]))  # total = 38
    assert _read_existing_total(f) == 38


def test_read_total_empty_array(tmp_path):
    f = tmp_path / "empty.json"
    _write_json(f, [])
    assert _read_existing_total(f) == 0


def test_read_total_missing_key(tmp_path):
    """JSON file without 'futureDue' key → treats as 0."""
    f = tmp_path / "nokey.json"
    f.write_text(json.dumps({"other": 123}), encoding="utf-8")
    assert _read_existing_total(f) == 0


def test_read_total_partial_entries(tmp_path):
    """Entries with missing mature/young keys → defaults to 0."""
    f = tmp_path / "partial.json"
    f.write_text(
        json.dumps({"futureDue": [{"day": 0}, {"day": 1, "mature": 5}]}),
        encoding="utf-8",
    )
    assert _read_existing_total(f) == 5


# =====================================================================
# _should_write (futureDue)
# =====================================================================


def test_should_write_no_old_file(tmp_path):
    """No old file → always write, even if new data is empty."""
    assert _should_write(_make_stats([0, 0, 0]), tmp_path / "absent.json") is True


def test_should_write_no_old_file_empty_list(tmp_path):
    """No old file + empty new list → still write."""
    assert _should_write([], tmp_path / "absent.json") is True


def test_should_write_old_empty(tmp_path):
    """Old file has zero total → always write."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([0, 0, 0]))
    assert _should_write(_make_stats([5, 10]), old) is True


def test_should_write_normal_update(tmp_path):
    """New data is comparable to old → allow write."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([100, 100], [50, 50]))  # total = 300
    assert _should_write(_make_stats([110, 90], [45, 55]), old) is True  # total = 300


def test_should_write_new_larger_than_old(tmp_path):
    """New data is significantly larger → allow write."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([50, 50]))  # total = 100
    assert _should_write(_make_stats([500, 500], [200, 200]), old) is True  # total = 1400


def test_should_write_blocks_empty_new(tmp_path):
    """Old has data, new is all zeros → fail-open: block write."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([100, 200], [30, 50]))  # total = 380
    assert _should_write(_make_stats([0, 0, 0]), old) is False


def test_should_write_blocks_empty_list(tmp_path):
    """Old has data, new is empty list → fail-open: block write."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([100, 200]))  # total = 300
    assert _should_write([], old) is False


def test_should_write_blocks_suspiciously_small(tmp_path):
    """Old has 1000 cards, new has 50 (< 10%) → fail-open: block write."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([500, 300], [100, 100]))  # total = 1000
    assert _should_write(_make_stats([25, 25]), old) is False  # total = 50 (5%)


def test_should_write_allows_modest_decrease(tmp_path):
    """Old has 1000 cards, new has 800 (80%) → allow write."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([500, 300], [100, 100]))  # total = 1000
    assert _should_write(_make_stats([400, 250], [80, 70]), old) is True  # total = 800


def test_should_write_threshold_boundary_10pct(tmp_path):
    """Exactly 10% of old → allow write (boundary is strictly less-than)."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([500, 500]))  # total = 1000
    assert _should_write(_make_stats([100]), old) is True  # total = 100 (exactly 10%)


def test_should_write_threshold_just_below_10pct(tmp_path):
    """99 out of 1000 (9.9%) → block write."""
    old = tmp_path / "old.json"
    _write_json(old, _make_stats([500, 500]))  # total = 1000
    assert _should_write(_make_stats([99]), old) is False  # total = 99 (9.9%)


def test_should_write_old_corrupt_allows_write(tmp_path):
    """Old file is corrupt JSON → treated as total=0 → allow write."""
    old = tmp_path / "corrupt.json"
    old.write_text("{broken", encoding="utf-8")
    assert _should_write(_make_stats([50, 50]), old) is True


# =====================================================================
# _read_existing_review_total
# =====================================================================


def test_read_review_total_missing(tmp_path):
    assert _read_existing_review_total(tmp_path / "nope.json") == 0


def test_read_review_total_corrupt(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert _read_existing_review_total(bad) == 0


def test_read_review_total_valid(tmp_path):
    f = tmp_path / "reviews.json"
    _write_review_json(f, _make_review_entries([100, 200, 50]))  # total = 350
    assert _read_existing_review_total(f) == 350


def test_read_review_total_missing_key(tmp_path):
    """JSON without 'reviews' key → 0."""
    f = tmp_path / "nokey.json"
    f.write_text(json.dumps({"other": 123}), encoding="utf-8")
    assert _read_existing_review_total(f) == 0


def test_read_review_total_empty_array(tmp_path):
    f = tmp_path / "empty.json"
    _write_review_json(f, [])
    assert _read_existing_review_total(f) == 0


# =====================================================================
# _should_write_reviews
# =====================================================================


def test_reviews_should_write_no_old_file(tmp_path):
    assert _should_write_reviews(_make_review_entries([0, 0]), tmp_path / "absent.json") is True


def test_reviews_should_write_no_old_empty_list(tmp_path):
    """Empty new list → still write if no old file."""
    assert _should_write_reviews([], tmp_path / "absent.json") is True


def test_reviews_should_write_normal_update(tmp_path):
    old = tmp_path / "old.json"
    _write_review_json(old, _make_review_entries([100, 200]))  # total = 300
    assert _should_write_reviews(_make_review_entries([110, 190]), old) is True


def test_reviews_should_write_new_larger(tmp_path):
    """New data larger than old → allow."""
    old = tmp_path / "old.json"
    _write_review_json(old, _make_review_entries([50, 50]))  # total = 100
    assert _should_write_reviews(_make_review_entries([500, 500]), old) is True


def test_reviews_blocks_empty_new(tmp_path):
    old = tmp_path / "old.json"
    _write_review_json(old, _make_review_entries([100, 200]))  # total = 300
    assert _should_write_reviews(_make_review_entries([0, 0]), old) is False


def test_reviews_blocks_empty_list(tmp_path):
    """Old has data, new is empty list → block."""
    old = tmp_path / "old.json"
    _write_review_json(old, _make_review_entries([100, 200]))  # total = 300
    assert _should_write_reviews([], old) is False


def test_reviews_blocks_suspiciously_small(tmp_path):
    old = tmp_path / "old.json"
    _write_review_json(old, _make_review_entries([500, 500]))  # total = 1000
    assert _should_write_reviews(_make_review_entries([25, 25]), old) is False  # 5%


def test_reviews_allows_at_10pct_boundary(tmp_path):
    old = tmp_path / "old.json"
    _write_review_json(old, _make_review_entries([500, 500]))  # total = 1000
    assert _should_write_reviews(_make_review_entries([100]), old) is True  # exactly 10%


def test_reviews_blocks_just_below_10pct(tmp_path):
    old = tmp_path / "old.json"
    _write_review_json(old, _make_review_entries([500, 500]))  # total = 1000
    assert _should_write_reviews(_make_review_entries([99]), old) is False  # 9.9%


def test_reviews_old_corrupt_allows_write(tmp_path):
    """Old file is corrupt → treated as 0 → allow write."""
    old = tmp_path / "corrupt.json"
    old.write_text("{{bad", encoding="utf-8")
    assert _should_write_reviews(_make_review_entries([50]), old) is True
