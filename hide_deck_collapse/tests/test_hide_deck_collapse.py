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
    if 'hide_deck_collapse' in sys.modules:
        del sys.modules['hide_deck_collapse']
    import hide_deck_collapse

    yield hide_deck_collapse

    # Restore modules
    sys.modules.clear()
    sys.modules.update(original_modules)
    if 'hide_deck_collapse' in sys.modules:
        del sys.modules['hide_deck_collapse']


def test_on_webview_will_set_content_deck_browser(mock_aqt):
    class DeckBrowser:
        pass

    web_content = MagicMock()
    web_content.head = "<html>"
    mock_aqt.on_webview_will_set_content(web_content, DeckBrowser())
    assert "visibility: hidden" in web_content.head
    assert "width: 550px" in web_content.head


def test_on_webview_will_set_content_other_context(mock_aqt):
    class OtherContext:
        pass

    web_content = MagicMock()
    web_content.head = "<html>"
    mock_aqt.on_webview_will_set_content(web_content, OtherContext())
    assert web_content.head == "<html>"
