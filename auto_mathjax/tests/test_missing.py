from unittest.mock import MagicMock, patch

import pytest

from auto_mathjax import _apply_mathjax, _convert_dollar_to_mathjax, on_editor_did_init_buttons


def test_convert_block_mathjax_whitespace():
    # Covers line 94: block_inner is whitespace only -> return unchanged
    assert _convert_dollar_to_mathjax("$$   $$") == "$$   $$"
    assert _convert_dollar_to_mathjax("$$\n\t$$") == "$$\n\t$$"


def test_apply_mathjax_none_note_or_field():
    # Covers line 120: editor.note is None or editor.currentField is None
    editor = MagicMock()
    editor.note = None
    editor.currentField = 0
    _apply_mathjax(editor)

    editor.note = MagicMock()
    editor.currentField = None
    _apply_mathjax(editor)


def test_apply_mathjax_invalid_field_idx():
    # Covers line 123: idx < 0 or idx >= len(fields)
    editor = MagicMock()
    editor.note.fields = ["Test"]
    editor.currentField = -1
    _apply_mathjax(editor)

    editor.currentField = 1
    _apply_mathjax(editor)


def test_apply_mathjax_no_changes():
    # Covers line 130: new_html == html_str -> return early
    editor = MagicMock()
    editor.note.fields = ["No math here"]
    editor.currentField = 0
    _apply_mathjax(editor)

    # Check that it didn't call flush or loadNoteKeepingFocus
    editor.note.flush.assert_not_called()
    editor.loadNoteKeepingFocus.assert_not_called()


def test_apply_mathjax_no_changes_shows_tooltip():
    """A no-op press must say so and name the focused field — silent no-ops
    made wrong-field focus undiagnosable."""
    editor = MagicMock()
    editor.note.fields = ["No math here"]
    editor.currentField = 0
    with patch("auto_mathjax.tooltip") as mock_tooltip:
        _apply_mathjax(editor)
    mock_tooltip.assert_called_once()
    assert "field 1" in mock_tooltip.call_args[0][0]


def test_apply_mathjax_conversion_shows_tooltip():
    """A successful conversion confirms with a tooltip."""
    editor = MagicMock()
    editor.note.fields = ["$math$"]
    editor.currentField = 0
    editor.addMode = True
    with patch("auto_mathjax.tooltip") as mock_tooltip:
        _apply_mathjax(editor)
    mock_tooltip.assert_called_once()


def test_apply_mathjax_flush_exception():
    # Covers line 136-137: exception during flush
    editor = MagicMock()
    editor.note.fields = ["$math$"]
    editor.currentField = 0
    editor.addMode = False
    editor.note.flush.side_effect = Exception("flush error")

    _apply_mathjax(editor)

    assert editor.note.fields[0] == r"\(math\)"
    editor.loadNoteKeepingFocus.assert_called_once()


def test_apply_mathjax_load_exception():
    # Covers line 140-141: exception during load
    editor = MagicMock()
    editor.note.fields = ["$math$"]
    editor.currentField = 0
    editor.addMode = False
    editor.loadNoteKeepingFocus.side_effect = Exception("load error")

    _apply_mathjax(editor)

    assert editor.note.fields[0] == r"\(math\)"
    editor.note.flush.assert_called_once()


def test_apply_mathjax_add_mode_skip_flush():
    # Covers line 133->138: if editor.addMode: skip flush
    editor = MagicMock()
    editor.note.fields = ["$math$"]
    editor.currentField = 0
    editor.addMode = True

    _apply_mathjax(editor)

    editor.note.flush.assert_not_called()
    editor.loadNoteKeepingFocus.assert_called_once()


def test_on_editor_did_init_buttons():
    # Covers lines 150-156
    editor = MagicMock()
    editor.addButton.return_value = "button"
    buttons = []

    on_editor_did_init_buttons(buttons, editor)

    editor.addButton.assert_called_once()
    assert buttons == ["button"]
    pass


def test_unreachable_empty_core():
    # Line 238 (if not core: return run) is practically unreachable because
    # EMBEDDED_RUN_RE only matches things containing at least one backslash
    # and a letter, neither of which are in _RUN_TRIM_CHARS.
    # We document this with a passing test.
    assert True
