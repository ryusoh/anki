import importlib
import sys
from unittest.mock import MagicMock

import pytest

# Mock dependencies before importing the editor_integration
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.browser'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()


class DummyBrowser:
    pass


sys.modules['aqt.browser'].Browser = DummyBrowser

import highlight_search_matches.editor_integration as ei

ei.Browser = DummyBrowser


def test_on_browser_did_search():
    context = MagicMock()
    context.search = "test search"
    ei.on_browser_did_search(context)
    assert ei._last_search_query == "test search"


def test_on_editor_did_load_note_not_browser():
    editor = MagicMock()
    editor.parentWindow = MagicMock()
    ei.on_editor_did_load_note(editor)
    editor.web.eval.assert_not_called()


def test_on_editor_did_load_note_browser_no_terms():
    editor = MagicMock()
    browser = DummyBrowser()
    browser.form = MagicMock()
    browser.form.searchEdit.currentText.return_value = ""
    browser.form.searchEdit.text.return_value = ""
    editor.parentWindow = browser
    ei._last_search_query = ""
    ei.on_editor_did_load_note(editor)
    editor.web.eval.assert_not_called()


def test_on_editor_did_load_note_browser_with_terms():
    editor = MagicMock()
    browser = DummyBrowser()
    browser.form = MagicMock()
    browser.form.searchEdit.currentText.return_value = "apple"
    editor.parentWindow = browser
    ei.on_editor_did_load_note(editor)
    editor.web.eval.assert_called_once()


def test_on_editor_did_load_note_browser_with_terms_fallback_last_query():
    editor = MagicMock()
    browser = DummyBrowser()
    browser.form = MagicMock()
    browser.form.searchEdit.currentText.return_value = ""
    browser.form.searchEdit.text.return_value = ""
    editor.parentWindow = browser
    ei._last_search_query = "banana"
    ei.on_editor_did_load_note(editor)
    editor.web.eval.assert_called_once()


def test_on_editor_did_load_note_eval_exception(capsys):
    editor = MagicMock()
    browser = DummyBrowser()
    browser.form = MagicMock()
    browser.form.searchEdit.currentText.return_value = "apple"
    editor.parentWindow = browser
    editor.web.eval.side_effect = Exception("test error")
    ei.on_editor_did_load_note(editor)
    editor.web.eval.assert_called_once()
    captured = capsys.readouterr()
    assert "Error evaluating JS" in captured.out


def test_on_editor_did_load_note_search_edit_exception(capsys):
    editor = MagicMock()
    browser = DummyBrowser()
    type(browser).form = property(lambda self: (_ for _ in ()).throw(Exception("test error")))
    editor.parentWindow = browser
    ei._last_search_query = "pear"
    ei.on_editor_did_load_note(editor)
    editor.web.eval.assert_called_once()
    captured = capsys.readouterr()
    assert "Error getting search edit text" in captured.out


def test_init_editor():
    ei.init_editor()
    ei.browser_did_search.append.assert_called_with(ei.on_browser_did_search)
    ei.editor_did_load_note.append.assert_called_with(ei.on_editor_did_load_note)


import highlight_search_matches.anki_integration as ai
from highlight_search_matches.anki_integration import init_addon, on_browser_did_search_filter


class MockNote:
    def __init__(self, note_id, fields):
        self.id = note_id
        self.fields = fields


class MockCard:
    def __init__(self, note):
        self._note = note

    def note(self):
        return self._note


def test_on_browser_did_search_filter_no_ids():
    context = MagicMock()
    context.ids = []
    on_browser_did_search_filter(context)
    assert context.ids == []


def test_on_browser_did_search_filter_no_terms():
    context = MagicMock()
    context.ids = [1, 2]
    context.search = "deck:Default"
    on_browser_did_search_filter(context)
    assert context.ids == [1, 2]


def test_on_browser_did_search_filter_wildcard():
    context = MagicMock()
    context.ids = [1, 2]
    context.search = "app*"
    on_browser_did_search_filter(context)
    assert context.ids == [1, 2]


def test_on_browser_did_search_filter_notes_mode(monkeypatch):
    context = MagicMock()
    context.ids = [1, 2, 3]
    context.search = "bsp"
    context.browser.table.is_notes_mode.return_value = True

    note1 = MockNote(1, ["apple pie bsp"])
    note2 = MockNote(2, ["&nbsp;"])

    def mock_get_note(item_id):
        if item_id == 1:
            return note1
        elif item_id == 2:
            return note2
        elif item_id == 3:
            return note1

    context.browser.col.get_note = mock_get_note

    on_browser_did_search_filter(context)
    assert context.ids == [1, 3]


def test_on_browser_did_search_filter_cards_mode_all_kept(monkeypatch):
    context = MagicMock()
    context.ids = [1]
    context.search = "bsp"
    context.browser.table.is_notes_mode.return_value = False

    note1 = MockNote(1, ["apple pie bsp"])

    def mock_get_card(item_id):
        return MockCard(note1)

    context.browser.col.get_card = mock_get_card

    on_browser_did_search_filter(context)
    assert context.ids == [1]


def test_on_browser_did_search_filter_exception(monkeypatch, capsys):
    context = MagicMock()
    context.ids = [1, 2]
    context.search = "bsp"
    context.browser.table.is_notes_mode.side_effect = Exception("test error")

    on_browser_did_search_filter(context)
    assert context.ids == [1, 2]
    captured = capsys.readouterr()
    assert "[hsm] search result filter error" in captured.out


def test_init_addon():
    init_addon()
    ai.browser_did_search.append.assert_called_with(on_browser_did_search_filter)


from highlight_search_matches.core import extract_search_terms, note_has_real_match


def test_note_has_real_match_no_match():
    assert note_has_real_match(["some normal text"], ["missing"]) is False


def test_note_has_real_match_image_src():
    assert note_has_real_match(['<img src="bsp.jpg">'], ["bsp"]) is True


def test_note_has_real_match_html_tag_stripping():
    assert note_has_real_match(['<div class="test">content</div>'], ["test"]) is False
    assert note_has_real_match(['<div class="test">content</div>'], ["content"]) is True


def test_extract_search_terms_skip_if_not_query():
    assert extract_search_terms(None) == []


def test_extract_search_terms_empty_word():
    assert extract_search_terms("()") == []


def test_init_log_not_pytest():
    from unittest.mock import mock_open, patch

    import highlight_search_matches

    orig_aqt = sys.modules.get("aqt")
    orig_pytest = sys.modules.get("pytest")

    if "aqt" in sys.modules:
        del sys.modules["aqt"]
    if "pytest" in sys.modules:
        del sys.modules["pytest"]

    try:
        importlib.reload(highlight_search_matches)
        with patch("builtins.open", mock_open()) as mocked_file:
            highlight_search_matches.log("test_message")
            mocked_file.assert_not_called()
    finally:
        if orig_aqt:
            sys.modules["aqt"] = orig_aqt
        if orig_pytest:
            sys.modules["pytest"] = orig_pytest
        importlib.reload(highlight_search_matches)
