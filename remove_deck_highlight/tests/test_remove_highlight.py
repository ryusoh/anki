import pytest
import sys
from unittest.mock import MagicMock

# Mock out aqt entirely
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()

# We need to setup mw.deckBrowser type
class MockDeckBrowser:
    pass

sys.modules['aqt'].mw = MagicMock()
sys.modules['aqt'].mw.deckBrowser = MockDeckBrowser()

import remove_deck_highlight
from remove_deck_highlight import on_webview_will_set_content

def test_on_webview_will_set_content_ignore():
    web_content = MagicMock()
    context = MagicMock()

    on_webview_will_set_content(web_content, context)

    # Should not append anything
    assert web_content.head.call_count == 0
    assert web_content.body.call_count == 0

def test_on_webview_will_set_content_inject():
    class WebContent:
        def __init__(self):
            self.head = "<html>"
            self.body = "<body>"

    web_content = WebContent()
    context = MockDeckBrowser()

    on_webview_will_set_content(web_content, context)

    assert "tr.deck.current," in web_content.head
    assert "stripCurrent();" in web_content.body
