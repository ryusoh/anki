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

def test_on_reflow_paragraphs_no_note():
    mod = _load()
    editor = MagicMock()
    editor.note = None
    mod.on_reflow_paragraphs(editor)
    editor.saveNow.assert_not_called()

def test_apply_reflow_no_note():
    mod = _load()
    editor = MagicMock()
    editor.note = None
    mod._apply_reflow(editor)
    sys.modules["aqt.utils"].tooltip.assert_not_called()

def test_apply_reflow_no_target_field():
    mod = _load()
    editor = MagicMock()
    editor.note.keys.return_value = ["Front", "Tags"]
    editor.currentField = None
    mod._apply_reflow(editor)
    sys.modules["aqt.utils"].tooltip.assert_called_with("No field focused and no 'Back' field found.")

def test_apply_reflow_nothing_to_reflow():
    mod = _load()
    editor = MagicMock()
    editor.note.fields = ["Front", "Already reflowed"]
    editor.note.keys.return_value = ["Front", "Back"]
    editor.currentField = 1
    from unittest.mock import patch
    from unittest.mock import patch
    with patch.object(mod, 'reflow_field_html', return_value="Already reflowed"):
        mod._apply_reflow(editor)
        sys.modules["aqt.utils"].tooltip.assert_called_with("Nothing to reflow.")

def test_apply_reflow_exceptions_handled(capsys):
    mod = _load()
    editor = MagicMock()
    editor.note.fields = ["Front", "Needs reflow<br>lines"]
    editor.note.keys.return_value = ["Front", "Back"]
    editor.currentField = 1
    editor.addMode = False

    def mock_flush():
        raise Exception("Flush Error")
    editor.note.flush.side_effect = mock_flush

    def mock_load():
        raise Exception("Load Error")
    editor.loadNoteKeepingFocus.side_effect = mock_load

    from unittest.mock import patch
    from unittest.mock import patch
    with patch.object(mod, 'reflow_field_html', return_value="Needs reflow lines"):
        mod._apply_reflow(editor)
        sys.modules["aqt.utils"].tooltip.assert_called_with("Reflowed hard-wrapped paragraph.")
        captured = capsys.readouterr()
        assert "Error flushing note: Flush Error" in captured.out
        assert "Error loading note: Load Error" in captured.out

        assert "Error flushing note: Flush Error" in captured.out
        assert "Error loading note: Load Error" in captured.out



def test_apply_reflow_exceptions_handled_flush_and_load(capsys):
    mod = _load()
    editor = MagicMock()
    editor.note.fields = ["Front", "Needs reflow<br>lines"]
    editor.note.keys.return_value = ["Front", "Back"]
    editor.currentField = 1
    editor.addMode = False

    def mock_flush():
        raise Exception("Flush Error")
    editor.note.flush.side_effect = mock_flush

    def mock_load():
        raise Exception("Load Error")
    editor.loadNoteKeepingFocus.side_effect = mock_load

    from unittest.mock import patch
    with patch.object(mod, 'reflow_field_html', return_value="Needs reflow lines"):
        mod._apply_reflow(editor)
        sys.modules["aqt.utils"].tooltip.assert_called_with("Reflowed hard-wrapped paragraph.")
        captured = capsys.readouterr()
        assert "Error flushing note: Flush Error" in captured.out
        assert "Error loading note: Load Error" in captured.out


def test_apply_reflow_exceptions_handled_flush_and_load_not_add_mode(capsys):
    mod = _load()
    editor = MagicMock()
    editor.note.fields = ["Front", "Needs reflow<br>lines"]
    editor.note.keys.return_value = ["Front", "Back"]
    editor.currentField = 1
    editor.addMode = True

    def mock_load():
        raise Exception("Load Error 2")
    editor.loadNoteKeepingFocus.side_effect = mock_load

    from unittest.mock import patch
    with patch.object(mod, 'reflow_field_html', return_value="Needs reflow lines"):
        mod._apply_reflow(editor)
        sys.modules["aqt.utils"].tooltip.assert_called_with("Reflowed hard-wrapped paragraph.")
        captured = capsys.readouterr()
        assert "Error flushing note:" not in captured.out
        assert "Error loading note: Load Error 2" in captured.out

def test_on_editor_did_init_buttons_add_button():
    mod = _load()
    editor = MagicMock()
    editor.addButton.return_value = "button"
    buttons = []

    mod.on_editor_did_init_buttons(buttons, editor)

    editor.addButton.assert_called_once()
    assert buttons == ["button"]
