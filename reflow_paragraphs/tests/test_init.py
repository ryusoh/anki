import importlib
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from test_reflow import DICTIONARY_FIELD, PDF_PARAGRAPH, PDF_PARAGRAPH_REFLOWED


def _load():
    """Reload the addon against fresh aqt mocks with a real hook list."""
    aqt = MagicMock()
    aqt.gui_hooks.editor_did_init_buttons = []
    sys.modules['aqt'] = aqt
    sys.modules['aqt.gui_hooks'] = aqt.gui_hooks
    sys.modules['aqt.editor'] = MagicMock()
    sys.modules['aqt.utils'] = MagicMock()
    import reflow_paragraphs
    importlib.reload(reflow_paragraphs)
    return reflow_paragraphs


def _editor(fields, field_names, current_field=None):
    editor = MagicMock()
    editor.note.fields = list(fields)
    editor.note.keys.return_value = list(field_names)
    editor.currentField = current_field
    editor.addMode = True
    # saveNow(cb) runs the callback immediately, like Anki does after a save.
    editor.saveNow.side_effect = lambda cb: cb()
    return editor


def test_button_hook_registered():
    mod = _load()
    assert mod.on_editor_did_init_buttons in mod.gui_hooks.editor_did_init_buttons


def test_button_reflows_focused_field():
    mod = _load()
    editor = _editor(
        fields=["word", PDF_PARAGRAPH.replace("\n", "<br>")],
        field_names=["Front", "Back"],
        current_field=1,
    )
    mod.on_reflow_paragraphs(editor)
    assert editor.note.fields[1] == PDF_PARAGRAPH_REFLOWED
    editor.loadNoteKeepingFocus.assert_called_once()


def test_button_falls_back_to_back_field_and_spares_dictionary_format():
    mod = _load()
    dictionary_html = DICTIONARY_FIELD.replace("\n", "<br>")
    editor = _editor(
        fields=["discharge", dictionary_html],
        field_names=["Front", "Back"],
        current_field=None,
    )
    mod.on_reflow_paragraphs(editor)
    assert editor.note.fields[1] == dictionary_html
