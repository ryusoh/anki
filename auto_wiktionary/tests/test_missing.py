from unittest.mock import MagicMock, patch

import pytest

from auto_wiktionary import _apply_wiktionary


def test_apply_wiktionary_no_candidates():
    # Covers line 42-43: No word found, no candidates
    editor = MagicMock()
    with (
        patch("auto_wiktionary.detect_language", return_value="en"),
        patch("auto_wiktionary.fetch_wiktionary_html", return_value=""),
        patch("auto_wiktionary.get_wiktionary_candidates", return_value=[]),
        patch("auto_wiktionary.tooltip") as mock_tooltip,
    ):
        _apply_wiktionary(editor, "not_found")
        mock_tooltip.assert_called_with(
            "Word 'not_found' not found in en.wiktionary and no suggestions found."
        )


def test_apply_wiktionary_redirect_fetch_fails():
    # Covers line 52-57: Detect redirect but fetch fails
    editor = MagicMock()
    with (
        patch("auto_wiktionary.detect_language", return_value="ja"),
        patch(
            "auto_wiktionary.fetch_wiktionary_html", side_effect=["redirect_html", "Error: failed"]
        ),
        patch("auto_wiktionary.detect_kanji_redirect", return_value=("reading", ["reading"])),
        patch("auto_wiktionary.tooltip") as mock_tooltip,
    ):
        _apply_wiktionary(editor, "kanji")
        mock_tooltip.assert_called_with("Could not fetch redirected reading 'reading'.")


def test_apply_wiktionary_redirect_success_with_readings():
    # Covers line 61: inject_redirect_pronunciation
    editor = MagicMock()
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["Kanji", ""]
    editor.addMode = False

    with (
        patch("auto_wiktionary.detect_language", return_value="ja"),
        patch("auto_wiktionary.fetch_wiktionary_html", side_effect=["redirect_html", "valid_html"]),
        patch("auto_wiktionary.detect_kanji_redirect", return_value=("reading", ["reading"])),
        patch("auto_wiktionary.parse_wiktionary_html", return_value="<p>def</p>"),
        patch("auto_wiktionary.inject_redirect_pronunciation", return_value="<p>def injected</p>"),
    ):
        _apply_wiktionary(editor, "kanji")

    assert "def injected" in editor.note.fields[1]


def test_apply_wiktionary_none_note_post_fetch():
    # Covers line 68: editor.note is None after fetch
    editor = MagicMock()
    editor.note = None
    with (
        patch("auto_wiktionary.detect_language", return_value="ja"),
        patch("auto_wiktionary.fetch_wiktionary_html", return_value="valid_html"),
        patch("auto_wiktionary.detect_kanji_redirect", return_value=None),
        patch("auto_wiktionary.parse_wiktionary_html", return_value="<p>def</p>"),
    ):
        _apply_wiktionary(editor, "word")
        # should return early without error


def test_apply_wiktionary_flush_exception():
    # Covers line 90-93: flush exception
    editor = MagicMock()
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["Kanji", ""]
    editor.addMode = False
    editor.note.flush.side_effect = Exception("flush error")

    with (
        patch("auto_wiktionary.detect_language", return_value="ja"),
        patch("auto_wiktionary.fetch_wiktionary_html", return_value="valid_html"),
        patch("auto_wiktionary.detect_kanji_redirect", return_value=None),
        patch("auto_wiktionary.parse_wiktionary_html", return_value="<p>def</p>"),
    ):
        _apply_wiktionary(editor, "word")

    editor.loadNoteKeepingFocus.assert_called_once()
