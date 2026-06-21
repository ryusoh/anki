import sys
from unittest.mock import MagicMock

# Mock aqt with classes that support __init__ patching
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

from stats_page_customizer import _process_future_due_rows


def test_process_future_due_rows():
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
