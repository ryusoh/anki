import sys
from unittest.mock import MagicMock, patch

# Mock aqt before import
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()
sys.modules['aqt.browser'] = MagicMock()

import highlight_search_matches.editor_integration as editor_int

def test_on_browser_did_search():
    ctx = MagicMock()
    ctx.search = "test_query"
    editor_int.on_browser_did_search(ctx)
    assert editor_int._last_search_query == "test_query"

def test_on_editor_did_load_note_not_browser():
    editor = MagicMock()

    # We will just patch isinstance in the editor_integration module
    with patch('highlight_search_matches.editor_integration.isinstance', return_value=False, create=True):
        editor_int.on_editor_did_load_note(editor)
    assert not editor.web.eval.called

def test_on_editor_did_load_note_no_terms():
    editor = MagicMock()
    editor.parentWindow.form.searchEdit.currentText.return_value = ""
    editor_int._last_search_query = ""

    with patch('highlight_search_matches.editor_integration.isinstance', return_value=True, create=True):
        editor_int.on_editor_did_load_note(editor)
    assert not editor.web.eval.called

def test_on_editor_did_load_note_with_terms():
    editor = MagicMock()
    editor.parentWindow.form.searchEdit.currentText.return_value = "hello"

    with patch('highlight_search_matches.editor_integration.isinstance', return_value=True, create=True), \
         patch('highlight_search_matches.editor_integration.extract_search_terms', return_value=['hello']):
        editor_int.on_editor_did_load_note(editor)
    assert editor.web.eval.called

def test_on_editor_did_load_note_exception():
    editor = MagicMock()
    editor.parentWindow.form.searchEdit.currentText.side_effect = Exception("error")
    editor_int._last_search_query = "hello"

    with patch('highlight_search_matches.editor_integration.isinstance', return_value=True, create=True), \
         patch('highlight_search_matches.editor_integration.extract_search_terms', return_value=['hello']):
        editor_int.on_editor_did_load_note(editor)
    assert editor.web.eval.called

def test_on_editor_did_load_note_js_exception():
    editor = MagicMock()
    editor.parentWindow.form.searchEdit.currentText.return_value = "hello"
    editor.web.eval.side_effect = Exception("js error")

    with patch('highlight_search_matches.editor_integration.isinstance', return_value=True, create=True), \
         patch('highlight_search_matches.editor_integration.extract_search_terms', return_value=['hello']):
        editor_int.on_editor_did_load_note(editor)
    assert editor.web.eval.called

def test_init_editor():
    with patch('highlight_search_matches.editor_integration.browser_did_search', MagicMock()) as b, \
         patch('highlight_search_matches.editor_integration.editor_did_load_note', MagicMock()) as e:
        editor_int.init_editor()
        assert b.append.called
        assert e.append.called
