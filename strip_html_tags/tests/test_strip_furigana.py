"""Tests for the furigana-strip feature of the Strip HTML Tags addon.

Furigana in Anki fields is <ruby>base<rt>reading</rt></ruby> (optionally with
<rp>(</rp> parens for non-ruby browsers). Stripping keeps the base text and
all other formatting, and drops only the readings. Like the HTML strip, it
acts on the selected text when there is a selection, else the whole field.
"""

from unittest.mock import MagicMock

from editor_test_double import Editor  # noqa: F401  (installs the aqt mocks)

from strip_html_tags import _strip_furigana, _strip_furigana_selection, on_js_message

# ---- _strip_furigana unit tests ----


def test_strip_furigana_basic_ruby():
    assert _strip_furigana('<ruby>漢字<rt>かんじ</rt></ruby>') == '漢字'


def test_strip_furigana_removes_rp_parens():
    html = '<ruby>漢字<rp>(</rp><rt>かんじ</rt><rp>)</rp></ruby>'
    assert _strip_furigana(html) == '漢字'


def test_strip_furigana_keeps_other_formatting():
    html = '<div><b><ruby>毎日<rt>まいにち</rt></ruby></b> <i>plain</i></div>'
    assert _strip_furigana(html) == '<div><b>毎日</b> <i>plain</i></div>'


def test_strip_furigana_ruby_with_attributes():
    html = '<ruby class="furigana">食<rt style="x">た</rt></ruby>べる'
    assert _strip_furigana(html) == '食べる'


def test_strip_furigana_multiple_ruby_in_line():
    html = '<ruby>私<rt>わたし</rt></ruby>は<ruby>学生<rt>がくせい</rt></ruby>です'
    assert _strip_furigana(html) == '私は学生です'


def test_strip_furigana_no_ruby_is_noop():
    html = '<div><b>just bold</b></div>'
    assert _strip_furigana(html) == html


# ---- _strip_furigana_selection tests ----


def test_furigana_selection_strips_only_selected_ruby():
    # The browser's getSelection().toString() includes the ruby reading inline,
    # so selecting the word yields base+reading concatenated.
    html = '<div><ruby>漢字<rt>かんじ</rt></ruby>です <ruby>私<rt>わたし</rt></ruby></div>'
    res = _strip_furigana_selection(html, '漢字かんじ')
    assert res == '<div>漢字です <ruby>私<rt>わたし</rt></ruby></div>'


def test_furigana_selection_spanning_ruby_and_tail():
    html = '<div><ruby>漢字<rt>かんじ</rt></ruby>です</div>'
    res = _strip_furigana_selection(html, '漢字かんじです')
    assert res == '<div>漢字です</div>'


def test_furigana_selection_inside_reading_expands_to_whole_ruby():
    # Selecting only part of the base text must not leave a half-stripped
    # <ruby> behind — the range expands to the whole element.
    html = '<div><ruby>漢字<rt>かんじ</rt></ruby>です</div>'
    res = _strip_furigana_selection(html, '漢字')
    assert res == '<div>漢字です</div>'


def test_furigana_selection_without_ruby_leaves_field_unchanged():
    html = '<div><b>plain text</b></div>'
    res = _strip_furigana_selection(html, 'plain text')
    assert res == html


def test_furigana_selection_unmappable_returns_none():
    html = '<div><ruby>漢字<rt>かんじ</rt></ruby></div>'
    assert _strip_furigana_selection(html, 'not in the field') is None


# ---- pycmd acceptance tests ----


def _editor_with_fields(fields, current_field=0):
    editor = Editor()
    editor.note = MagicMock()
    editor.note.fields = list(fields)
    editor.currentField = current_field
    editor.addMode = False
    editor.loadNoteKeepingFocus = MagicMock()
    return editor


def test_furigana_button_with_no_selection_strips_whole_field():
    editor = _editor_with_fields(
        [
            '<div><ruby>私<rt>わたし</rt></ruby>は<ruby>学生<rt>がくせい</rt></ruby>です</div>',
            'keep <rt>me</rt>',
        ]
    )

    handled = on_js_message((False, None), 'stripFuriAll', editor)

    assert handled == (True, None)
    assert editor.note.fields[0] == '<div>私は学生です</div>'
    assert editor.note.fields[1] == 'keep <rt>me</rt>'  # other field untouched


def test_furigana_button_with_selection_strips_only_selection():
    editor = _editor_with_fields(
        ['<div><ruby>漢字<rt>かんじ</rt></ruby>です <ruby>私<rt>わたし</rt></ruby></div>']
    )

    handled = on_js_message((False, None), 'stripFuriSel:漢字かんじ', editor)

    assert handled == (True, None)
    assert editor.note.fields[0] == '<div>漢字です <ruby>私<rt>わたし</rt></ruby></div>'


def test_furigana_button_on_field_without_ruby_is_noop():
    editor = _editor_with_fields(['<div><b>no furigana here</b></div>'])

    handled = on_js_message((False, None), 'stripFuriAll', editor)

    assert handled == (True, None)
    assert editor.note.fields[0] == '<div><b>no furigana here</b></div>'
    editor.note.flush.assert_not_called()
    editor.loadNoteKeepingFocus.assert_not_called()


def test_furigana_button_unmappable_selection_falls_back_to_whole_field():
    editor = _editor_with_fields(['<div><ruby>漢字<rt>かんじ</rt></ruby>です</div>'])

    handled = on_js_message((False, None), 'stripFuriSel:garbage', editor)

    assert handled == (True, None)
    assert editor.note.fields[0] == '<div>漢字です</div>'
