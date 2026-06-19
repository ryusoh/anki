import os
import sys
from unittest.mock import MagicMock, patch

# Mock aqt before import
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()

import auto_wiktionary
from auto_wiktionary import (
    _apply_wiktionary,
    _on_selection_result,
    _use_front_field,
    on_auto_wiktionary,
    on_editor_did_init_buttons,
)


def test_apply_wiktionary_no_text():
    editor = MagicMock()
    with patch("auto_wiktionary.clean_html_text", return_value=""):
        _apply_wiktionary(editor, "")
    assert sys.modules['aqt.utils'].tooltip.called


def test_apply_wiktionary_no_back_field():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["front"]
    with (
        patch("auto_wiktionary.clean_html_text", return_value="test"),
        patch("auto_wiktionary.detect_language", return_value="en"),
        patch("auto_wiktionary.fetch_wiktionary_html", return_value="html"),
        patch("auto_wiktionary.parse_wiktionary_html", return_value="parsed"),
    ):
        _apply_wiktionary(editor, "test")
    assert sys.modules['aqt.utils'].tooltip.called


def test_apply_wiktionary_success():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["", ""]
    with (
        patch("auto_wiktionary.clean_html_text", return_value="test"),
        patch("auto_wiktionary.detect_language", return_value="en"),
        patch("auto_wiktionary.fetch_wiktionary_html", return_value="html"),
        patch("auto_wiktionary.parse_wiktionary_html", return_value="parsed_html"),
    ):
        _apply_wiktionary(editor, "test")
    assert "parsed_html" in editor.note.fields[1]
    assert editor.loadNoteKeepingFocus.called
    assert sys.modules['aqt.utils'].tooltip.called


def test_on_auto_wiktionary_no_note():
    editor = MagicMock()
    editor.note = None
    on_auto_wiktionary(editor)
    assert not editor.web.evalWithCallback.called


def test_on_auto_wiktionary_with_note():
    editor = MagicMock()
    editor.note = MagicMock()
    on_auto_wiktionary(editor)
    assert editor.web.evalWithCallback.called


def test_on_selection_result_with_selection():
    editor = MagicMock()
    _on_selection_result(editor, "selected text")
    assert editor.saveNow.called


def test_on_selection_result_no_selection():
    editor = MagicMock()
    _on_selection_result(editor, "")
    assert editor.saveNow.called


def test_use_front_field_no_note():
    editor = MagicMock()
    editor.note = None
    _use_front_field(editor)
    # Shouldn't raise


def test_use_front_field_no_front_field():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["NotFront"]
    _use_front_field(editor)
    assert sys.modules['aqt.utils'].tooltip.called


def test_use_front_field_success():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["Front"]
    editor.note.fields = ["front text"]
    with patch("auto_wiktionary._apply_wiktionary") as mock_apply:
        _use_front_field(editor)
        mock_apply.assert_called_with(editor, "front text")


def test_on_editor_did_init_buttons():
    editor = MagicMock()
    on_editor_did_init_buttons([], editor)
    assert editor.addButton.called


def test_apply_wiktionary_unsupported_language():
    editor = MagicMock()
    with (
        patch("auto_wiktionary.clean_html_text", return_value="test"),
        patch("auto_wiktionary.detect_language", return_value="unsupported"),
    ):
        _apply_wiktionary(editor, "test")
    assert sys.modules['aqt.utils'].tooltip.called


def test_apply_wiktionary_no_html_found():
    editor = MagicMock()
    with (
        patch("auto_wiktionary.clean_html_text", return_value="test"),
        patch("auto_wiktionary.detect_language", return_value="en"),
        patch("auto_wiktionary.fetch_wiktionary_html", return_value=""),
    ):
        _apply_wiktionary(editor, "test")
    assert sys.modules['aqt.utils'].tooltip.called


def test_apply_wiktionary_parse_failure():
    editor = MagicMock()
    with (
        patch("auto_wiktionary.clean_html_text", return_value="test"),
        patch("auto_wiktionary.detect_language", return_value="en"),
        patch("auto_wiktionary.fetch_wiktionary_html", return_value="html"),
        patch("auto_wiktionary.parse_wiktionary_html", return_value=""),
    ):
        _apply_wiktionary(editor, "test")
    assert sys.modules['aqt.utils'].tooltip.called


def test_apply_wiktionary_exception():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["", ""]
    editor.loadNoteKeepingFocus.side_effect = Exception("test error")
    with (
        patch("auto_wiktionary.clean_html_text", return_value="test"),
        patch("auto_wiktionary.detect_language", return_value="en"),
        patch("auto_wiktionary.fetch_wiktionary_html", return_value="html"),
        patch("auto_wiktionary.parse_wiktionary_html", return_value="parsed_html"),
    ):
        _apply_wiktionary(editor, "test")
    # Coverage should handle the exception catch block silently
