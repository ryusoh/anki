"""Tests for the fail-open mechanism in stats_page_customizer.

Ensures _write_custom_stats_payload preserves old data when new data
is empty or suspiciously small.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock aqt with classes that support __init__ patching
_mock_aqt = MagicMock()


class _FakeStatsClass:
    """Dummy class that can have __init__ and refresh patched."""

    def __init__(self, *a, **kw):
        pass

    def refresh(self, *a, **kw):
        pass


_mock_stats = MagicMock()
_mock_stats.DeckStats = _FakeStatsClass
_mock_stats.NewDeckStats = _FakeStatsClass

sys.modules["aqt"] = _mock_aqt
sys.modules["aqt.gui_hooks"] = MagicMock()
sys.modules["aqt.qt"] = MagicMock()
sys.modules["aqt.stats"] = _mock_stats
sys.modules["aqt.utils"] = MagicMock()
sys.modules["aqt.webview"] = MagicMock()

import stats_page_customizer
from stats_page_customizer import (
    _read_existing_total_from_file,
    _write_custom_stats_payload,
)


def _make_payload(mature_vals, young_vals=None):
    """Build a payload dict from mature/young value lists."""
    if young_vals is None:
        young_vals = [0] * len(mature_vals)
    entries = [
        {"day": i, "mature": m, "young": y} for i, (m, y) in enumerate(zip(mature_vals, young_vals))
    ]
    return {"futureDue": entries}


def _write_json(path, payload):
    """Write a payload to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# =====================================================================
# _read_existing_total_from_file
# =====================================================================


def test_read_total_missing(tmp_path):
    assert _read_existing_total_from_file(tmp_path / "nope.json") == 0


def test_read_total_corrupt(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    assert _read_existing_total_from_file(bad) == 0


def test_read_total_valid(tmp_path):
    f = tmp_path / "data.json"
    _write_json(f, _make_payload([100, 50], [20, 10]))  # total = 180
    assert _read_existing_total_from_file(f) == 180


def test_read_total_missing_key(tmp_path):
    """No 'futureDue' key → 0."""
    f = tmp_path / "nokey.json"
    f.write_text(json.dumps({"other": 42}), encoding="utf-8")
    assert _read_existing_total_from_file(f) == 0


def test_read_total_empty_array(tmp_path):
    f = tmp_path / "empty.json"
    _write_json(f, _make_payload([]))
    assert _read_existing_total_from_file(f) == 0


# =====================================================================
# _write_custom_stats_payload (fail-open)
# =====================================================================


def test_write_allows_when_no_old_file(tmp_path, monkeypatch):
    """No existing file → always write new data."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    _write_custom_stats_payload(_make_payload([50, 30], [10, 5]))

    assert target.exists()
    written = json.loads(target.read_text(encoding="utf-8"))
    assert len(written["futureDue"]) == 2


def test_write_allows_normal_update(tmp_path, monkeypatch):
    """Old and new have similar totals → allow overwrite."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    _write_json(target, _make_payload([100, 100], [50, 50]))  # total = 300
    _write_custom_stats_payload(_make_payload([110, 90], [45, 55]))  # total = 300

    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["futureDue"][0]["mature"] == 110


def test_write_allows_new_larger(tmp_path, monkeypatch):
    """New data larger than old → allow."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    _write_json(target, _make_payload([50, 50]))  # total = 100
    _write_custom_stats_payload(_make_payload([500, 500], [200, 200]))  # total = 1400

    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["futureDue"][0]["mature"] == 500


def test_write_blocks_empty_new(tmp_path, monkeypatch):
    """Old has data, new is empty → fail-open: preserve old."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    _write_json(target, _make_payload([100, 200], [30, 50]))  # total = 380
    _write_custom_stats_payload(_make_payload([0, 0, 0]))  # total = 0

    preserved = json.loads(target.read_text(encoding="utf-8"))
    assert preserved["futureDue"][0]["mature"] == 100


def test_write_blocks_empty_list(tmp_path, monkeypatch):
    """Old has data, new is empty list → fail-open: preserve old."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    _write_json(target, _make_payload([100, 200]))  # total = 300
    _write_custom_stats_payload({"futureDue": []})

    preserved = json.loads(target.read_text(encoding="utf-8"))
    assert preserved["futureDue"][0]["mature"] == 100


def test_write_blocks_suspiciously_small(tmp_path, monkeypatch):
    """Old has 1000, new has 50 (< 10%) → fail-open: preserve old."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    _write_json(target, _make_payload([500, 300], [100, 100]))  # total = 1000
    _write_custom_stats_payload(_make_payload([25, 25]))  # total = 50 (5%)

    preserved = json.loads(target.read_text(encoding="utf-8"))
    assert preserved["futureDue"][0]["mature"] == 500


def test_write_allows_at_10pct_boundary(tmp_path, monkeypatch):
    """Exactly 10% → allow write."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    _write_json(target, _make_payload([500, 500]))  # total = 1000
    _write_custom_stats_payload(_make_payload([100]))  # total = 100 (exactly 10%)

    written = json.loads(target.read_text(encoding="utf-8"))
    assert len(written["futureDue"]) == 1


def test_write_blocks_just_below_10pct(tmp_path, monkeypatch):
    """99 out of 1000 → block."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    _write_json(target, _make_payload([500, 500]))  # total = 1000
    _write_custom_stats_payload(_make_payload([99]))  # total = 99 (9.9%)

    preserved = json.loads(target.read_text(encoding="utf-8"))
    assert preserved["futureDue"][0]["mature"] == 500


def test_write_old_corrupt_allows_write(tmp_path, monkeypatch):
    """Old file is corrupt JSON → treated as 0 → allow write."""
    target = tmp_path / "custom_stats_30d.json"
    monkeypatch.setattr(stats_page_customizer, "CUSTOM_STATS_30D_JSON", target)

    target.write_text("{{broken", encoding="utf-8")
    _write_custom_stats_payload(_make_payload([50, 30]))

    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["futureDue"][0]["mature"] == 50
