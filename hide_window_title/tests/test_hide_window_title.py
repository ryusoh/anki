import importlib
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def clean_sys_modules():
    # Keep track of originally imported modules to restore them later
    original_modules = sys.modules.copy()
    yield
    # Restore original modules
    sys.modules.clear()
    sys.modules.update(original_modules)
    if 'hide_window_title' in sys.modules:
        del sys.modules['hide_window_title']


def test_hide_window_title_monkeypatch(clean_sys_modules):
    # Mock aqt and AnkiQt
    mock_aqt = MagicMock()
    mock_mw = MagicMock()
    mock_aqt.mw = mock_mw

    class MockAnkiQt:
        @staticmethod
        def setWindowTitle(self, title):
            pass

    mock_aqt.main.AnkiQt = MockAnkiQt

    sys.modules['aqt'] = mock_aqt
    sys.modules['aqt.main'] = mock_aqt.main

    if 'hide_window_title' in sys.modules:
        del sys.modules['hide_window_title']
    import hide_window_title

    assert hasattr(MockAnkiQt, "_hide_window_title_patched")
    assert MockAnkiQt._hide_window_title_patched is True

    pass


def test_hide_window_title_monkeypatch_logic(clean_sys_modules):
    mock_aqt = MagicMock()
    mock_mw = MagicMock()
    mock_aqt.mw = mock_mw

    class MockAnkiQt:
        pass

    mock_set_window_title = MagicMock()
    MockAnkiQt.setWindowTitle = mock_set_window_title

    mock_aqt.main.AnkiQt = MockAnkiQt
    sys.modules['aqt'] = mock_aqt
    sys.modules['aqt.main'] = mock_aqt.main

    import hide_window_title

    # Verify the monkeypatch replaces the method
    assert MockAnkiQt.setWindowTitle != mock_set_window_title

    # Call the new method
    instance = MagicMock()
    MockAnkiQt.setWindowTitle(instance, "New Title")

    # Check that original was called with empty string
    mock_set_window_title.assert_called_once_with(instance, "")

    # Check that mw title was cleared on import
    mock_mw.setWindowTitle.assert_called_once_with("")


def test_hide_window_title_already_patched(clean_sys_modules):
    mock_aqt = MagicMock()
    mock_mw = MagicMock()
    mock_aqt.mw = mock_mw

    class MockAnkiQt:
        _hide_window_title_patched = True

    mock_set_window_title = MagicMock()
    MockAnkiQt.setWindowTitle = mock_set_window_title

    mock_aqt.main.AnkiQt = MockAnkiQt
    sys.modules['aqt'] = mock_aqt
    sys.modules['aqt.main'] = mock_aqt.main

    if 'hide_window_title' in sys.modules:
        del sys.modules['hide_window_title']
    import hide_window_title

    # Should not re-patch
    assert MockAnkiQt.setWindowTitle == mock_set_window_title
    # But should still clear mw title
    mock_mw.setWindowTitle.assert_called_once_with("")


def test_hide_window_title_no_mw(clean_sys_modules):
    mock_aqt = MagicMock()
    mock_aqt.mw = None

    class MockAnkiQt:
        pass

    mock_set_window_title = MagicMock()
    MockAnkiQt.setWindowTitle = mock_set_window_title

    mock_aqt.main.AnkiQt = MockAnkiQt

    sys.modules['aqt'] = mock_aqt
    sys.modules['aqt.main'] = mock_aqt.main

    if 'hide_window_title' in sys.modules:
        del sys.modules['hide_window_title']

    # Should not crash
    import hide_window_title
