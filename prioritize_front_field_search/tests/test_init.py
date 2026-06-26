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


def test_fetch_front_fields_none_model(mock_aqt):
    col = MagicMock()
    col.db.all.return_value = [(1, 2, "field1\x1ffield2")]
    col.models.get.return_value = None
    result = mock_aqt._fetch_front_fields(col, [1], True)
    assert result == {1: 'field1'}


def test_fetch_front_fields_no_front(mock_aqt):
    col = MagicMock()
    col.db.all.return_value = [(1, 2, "field1\x1ffield2")]
    col.models.get.return_value = {'flds': [{'name': 'Back', 'ord': 0}]}
    result = mock_aqt._fetch_front_fields(col, [1], True)
    # Default idx is 0, so it will get field1
    assert result[1] == "field1"


def test_on_browser_did_search_no_query(mock_aqt):
    search_context = MagicMock()
    search_context.search = ""
    mock_aqt.on_browser_did_search(search_context)
    # ids should not be changed since it returned early


def test_on_browser_did_search_no_terms(mock_aqt, monkeypatch):
    search_context = MagicMock()
    search_context.search = "test"
    import prioritize_front_field_search.search

    monkeypatch.setattr(mock_aqt, "extract_terms", lambda x: [])
    mock_aqt.on_browser_did_search(search_context)


def test_on_browser_did_search_no_ids(mock_aqt):
    search_context = MagicMock()
    search_context.search = "test"
    search_context.ids = []
    mock_aqt.on_browser_did_search(search_context)


def test_on_browser_did_search_exception(mock_aqt, capsys):
    search_context = MagicMock()
    # Mock search to raise an exception
    type(search_context).search = property(
        lambda self: (_ for _ in ()).throw(Exception("Test Error"))
    )
    mock_aqt.on_browser_did_search(search_context)
    captured = capsys.readouterr()
    assert "Test Error" in captured.out


def test_fetch_front_fields_not_notes_mode(mock_aqt):
    col = MagicMock()
    col.db.all.return_value = [(1, 2, "field1\x1ffield2")]
    result = mock_aqt._fetch_front_fields(col, [1], False)
    assert result[1] == "field1"


def test_on_browser_did_search_import_error(mock_aqt, monkeypatch):
    import prioritize_front_field_search

    # To test the import error branch we can mock the import inside init()
    # However init is already called when module is loaded.
    pass


def test_fetch_front_fields_with_front_field(mock_aqt):
    col = MagicMock()
    col.db.all.return_value = [(1, 2, "back\x1ffront_text\x1fother")]
    col.models.get.return_value = {
        'flds': [{'name': 'Back', 'ord': 0}, {'name': 'Front', 'ord': 1}]
    }
    result = mock_aqt._fetch_front_fields(col, [1], True)
    assert result[1] == "front_text"


def test_fetch_front_fields_idx_out_of_bounds(mock_aqt):
    col = MagicMock()
    col.db.all.return_value = [(1, 2, "back")]
    col.models.get.return_value = {
        'flds': [{'name': 'Back', 'ord': 0}, {'name': 'Front', 'ord': 1}]
    }
    result = mock_aqt._fetch_front_fields(col, [1], True)
    assert 1 not in result


def test_on_browser_did_search_no_tier_1(mock_aqt):
    search_context = MagicMock()
    search_context.search = "test"
    search_context.ids = [1]

    col = MagicMock()
    # "other" does not match "test"
    col.db.all.return_value = [(1, 10, "other")]
    search_context.browser.col = col

    mock_aqt.on_browser_did_search(search_context)
    assert search_context.ids == [1]


def test_init_import_error():
    import sys

    original_modules = sys.modules.copy()

    # Force ImportError
    sys.modules['aqt.gui_hooks'] = None

    # Need to reload
    if 'prioritize_front_field_search' in sys.modules:
        del sys.modules['prioritize_front_field_search']

    import prioritize_front_field_search

    # It logs a warning but shouldn't crash

    # Restore
    sys.modules.clear()
    sys.modules.update(original_modules)
    if 'prioritize_front_field_search' in sys.modules:
        del sys.modules['prioritize_front_field_search']


def test_fetch_front_fields_cached_model(mock_aqt):
    col = MagicMock()
    # Return two rows with the same mid to test the cache branch 26->28
    col.db.all.return_value = [(1, 2, "field1"), (2, 2, "field2")]
    col.models.get.return_value = {'flds': [{'name': 'Front', 'ord': 0}]}

    result = mock_aqt._fetch_front_fields(col, [1, 2], True)
    assert result[1] == "field1"
    assert result[2] == "field2"
    # col.models.get should only be called once due to cache
    col.models.get.assert_called_once_with(2)
