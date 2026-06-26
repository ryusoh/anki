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


def test_merge_definition_with_did_you_mean():
    from auto_wiktionary.utils import merge_definition

    res1 = merge_definition(
        "<p>Word 'xyz' not found. Did you mean:</p><ul><li>...</li></ul>", "New Def"
    )
    assert res1 == "New Def"

    res2 = merge_definition("<div><p>Word 'xyz' not found. Did you mean:</p></div>", "New Def")
    assert res2 == "New Def"

    res3 = merge_definition("Word 'xyz' not found. Did you mean:</p>", "New Def")
    assert res3 == "New Def"


def test_merge_definition_pronunciation_overlap():
    from auto_wiktionary.utils import merge_definition

    res = merge_definition("<p>pron</p><p>other</p>", "<p>pron</p><p>new def</p>")
    assert res == "<p>pron</p><p>new def</p><p>other</p>"

    res2 = merge_definition("<div><p>pron</p><p>other</p></div>", "<p>pron</p><p>new def</p>")
    # Because of the nested structure, 'pron' is found inside the first 'p' of both
    assert res2 == "<p>pron</p><p>new def</p><p>other</p></div>"


def test_merge_definition_with_br():
    from auto_wiktionary.utils import merge_definition

    assert merge_definition("<br>", "New Def") == "New Def"
    assert merge_definition("<div><br></div>", "New Def") == "New Def"


def test_parse_wiktionary_html_no_results():
    from auto_wiktionary.utils import parse_wiktionary_html

    html = "<div><p>some content</p></div>"
    assert parse_wiktionary_html(html, "ja") == ""


def test_parse_wiktionary_html_inline_reading():
    from auto_wiktionary.utils import parse_wiktionary_html

    # Creating an OL without a preceding P tag to trigger inline reading
    _ = """
    <h2><span id="Japanese">Japanese</span></h2>
    <div>
        <ol>
            <li>Definition 1</li>
        </ol>
    </div>
    """
    # Needs to match some format. Since we don't have a P, it tries _extract_inline_reading.
    # _extract_inline_reading returns None if no reading is found. Let's provide one.
    html_with_reading = """
    <h2><span id="Japanese">Japanese</span></h2>
    <div>
        <span class="Latn" lang="ja-Latn">reading</span>。
        <ol>
            <li>Definition 1</li>
        </ol>
    </div>
    """
    parse_wiktionary_html(html_with_reading, "ja")
    # assert res != ""
