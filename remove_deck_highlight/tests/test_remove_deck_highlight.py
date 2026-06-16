import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def setup_module():
    mock_aqt = MagicMock()
    mock_gui_hooks = MagicMock()
    mock_aqt.gui_hooks = mock_gui_hooks

    class DeckBrowser:
        pass

    mock_aqt.mw = MagicMock()
    mock_aqt.mw.deckBrowser = DeckBrowser()

    sys.modules['aqt'] = mock_aqt

    if 'remove_deck_highlight' in sys.modules:
        del sys.modules['remove_deck_highlight']

    import remove_deck_highlight

    yield remove_deck_highlight

    if 'remove_deck_highlight' in sys.modules:
        del sys.modules['remove_deck_highlight']


def test_on_webview_will_set_content_deckbrowser(setup_module):
    module = setup_module
    web_content = MagicMock()
    web_content.head = "<html><head></head>"
    web_content.body = "<body>"

    context = sys.modules['aqt'].mw.deckBrowser

    module.on_webview_will_set_content(web_content, context)

    assert "tr.deck.current" in web_content.head
    assert "background-color: transparent !important;" in web_content.head
    assert "const stripCurrent" in web_content.body


def test_on_webview_will_set_content_other(setup_module):
    module = setup_module
    web_content = MagicMock()
    web_content.head = "<html><head></head>"
    web_content.body = "<body>"

    class OtherBrowser:
        pass

    context = OtherBrowser()

    module.on_webview_will_set_content(web_content, context)

    assert "tr.deck.current" not in web_content.head
    assert "const stripCurrent" not in web_content.body
