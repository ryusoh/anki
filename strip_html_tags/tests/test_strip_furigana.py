"""Furigana handling in the strip pipeline of the Strip HTML Tags addon.

Stripping HTML from <ruby>base<rt>reading</rt></ruby> must drop the readings
too — otherwise the tags vanish but the readings stay behind as stray text
(彼女かのじょ… instead of 彼女…). This applies to the whole-field strip and
to selection strips, via the same single strip button.
"""

from unittest.mock import MagicMock

from editor_test_double import Editor  # noqa: F401  (installs the aqt mocks)

from strip_html_tags import _render_text, _strip_furigana, _strip_selection, on_js_message

REAL_FIELD = '<ruby>彼女<rt>かのじょ</rt></ruby>の<ruby>語学<rt>ごがく</rt></ruby><ruby>力<rt>りょく</rt></ruby>は<ruby>日<rt>にち</rt></ruby><ruby>一<rt>いち</rt></ruby><ruby>日<rt>にち</rt></ruby>と<ruby>育<rt>そだ</rt></ruby>っていく。'


# ---- _strip_furigana helper unit tests ----


def test_strip_furigana_basic_ruby():
    assert _strip_furigana('<ruby>漢字<rt>かんじ</rt></ruby>') == '漢字'


def test_strip_furigana_removes_rp_parens_and_attrs():
    html = '<ruby class="furi">漢字<rp>(</rp><rt style="x">かんじ</rt><rp>)</rp></ruby>'
    assert _strip_furigana(html) == '漢字'


def test_strip_furigana_no_ruby_is_noop():
    html = '<div><b>just bold</b></div>'
    assert _strip_furigana(html) == html


# ---- whole-field strip drops readings ----


def test_render_text_drops_furigana_readings():
    assert _render_text(REAL_FIELD) == '彼女の語学力は日一日と育っていく。'


def test_render_text_furigana_mixed_with_formatting():
    html = '<div><b><ruby>毎日<rt>まいにち</rt></ruby></b> <i>plain</i></div>'
    assert _render_text(html) == '毎日 plain'


# ---- selection strip drops readings only in the selection ----


def test_selection_strip_drops_readings_keeps_unselected_ruby():
    # The browser's getSelection().toString() includes the ruby reading inline,
    # so selecting the word yields base+reading concatenated.
    html = '<div><ruby>漢字<rt>かんじ</rt></ruby>です <ruby>私<rt>わたし</rt></ruby></div>'
    res = _strip_selection(html, '漢字かんじ')
    assert res == '<div>漢字です <ruby>私<rt>わたし</rt></ruby></div>'


def test_selection_strip_spanning_ruby_and_tail():
    html = '<div><ruby>漢字<rt>かんじ</rt></ruby>です</div>'
    res = _strip_selection(html, '漢字かんじです')
    assert res == '<div>漢字です</div>'


def test_selection_strip_partial_base_expands_to_whole_ruby():
    # Selecting only the base text must not strand the <rt> reading behind.
    html = '<div><ruby>漢字<rt>かんじ</rt></ruby>です</div>'
    res = _strip_selection(html, '漢字')
    assert res == '<div>漢字です</div>'


def test_selection_strip_whole_ruby_line():
    res = _strip_selection(
        REAL_FIELD, '彼女かのじょの語学ごがく力りょくは日にち一いち日にちと育そだっていく。'
    )
    assert res == '彼女の語学力は日一日と育っていく。'


# ---- pycmd acceptance tests (same single strip button) ----


def _editor_with_fields(fields, current_field=0):
    editor = Editor()
    editor.note = MagicMock()
    editor.note.fields = list(fields)
    editor.currentField = current_field
    editor.addMode = False
    editor.loadNoteKeepingFocus = MagicMock()
    return editor


def test_strip_button_no_selection_drops_all_readings():
    editor = _editor_with_fields([REAL_FIELD])

    handled = on_js_message((False, None), 'stripHtmlAll', editor)

    assert handled == (True, None)
    assert editor.note.fields[0] == '彼女の語学力は日一日と育っていく。'


def test_strip_button_with_selection_drops_readings_in_selection_only():
    editor = _editor_with_fields([REAL_FIELD])

    handled = on_js_message((False, None), 'stripHtmlSel:語学ごがく力りょく', editor)

    assert handled == (True, None)
    assert editor.note.fields[0] == (
        '<ruby>彼女<rt>かのじょ</rt></ruby>の語学力は'
        '<ruby>日<rt>にち</rt></ruby><ruby>一<rt>いち</rt></ruby><ruby>日<rt>にち</rt></ruby>'
        'と<ruby>育<rt>そだ</rt></ruby>っていく。'
    )
