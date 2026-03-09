import pytest
import sys
from pathlib import Path

# Add parent to sys.path so we can import the modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_custom_stats import calculate_future_due

def test_calculate_future_due_basic():
    """Test with a mix of mature and young cards."""
    anki_today = 100
    cards_data = [
        {"due": 100, "ivl": 21, "queue": 2}, # Today, mature
        {"due": 100, "ivl": 10, "queue": 2}, # Today, young
        {"due": 101, "ivl": 25, "queue": 2}, # Tomorrow, mature
        {"due": 102, "ivl": 5,  "queue": 2}, # Day after, young
    ]

    result = calculate_future_due(cards_data, max_days=3, anki_today=anki_today)

    assert len(result) == 3
    assert result[0] == {"day": 0, "mature": 1, "young": 1}
    assert result[1] == {"day": 1, "mature": 1, "young": 0}
    assert result[2] == {"day": 2, "mature": 0, "young": 1}

def test_calculate_future_due_empty():
    """Test with empty cards_data."""
    result = calculate_future_due([], max_days=None, anki_today=100)
    assert result == []

def test_calculate_future_due_no_reviews():
    """Test with cards but no review cards (queue=2)."""
    cards_data = [
        {"due": 100, "ivl": 21, "queue": 0}, # New card
        {"due": 100, "ivl": 1,  "queue": 1}, # Learning card
    ]
    result = calculate_future_due(cards_data, max_days=None, anki_today=100)
    assert result == []

def test_calculate_future_due_overdue():
    """Overdue cards should be skipped."""
    anki_today = 100
    cards_data = [
        {"due": 99, "ivl": 21, "queue": 2}, # Overdue
        {"due": 100, "ivl": 21, "queue": 2}, # Today
    ]
    result = calculate_future_due(cards_data, max_days=None, anki_today=anki_today)
    # max_due is 100. max_days = 100 - 100 + 1 = 1.
    assert len(result) == 1
    assert result[0] == {"day": 0, "mature": 1, "young": 0}

def test_calculate_future_due_max_days_limit():
    """Cards scheduled beyond max_days should be skipped."""
    anki_today = 100
    cards_data = [
        {"due": 100, "ivl": 21, "queue": 2},
        {"due": 105, "ivl": 21, "queue": 2},
    ]
    result = calculate_future_due(cards_data, max_days=3, anki_today=anki_today)
    assert len(result) == 3
    assert result[0] == {"day": 0, "mature": 1, "young": 0}
    assert result[1] == {"day": 1, "mature": 0, "young": 0}
    assert result[2] == {"day": 2, "mature": 0, "young": 0}

def test_calculate_future_due_maturity_boundary():
    """Test the 21-day maturity boundary."""
    anki_today = 100
    cards_data = [
        {"due": 100, "ivl": 20, "queue": 2}, # Young
        {"due": 100, "ivl": 21, "queue": 2}, # Mature
    ]
    result = calculate_future_due(cards_data, max_days=1, anki_today=anki_today)
    assert result[0] == {"day": 0, "mature": 1, "young": 1}

def test_calculate_future_due_auto_max_days():
    """Test automatic max_days calculation."""
    anki_today = 100
    cards_data = [
        {"due": 102, "ivl": 21, "queue": 2},
    ]
    # max_due = 102. anki_today = 100. max_days = 102 - 100 + 1 = 3.
    result = calculate_future_due(cards_data, max_days=None, anki_today=anki_today)
    assert len(result) == 3
    assert result[0]["day"] == 0
    assert result[1]["day"] == 1
    assert result[2]["day"] == 2
    assert result[2]["mature"] == 1

def test_calculate_future_due_fallback_today(monkeypatch):
    """Test that it falls back to get_anki_today() if anki_today is None."""
    monkeypatch.setattr("generate_custom_stats.get_anki_today", lambda: 500)
    cards_data = [{"due": 500, "ivl": 10, "queue": 2}]
    result = calculate_future_due(cards_data, max_days=1, anki_today=None)
    assert len(result) == 1
    assert result[0] == {"day": 0, "mature": 0, "young": 1}
