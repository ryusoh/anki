import importlib
import sys
from unittest.mock import MagicMock


def test_remove_deck_highlight():
    mock_aqt = MagicMock()
    # We need to mock aqt.gui_hooks as an object that has an appendable list
    mock_gui_hooks = MagicMock()
    mock_gui_hooks.webview_will_set_content = []
    mock_aqt.gui_hooks = mock_gui_hooks

    mock_mw = MagicMock()

    # Let's create a specific class for the deck browser so type() works
    class MockDeckBrowser:
        pass

    mock_deckBrowser = MockDeckBrowser()
    mock_mw.deckBrowser = mock_deckBrowser
    mock_aqt.mw = mock_mw

    sys.modules['aqt'] = mock_aqt

    import remove_deck_highlight

    importlib.reload(remove_deck_highlight)

    # Check that hook was appended
    assert len(remove_deck_highlight.gui_hooks.webview_will_set_content) == 1

    handler = remove_deck_highlight.gui_hooks.webview_will_set_content[0]

    # Test with correct context
    web_content = MagicMock()
    web_content.head = ""
    web_content.body = ""

    # Correct context is an instance of the same type as mw.deckBrowser
    context = MockDeckBrowser()

    handler(web_content, context)

    assert "background-color: transparent !important;" in web_content.head
    assert "stripCurrent();" in web_content.body

    # Test with wrong context
    web_content_wrong = MagicMock()
    web_content_wrong.head = ""
    web_content_wrong.body = ""

    class WrongContext:
        pass

    context_wrong = WrongContext()  # not the same type

    handler(web_content_wrong, context_wrong)

    assert web_content_wrong.head == ""
    assert web_content_wrong.body == ""
