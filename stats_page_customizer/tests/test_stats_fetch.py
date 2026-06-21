import sys
from unittest.mock import MagicMock, patch

_mock_aqt = MagicMock()


class _FakeStatsClass:
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

from stats_page_customizer import _fetch_future_due_rows, mw


def test_fetch_future_due_rows():
    mw.col.db.all.return_value = [(0, 5, 2)]
    res = _fetch_future_due_rows(today=100, max_days=30)
    assert res == [(0, 5, 2)]
    mw.col.db.all.assert_called_once()


def test_fetch_future_due_rows_none():
    from stats_page_customizer import _fetch_future_due_rows, mw

    mw.col.db.all.return_value = []
    res = _fetch_future_due_rows(today=100, max_days=30)
    assert res == []
