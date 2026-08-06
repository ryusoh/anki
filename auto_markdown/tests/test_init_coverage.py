from unittest.mock import MagicMock, patch

import pytest

from auto_markdown import _apply_markdown, on_auto_markdown, on_editor_did_init_buttons


def test_apply_markdown_note_none():
    editor = MagicMock()
    editor.note = None
    _apply_markdown(editor)


def test_apply_markdown_no_changes():
    editor = MagicMock()
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["no markdown", "no markdown"]
    with patch("auto_markdown.tooltip") as mock_tooltip:
        _apply_markdown(editor)
    mock_tooltip.assert_called_with("No markdown to convert.")


def test_apply_markdown_with_changes_exception():
    editor = MagicMock()
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["**bold**", "no markdown"]
    editor.addMode = False
    editor.note.flush.side_effect = Exception("flush error")
    with patch("auto_markdown.tooltip") as mock_tooltip:
        _apply_markdown(editor)
    editor.loadNoteKeepingFocus.assert_called_once()
    mock_tooltip.assert_called_with("Converted markdown to HTML.")


def test_apply_markdown_with_changes_exception_load():
    editor = MagicMock()
    editor.note.keys.return_value = ["Front"]
    editor.note.fields = ["**bold**"]
    editor.addMode = False
    editor.loadNoteKeepingFocus.side_effect = Exception("load error")
    with patch("auto_markdown.tooltip") as mock_tooltip:
        _apply_markdown(editor)
    editor.note.flush.assert_called_once()
    mock_tooltip.assert_called_with("Converted markdown to HTML.")


def test_on_auto_markdown_none():
    editor = MagicMock()
    editor.note = None
    on_auto_markdown(editor)


def test_on_editor_did_init_buttons():
    editor = MagicMock()
    buttons = []
    on_editor_did_init_buttons(buttons, editor)
    editor.addButton.assert_called_once()


def test_apply_markdown_addMode_true():
    editor = MagicMock()
    editor.note.keys.return_value = ["Front"]
    editor.note.fields = ["**bold**"]
    editor.addMode = True
    with patch("auto_markdown.tooltip"):
        _apply_markdown(editor)
    editor.note.flush.assert_not_called()
    editor.loadNoteKeepingFocus.assert_called_once()


def test_apply_markdown_other_field():
    """Fields with names other than Front/Back are also converted."""
    editor = MagicMock()
    editor.note.keys.return_value = ["Other"]
    editor.note.fields = ["**bold**"]
    editor.addMode = False
    with patch("auto_markdown.tooltip") as mock_tooltip:
        _apply_markdown(editor)
    assert editor.note.fields[0] == "<b>bold</b>"
    mock_tooltip.assert_called_with("Converted markdown to HTML.")
