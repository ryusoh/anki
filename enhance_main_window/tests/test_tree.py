from unittest.mock import MagicMock, patch

import pytest

import enhance_main_window.tree as tree


@pytest.fixture(autouse=True)
def mock_anki_modules():
    tree.values.clear()
    tree.times.clear()

    with patch("enhance_main_window.tree.mw") as mw:
        # Mock configuration for computeValues
        mw.col.get_config.return_value = 1000
        mw.col.sched.today = 500
        mw.col.sched.day_cutoff = 100000

        # We need a mock for db.all
        yield mw


def test_computeValues(mock_anki_modules):
    def mock_db_all(query):
        if "from cards " in query.lower():
            # Match number of aggregates
            # There are 19 conditions for cards, and 2 for revlog ...
            # It groups by table, so counting the SUM( aggregates works.
            num_selects = query.count("SUM(")
            return [[123] + [2] * num_selects]  # did=123, val=2 for all columns
        elif "revlog" in query.lower():
            num_selects = query.count("SUM(")
            return [[456] + [3] * num_selects]
        return []

    mock_anki_modules.col.db.all.side_effect = mock_db_all

    tree.computeValues()

    assert "cards" in tree.values
    assert tree.values["cards"][123] == 2
    assert tree.values["repeated"][456] == 3


def test_computeTime(mock_anki_modules):
    mock_anki_modules.col.db.all.return_value = [[123, 4000]]
    tree.computeTime()
    assert tree.times[123] == 4000


def test_computeValues_None_or_zero(mock_anki_modules):
    def mock_db_all(query):
        if "from cards " in query.lower():
            num_selects = query.count("SUM(")
            return [[123] + [0, None] * (num_selects // 2) + [0] * (num_selects % 2)]
        return []

    mock_anki_modules.col.db.all.side_effect = mock_db_all
    tree.computeValues()
    for _name, did_dict in tree.values.items():
        assert 123 not in did_dict
