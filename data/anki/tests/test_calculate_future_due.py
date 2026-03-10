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

    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=3, anki_today=anki_today)

    assert len(result_global) == 3
    assert result_global[0] == {"day": 0, "mature": 1, "young": 1}
    assert result_global[1] == {"day": 1, "mature": 1, "young": 0}
    assert result_global[2] == {"day": 2, "mature": 0, "young": 1}

def test_calculate_future_due_empty():
    """Test with empty cards_data."""
    result_global, result_by_deck = calculate_future_due([], cid_to_deck={}, max_days=None, anki_today=100)
    assert result_global == []
    assert result_by_deck == {}

def test_calculate_future_due_no_reviews():
    """Test with cards but no review cards (queue=2)."""
    cards_data = [
        {"due": 100, "ivl": 21, "queue": 0}, # New card
        {"due": 100, "ivl": 1,  "queue": 1}, # Learning card
    ]
    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=None, anki_today=100)
    assert result_global == []
    assert result_by_deck == {}

def test_calculate_future_due_overdue():
    """Overdue cards should be skipped."""
    anki_today = 100
    cards_data = [
        {"due": 99, "ivl": 21, "queue": 2}, # Overdue
        {"due": 100, "ivl": 21, "queue": 2}, # Today
    ]
    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=None, anki_today=anki_today)
    # max_due is 100. max_days = 100 - 100 + 1 = 1.
    assert len(result_global) == 1
    assert result_global[0] == {"day": 0, "mature": 1, "young": 0}

def test_calculate_future_due_max_days_limit():
    """Cards scheduled beyond max_days should be skipped."""
    anki_today = 100
    cards_data = [
        {"due": 100, "ivl": 21, "queue": 2},
        {"due": 105, "ivl": 21, "queue": 2},
    ]
    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=3, anki_today=anki_today)
    assert len(result_global) == 3
    assert result_global[0] == {"day": 0, "mature": 1, "young": 0}
    assert result_global[1] == {"day": 1, "mature": 0, "young": 0}
    assert result_global[2] == {"day": 2, "mature": 0, "young": 0}

def test_calculate_future_due_maturity_boundary():
    """Test the 21-day maturity boundary."""
    anki_today = 100
    cards_data = [
        {"due": 100, "ivl": 20, "queue": 2}, # Young
        {"due": 100, "ivl": 21, "queue": 2}, # Mature
    ]
    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=1, anki_today=anki_today)
    assert result_global[0] == {"day": 0, "mature": 1, "young": 1}

def test_calculate_future_due_auto_max_days():
    """Test automatic max_days calculation."""
    anki_today = 100
    cards_data = [
        {"due": 102, "ivl": 21, "queue": 2},
    ]
    # max_due = 102. anki_today = 100. max_days = 102 - 100 + 1 = 3.
    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=None, anki_today=anki_today)
    assert len(result_global) == 3
    assert result_global[0]["day"] == 0
    assert result_global[1]["day"] == 1
    assert result_global[2]["day"] == 2
    assert result_global[2]["mature"] == 1

def test_calculate_future_due_fallback_today(monkeypatch):
    """Test that it falls back to get_anki_today() if anki_today is None."""
    monkeypatch.setattr("generate_custom_stats.get_anki_today", lambda: 500)
    cards_data = [{"due": 500, "ivl": 10, "queue": 2}]
    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=1, anki_today=None)
    assert len(result_global) == 1
    assert result_global[0] == {"day": 0, "mature": 0, "young": 1}

def test_calculate_future_due_by_deck():
    """Test that result_by_deck correctly splits data by deck."""
    anki_today = 100
    cards_data = [
        {"id": 1, "due": 100, "ivl": 21, "queue": 2}, # Deck A, mature
        {"id": 2, "due": 101, "ivl": 10, "queue": 2}, # Deck A, young
        {"id": 3, "due": 100, "ivl": 25, "queue": 2}, # Deck B, mature
        {"id": 4, "due": 102, "ivl": 5,  "queue": 2}, # Unknown, young
    ]
    cid_to_deck = {
        1: "Deck A",
        2: "Deck A",
        3: "Deck B"
    }

    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck=cid_to_deck, max_days=3, anki_today=anki_today)

    # Check global stats
    assert len(result_global) == 3
    assert result_global[0] == {"day": 0, "mature": 2, "young": 0}
    assert result_global[1] == {"day": 1, "mature": 0, "young": 1}
    assert result_global[2] == {"day": 2, "mature": 0, "young": 1}

    # Check by deck stats
    assert "Deck A" in result_by_deck
    assert "Deck B" in result_by_deck
    assert "Unknown" in result_by_deck

    # Deck A has due 100 and 101
    assert result_by_deck["Deck A"] == [
        {"day": 0, "mature": 1, "young": 0},
        {"day": 1, "mature": 0, "young": 1}
    ]

    # Deck B has due 100
    assert result_by_deck["Deck B"] == [
        {"day": 0, "mature": 1, "young": 0}
    ]

    # Unknown has due 102
    assert result_by_deck["Unknown"] == [
        {"day": 2, "mature": 0, "young": 1}
    ]

def test_calculate_future_due_cid_to_deck_none():
    """Test when cid_to_deck is completely empty or not provided properly."""
    anki_today = 100
    cards_data = [
        {"id": 1, "due": 100, "ivl": 21, "queue": 2},
    ]

    result_global, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=1, anki_today=anki_today)
    assert "Unknown" in result_by_deck
    assert result_by_deck["Unknown"] == [{"day": 0, "mature": 1, "young": 0}]
