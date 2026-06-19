import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_aqt():
    original_modules = sys.modules.copy()

    # Mock modules
    sys.modules['aqt'] = MagicMock()
    sys.modules['aqt.gui_hooks'] = MagicMock()

    # Reload the module to use the mocks
    if 'prioritize_front_field_search' in sys.modules:
        del sys.modules['prioritize_front_field_search']
    import prioritize_front_field_search

    yield prioritize_front_field_search

    # Restore modules
    sys.modules.clear()
    sys.modules.update(original_modules)
    if 'prioritize_front_field_search' in sys.modules:
        del sys.modules['prioritize_front_field_search']


def test_fetch_front_fields(mock_aqt):
    col = MagicMock()
    col.db.all.return_value = [(1, 2, "field1\x1ffield2")]
    result = mock_aqt._fetch_front_fields(col, [1], True)
    assert result[1] == "field1"


def test_on_browser_did_search(mock_aqt):
    search_context = MagicMock()
    search_context.search = "test"
    search_context.ids = [1, 2]
    search_context.is_notes = True

    col = MagicMock()
    col.db.all.return_value = [(1, 10, "test\x1ffield2"), (2, 20, "other\x1ftest")]
    search_context.browser.col = col

    mock_aqt.on_browser_did_search(search_context)
    assert search_context.ids == [1, 2]
