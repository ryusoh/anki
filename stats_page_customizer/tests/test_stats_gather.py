import sys
from unittest.mock import MagicMock, patch

import pytest

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

from stats_page_customizer import _gather_future_due, mw


@patch('stats_page_customizer._fetch_future_due_rows')
def test_gather_future_due_success(mock_fetch):
    mock_fetch.return_value = [(0, 5, 2), (1, 10, 0)]
    mw.col.sched.today = 1000

    res = _gather_future_due(days=3)

    assert len(res) == 4
    assert res[0]['mature'] == 5
    assert res[0]['young'] == 2
    assert res[1]['mature'] == 10


@patch('stats_page_customizer._fetch_future_due_rows')
def test_gather_future_due_exception(mock_fetch):
    mock_fetch.side_effect = Exception("Test Exception")
    mw.col.sched.today = 1000

    with pytest.raises(Exception, match='Test Exception'):
        _gather_future_due(days=3)


def test_gather_future_due_no_mw():
    old_mw = sys.modules['stats_page_customizer'].mw
    sys.modules['stats_page_customizer'].mw = None
    res = _gather_future_due()
    assert res == []
    sys.modules['stats_page_customizer'].mw = old_mw


def test_gather_future_due_sched_exception():
    old_col = mw.col
    mw.col = MagicMock()
    type(mw.col.sched).today = property(lambda self: (_ for _ in ()).throw(Exception("test")))

    res = _gather_future_due()
    assert res == []
    mw.col = old_col


def test_process_future_due_rows():
    from stats_page_customizer import _process_future_due_rows

    rows = [(0, 5, 2), (1, 10, 0), (5, 0, 3)]
    res = _process_future_due_rows(rows, max_days=30)
    assert len(res) == 31  # 0 to 30 inclusive
    assert res[0]['day'] == 0
    assert res[0]['mature'] == 5
    assert res[0]['young'] == 2
    assert res[1]['mature'] == 10
    assert res[1]['young'] == 0
    assert res[5]['mature'] == 0
    assert res[5]['young'] == 3
    assert res[2]['mature'] == 0
    assert res[2]['young'] == 0


def test_process_future_due_rows_out_of_bounds():
    from stats_page_customizer import _process_future_due_rows

    # Day -1 should be skipped, Day 31 should be skipped
    rows = [(-1, 5, 5), (0, 10, 10), (31, 20, 20)]
    res = _process_future_due_rows(rows, max_days=30)
    assert len(res) == 31
    assert res[0]['mature'] == 10
    # Day 31 should not be in the results (length is 31: 0-30)
    assert res[30]['mature'] == 0
