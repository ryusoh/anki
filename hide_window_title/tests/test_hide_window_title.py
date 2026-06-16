import importlib
import sys
from unittest.mock import MagicMock


def test_hide_window_title_initialization():
    # Set up mocks
    mock_aqt = MagicMock()
    mock_aqt.mw = MagicMock()
    sys.modules['aqt'] = mock_aqt

    mock_aqt_main = MagicMock()
    mock_AnkiQt = MagicMock()
    # Ensure it doesn't have the attribute initially
    del mock_AnkiQt._hide_window_title_patched

    # We will mock setWindowTitle to track calls
    original_set_window_title = MagicMock()
    mock_AnkiQt.setWindowTitle = original_set_window_title

    mock_aqt_main.AnkiQt = mock_AnkiQt
    sys.modules['aqt.main'] = mock_aqt_main

    # Import module
    import hide_window_title

    # Reload to ensure we test the main execution path if it was already imported
    importlib.reload(hide_window_title)

    # Assertions
    assert mock_AnkiQt._hide_window_title_patched is True
    assert mock_AnkiQt.setWindowTitle != original_set_window_title

    # Call the patched method
    mock_self = MagicMock()
    mock_AnkiQt.setWindowTitle(mock_self, "Test Title")

    # Ensure original method was called with empty string
    original_set_window_title.assert_called_with(mock_self, "")

    # Ensure mw.setWindowTitle was called
    mock_aqt.mw.setWindowTitle.assert_called_with("")


def test_hide_window_title_already_patched():
    # Set up mocks
    mock_aqt = MagicMock()
    mock_aqt.mw = None  # Test case where mw is None
    sys.modules['aqt'] = mock_aqt

    mock_aqt_main = MagicMock()
    mock_AnkiQt = MagicMock()
    mock_AnkiQt._hide_window_title_patched = True

    original_set_window_title = MagicMock()
    mock_AnkiQt.setWindowTitle = original_set_window_title

    mock_aqt_main.AnkiQt = mock_AnkiQt
    sys.modules['aqt.main'] = mock_aqt_main

    import hide_window_title

    importlib.reload(hide_window_title)

    # Method should not be patched again
    assert mock_AnkiQt.setWindowTitle == original_set_window_title
