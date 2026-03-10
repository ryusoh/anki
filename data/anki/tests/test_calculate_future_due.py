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
        {"id": 1, "due": 100, "ivl": 21, "queue": 2}, # Today, mature
        {"id": 2, "due": 100, "ivl": 10, "queue": 2}, # Today, young
        {"id": 3, "due": 101, "ivl": 25, "queue": 2}, # Tomorrow, mature
        {"id": 4, "due": 102, "ivl": 5,  "queue": 2}, # Day after, young
    ]
    cid_to_deck = {1: "DeckA", 2: "DeckB", 3: "DeckA", 4: "DeckB"}

    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck=cid_to_deck, max_days=3, anki_today=anki_today)

    assert len(result) == 3
    assert result[0] == {"day": 0, "mature": 1, "young": 1}
    assert result[1] == {"day": 1, "mature": 1, "young": 0}
    assert result[2] == {"day": 2, "mature": 0, "young": 1}

    assert "DeckA" in result_by_deck
    assert result_by_deck["DeckA"] == [
        {"day": 0, "mature": 1, "young": 0},
        {"day": 1, "mature": 1, "young": 0}
    ]

    assert "DeckB" in result_by_deck
    assert result_by_deck["DeckB"] == [
        {"day": 0, "mature": 0, "young": 1},
        {"day": 2, "mature": 0, "young": 1}
    ]

def test_calculate_future_due_empty():
    """Test with empty cards_data."""
    result, result_by_deck = calculate_future_due([], cid_to_deck={}, max_days=None, anki_today=100)
    assert result == []
    assert result_by_deck == {}

def test_calculate_future_due_no_reviews():
    """Test with cards but no review cards (queue=2)."""
    cards_data = [
        {"id": 1, "due": 100, "ivl": 21, "queue": 0}, # New card
        {"id": 2, "due": 100, "ivl": 1,  "queue": 1}, # Learning card
    ]
    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=None, anki_today=100)
    assert result == []
    assert result_by_deck == {}

def test_calculate_future_due_overdue():
    """Overdue cards should be skipped."""
    anki_today = 100
    cards_data = [
        {"id": 1, "due": 99, "ivl": 21, "queue": 2}, # Overdue
        {"id": 2, "due": 100, "ivl": 21, "queue": 2}, # Today
    ]
    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=None, anki_today=anki_today)
    # max_due is 100. max_days = 100 - 100 + 1 = 1.
    assert len(result) == 1
    assert result[0] == {"day": 0, "mature": 1, "young": 0}
    assert "Unknown" in result_by_deck
    assert len(result_by_deck["Unknown"]) == 1

def test_calculate_future_due_max_days_limit():
    """Cards scheduled beyond max_days should be skipped."""
    anki_today = 100
    cards_data = [
        {"id": 1, "due": 100, "ivl": 21, "queue": 2},
        {"id": 2, "due": 105, "ivl": 21, "queue": 2},
    ]
    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=3, anki_today=anki_today)
    assert len(result) == 3
    assert result[0] == {"day": 0, "mature": 1, "young": 0}
    assert result[1] == {"day": 1, "mature": 0, "young": 0}
    assert result[2] == {"day": 2, "mature": 0, "young": 0}

def test_calculate_future_due_maturity_boundary():
    """Test the 21-day maturity boundary."""
    anki_today = 100
    cards_data = [
        {"id": 1, "due": 100, "ivl": 20, "queue": 2}, # Young
        {"id": 2, "due": 100, "ivl": 21, "queue": 2}, # Mature
    ]
    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=1, anki_today=anki_today)
    assert result[0] == {"day": 0, "mature": 1, "young": 1}

def test_calculate_future_due_auto_max_days():
    """Test automatic max_days calculation."""
    anki_today = 100
    cards_data = [
        {"id": 1, "due": 102, "ivl": 21, "queue": 2},
    ]
    # max_due = 102. anki_today = 100. max_days = 102 - 100 + 1 = 3.
    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=None, anki_today=anki_today)
    assert len(result) == 3
    assert result[0]["day"] == 0
    assert result[1]["day"] == 1
    assert result[2]["day"] == 2
    assert result[2]["mature"] == 1

def test_calculate_future_due_fallback_today(monkeypatch):
    """Test that it falls back to get_anki_today() if anki_today is None."""
    monkeypatch.setattr("generate_custom_stats.get_anki_today", lambda: 500)
    cards_data = [{"id": 1, "due": 500, "ivl": 10, "queue": 2}]
    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck={}, max_days=1, anki_today=None)
    assert len(result) == 1
    assert result[0] == {"day": 0, "mature": 0, "young": 1}

def test_calculate_future_due_missing_cid_to_deck():
    """Test that the function works without error when cid_to_deck is None."""
    cards_data = [{"id": 1, "due": 100, "ivl": 21, "queue": 2}]
    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck=None, max_days=1, anki_today=100)
    assert len(result) == 1
    assert "Unknown" in result_by_deck
    assert result_by_deck["Unknown"] == [{"day": 0, "mature": 1, "young": 0}]

def test_calculate_future_due_missing_keys():
    """Test that missing keys in a card dictionary are handled gracefully."""
    cards_data = [
        # Missing 'due' -> defaults to 0, which means overdue (100 - 0 = -100 days from now), so it's skipped
        {"id": 1, "ivl": 21, "queue": 2},
        # Missing 'ivl' -> defaults to 0 -> young
        {"id": 2, "due": 100, "queue": 2},
        # Missing 'queue' -> defaults to 0 -> non-review -> skipped
        {"id": 3, "due": 100, "ivl": 21},
        # Missing 'id' -> handled fine, defaults to Unknown deck
        {"due": 100, "ivl": 21, "queue": 2},
    ]
    result, result_by_deck = calculate_future_due(cards_data, cid_to_deck={1: "A", 2: "B", 3: "C"}, max_days=1, anki_today=100)

    # We expect the 2nd card to be processed as young, and the 4th card as mature.
    assert len(result) == 1
    assert result[0] == {"day": 0, "mature": 1, "young": 1}

    assert "B" in result_by_deck
    assert result_by_deck["B"] == [{"day": 0, "mature": 0, "young": 1}]

    assert "Unknown" in result_by_deck
    assert result_by_deck["Unknown"] == [{"day": 0, "mature": 1, "young": 0}]

    # "A" and "C" should not be present because those cards were skipped
    assert "A" not in result_by_deck
    assert "C" not in result_by_deck
