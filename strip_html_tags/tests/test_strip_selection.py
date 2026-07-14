import sys
from unittest.mock import MagicMock


# Mock out aqt entirely so we can import the module outside of Anki
class Editor:
    pass


sys.modules['aqt'] = MagicMock()
mock_editor_mod = MagicMock()
mock_editor_mod.Editor = Editor
sys.modules['aqt.editor'] = mock_editor_mod

from strip_html_tags import _render_text, _strip_field, _strip_selection, on_js_message


# Test Case 1: Partial line selection shouldn't strip surrounding tags
def test_partial_selection():
    html = '<h3><span style="font-size: 20px;">The quick brown fox jumps over the lazy dog.</span><br></h3><div>Some other text block.</div>'
    selected = "brown fox jumps"

    res = _strip_selection(html, selected)
    assert res == html


# Test Case 2: Inner tags inside partial selection SHOULD be stripped
def test_inner_tags_stripped():
    html = '<h3><span style="font-size: 20px;">The quick </span><b>brown fox</b><span style="font-size: 20px;"> jumps over the lazy dog.</span><br></h3><div>Some other text block.</div>'
    selected = "The quick brown fox jumps over the lazy dog."

    res = _strip_selection(html, selected)
    # "The quick brown fox jumps over the lazy dog." is fully enclosed by the <h3> tag.
    # The script will now strip the <h3> and the <br> inside it, and replace the whole block
    # with a generic <div> to prevent merging with adjacent blocks.
    expected = (
        '<div>The quick brown fox jumps over the lazy dog.</div><div>Some other text block.</div>'
    )

    assert res == expected


# Test Case 3: Invisible characters and HTML entities mapping
def test_html_entities_and_invisible_chars():
    html = '<div><b>Rule:</b> Data is not lost.&nbsp;</div>\n<div><b>Implementation:</b> Stateful Repair.</div>'
    selected = "Rule: Data is not lost. "

    res = _strip_selection(html, selected)
    expected = '<div>Rule: Data is not lost.&nbsp;</div>\n<div><b>Implementation:</b> Stateful Repair.</div>'
    assert res == expected


# Test Case 4: Smart Block Replacement (Full block selection)
def test_block_replacement():
    html = (
        '<div><h3><b>1.3 Section Title</b></h3></div><div><ul><li><div>Item 1</div></li></ul></div>'
    )
    selected = "1.3 Section Title"

    res = _strip_selection(html, selected)
    expected = (
        '<div><div>1.3 Section Title</div></div><div><ul><li><div>Item 1</div></li></ul></div>'
    )
    assert res == expected


# Test Case 5: Smart Block Replacement near Lists
def test_block_replacement_near_lists():
    html = '<h3><span>Some text.</span> <b>Bypass</b> <span>Standard stack.</span><br></h3><ul><li><div>Item 1</div></li></ul>'
    selected = "Some text. Bypass Standard stack."

    res = _strip_selection(html, selected)
    expected = '<div>Some text. Bypass Standard stack.</div><ul><li><div>Item 1</div></li></ul>'
    assert res == expected


# Test Case 6: Unicode space normalization
def test_unicode_space_normalization():
    # Using an EN SPACE (\u2002) in the HTML
    html = '<div><h3><b>1.3 Section Title</b></h3></div>'
    selected = "1.3 Section Title"  # also has EN SPACE

    res = _strip_selection(html, selected)
    expected = '<div><div>1.3 Section Title</div></div>'
    assert res == expected


# Test Case 7: Block tag boundaries produce spaces in browser selection
def test_block_boundary_space():
    html = '<p>What are the alternatives and Trade-Offs for each?</p><p>We\'ll introduce some components.</p>'
    # Browser getSelection().toString() produces a space at the </p><p> boundary
    selected = "What are the alternatives and Trade-Offs for each? We'll introduce some components."

    res = _strip_selection(html, selected)
    assert res is not None


# Test Case 8: _render_text formatting and entity conversion
def test_render_text():
    # Simple formatting tag strip
    assert _render_text("<b>hello</b> <i>world</i>") == "hello world"
    # Block boundaries preserve the visible line structure
    assert _render_text("<div>first</div><div>second</div>") == "first<br>second"
    # Entities unescaped
    assert _render_text("hello &amp; world &lt;3") == "hello & world <3"
    # Collapse extra spaces
    assert _render_text("hello   world") == "hello world"


def test_render_text_whole_field_keeps_lines_drops_empty_wrappers():
    # Whole-field strip of a deeply nested dictionary field (real 'take-up'
    # shape): every visible line survives as its own line, empty wrapper
    # divs contribute nothing, and no tags remain.
    html = (
        '<div>UK headline line</div>'
        '<h3><div><div><div>the acceptance of something offered.</div>'
        '<div>"practices that discourage take-up"</div>'
        '<div><div></div><div><div><div>Similar:</div></div></div>'
        '<div><div>accept<div><div></div></div></div></div></div>'
        '<span style="font-weight: 400;">The meeting took up a whole morning.</span>'
        '</div></div></h3>'
    )
    expected = (
        'UK headline line<br>'
        'the acceptance of something offered.<br>'
        '"practices that discourage take-up"<br>'
        'Similar:<br>'
        'accept<br>'
        'The meeting took up a whole morning.'
    )
    assert _render_text(html) == expected


# Test Case 9: on_js_message with standard JS messaging inputs
def test_on_js_message_non_str():
    assert on_js_message("my_handled", 123, None) == "my_handled"


def test_on_js_message_unhandled():
    assert on_js_message("my_handled", "otherMessage", None) == "my_handled"


def test_on_js_message_strip_all_no_editor():
    assert on_js_message("my_handled", "stripHtmlAll", None) == (True, None)


def test_on_js_message_strip_sel_no_editor():
    assert on_js_message("my_handled", "stripHtmlSel:some text", None) == (True, None)


class MockedEditor(Editor):
    def __init__(self):
        self.note = MagicMock()
        self.currentField = 0
        self.addMode = False
        self.loadNoteKeepingFocus = MagicMock()


# Test Case 10: on_js_message with a mocked Editor (Success and Fallback)
def test_on_js_message_strip_all_with_editor():
    mock_editor = MockedEditor()
    mock_editor.note.fields = ["<b>hello</b> <i>world</i>"]
    mock_editor.currentField = 0
    mock_editor.addMode = False

    res = on_js_message("my_handled", "stripHtmlAll", mock_editor)
    assert res == (True, None)
    assert mock_editor.note.fields[0] == "hello world"
    mock_editor.note.flush.assert_called_once()
    mock_editor.loadNoteKeepingFocus.assert_called_once()


def test_on_js_message_strip_sel_with_editor_success():
    mock_editor = MockedEditor()
    mock_editor.note.fields = ["<div><b>hello</b> <i>world</i></div>"]
    mock_editor.currentField = 0
    mock_editor.addMode = False

    res = on_js_message("my_handled", "stripHtmlSel:world", mock_editor)
    assert res == (True, None)
    # Balanced: stripping "world" removes only <i>…</i>; the <b> pair around
    # "hello" (whose closer sits before the selection) must stay intact.
    assert mock_editor.note.fields[0] == "<div><b>hello</b> world</div>"
    mock_editor.note.flush.assert_called_once()
    mock_editor.loadNoteKeepingFocus.assert_called_once()


def test_on_js_message_strip_sel_with_editor_fallback():
    mock_editor = MockedEditor()
    mock_editor.note.fields = ["<div><b>hello</b> <i>world</i></div>"]
    mock_editor.currentField = 0
    mock_editor.addMode = False

    res = on_js_message("my_handled", "stripHtmlSel:invalid", mock_editor)
    assert res == (True, None)
    assert mock_editor.note.fields[0] == "hello world"
    mock_editor.note.flush.assert_called_once()
    mock_editor.loadNoteKeepingFocus.assert_called_once()


# Test Case 11: _strip_field under AddMode and Edge Cases
def test_strip_field_add_mode():
    mock_editor = MockedEditor()
    mock_editor.note.fields = ["<b>test</b>"]
    mock_editor.currentField = 0
    mock_editor.addMode = True

    _strip_field(mock_editor)
    assert mock_editor.note.fields[0] == "test"
    mock_editor.note.flush.assert_not_called()
    mock_editor.loadNoteKeepingFocus.assert_called_once()


def test_strip_field_edge_cases():
    # note is None
    mock_editor = MockedEditor()
    mock_editor.note = None
    _strip_field(mock_editor)

    # currentField is None
    mock_editor = MockedEditor()
    mock_editor.currentField = None
    _strip_field(mock_editor)

    # currentField out of bounds
    mock_editor = MockedEditor()
    mock_editor.note.fields = ["one", "two"]
    mock_editor.currentField = -1
    _strip_field(mock_editor)

    mock_editor.currentField = 5
    _strip_field(mock_editor)


# Regression (real 'take-up' card): the field is globally wrapped in <h3>,
# lines are <span style="font-weight: 400;">…</span> separated by <br>.
# Stripping one sentence must not eat the </div> closers before it, the <br>
# line separator after it, or the NEXT sentence's <span> opener — doing so
# unbalanced the field and made the following text render h3-big.
def test_selection_strip_stays_balanced_across_line_spans():
    html = (
        '<h3><div>begin (a hobby or leisure-time activity)<br></div>'
        '<span style="font-weight: 400;">The meeting took up a whole morning.</span>'
        '<br style="font-weight: 400;">'
        '<span style="font-weight: 400;">A: "Do you like to ski?"</span></h3>'
    )
    selected = "The meeting took up a whole morning."

    res = _strip_selection(html, selected)
    expected = (
        '<h3><div>begin (a hobby or leisure-time activity)<br></div>'
        'The meeting took up a whole morning.'
        '<br style="font-weight: 400;">'
        '<span style="font-weight: 400;">A: "Do you like to ski?"</span></h3>'
    )
    assert res == expected


def test_selection_strip_keeps_unpaired_closers_before_selection():
    html = '<div>intro</div></div><span style="color: red;">target text here</span><br>tail'
    selected = "target text here"

    res = _strip_selection(html, selected)
    expected = '<div>intro</div></div>target text here<br>tail'
    assert res == expected


def test_selection_strip_replaces_enclosed_block_pairs_with_line_breaks():
    # A block pair fully inside the strip range is structure: it becomes a
    # line break, not silent deletion that glues the lines together.
    html = (
        '<h3><span style="font-size: 20px;">intro words here</span>'
        '<div>middle line</div>'
        '<span style="font-size: 20px;">outro words.</span></h3>'
    )
    selected = "intro words here middle line outro words."

    res = _strip_selection(html, selected)
    expected = '<div>intro words here<br>middle line<br>outro words.</div>'
    assert res == expected


# The editor renders \(...\) / \[...\] as an atomic <anki-mathjax> element, so
# getSelection().toString() yields a lone space where the field stores the
# literal MathJax source. The selection must still map, and the MathJax source
# must survive the strip untouched.
def test_mathjax_inline_selection_maps_to_space():
    html = '<div><b>value (</b>\\(x^*\\)<b>) here</b></div>'
    selected = 'value ( ) here'

    res = _strip_selection(html, selected)
    assert res == '<div>value (\\(x^*\\)) here</div>'


def test_mathjax_display_selection_maps_to_space():
    html = '<div><i>before</i> \\[\\sum_i x_i\\] <i>after</i></div>'
    selected = 'before after'

    res = _strip_selection(html, selected)
    assert res == '<div>before \\[\\sum_i x_i\\] after</div>'


def test_mathjax_selection_real_card_repro():
    # Real card 1766288135492 — selecting the first <h3> line (which contains
    # two inline MathJax expressions) used to fail the selection mapping and
    # fall back to stripping the whole field.
    html = (
        '<h3><span style="font-size: 20px;">训练数据里每个位置只给你一个“真 token” (</span>'
        '\\(x^*\\)'
        '<span style="font-size: 20px;">)。把它看成 one-hot 的经验分布（在那个样本上 (P) 全压在 (</span>'
        '\\(x^*\\)'
        '<span style="font-size: 20px;">) 上），那么：</span></h3>'
        '<div>\\(\\text{loss} = -\\log Q_\\theta(x^*\\mid c)\\)<br><br></div>'
        '<div>这就是你在代码里看到的&nbsp;<strong>NLL / CrossEntropyLoss</strong>&nbsp;的核心。</div>'
    )
    selected = (
        '训练数据里每个位置只给你一个“真 token” ( )。把它看成 one-hot 的经验分布'
        '（在那个样本上 (P) 全压在 ( ) 上），那么：'
    )

    res = _strip_selection(html, selected)
    assert res is not None
    assert res.count('\\(x^*\\)') == 2  # MathJax source survives
    assert res.startswith('<div>训练数据里每个位置只给你一个')
    # The untouched tail of the field is preserved verbatim
    assert res.endswith(
        '<div>\\(\\text{loss} = -\\log Q_\\theta(x^*\\mid c)\\)<br><br></div>'
        '<div>这就是你在代码里看到的&nbsp;<strong>NLL / CrossEntropyLoss</strong>&nbsp;的核心。</div>'
    )


def test_find_mismatches_none():
    import sys
    from io import StringIO
    from unittest.mock import patch

    from strip_html_tags import _find_mismatches

    with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
        res = _find_mismatches("abc", "def")
        assert res is None
        assert "====== STRIP_HTML_DEBUG: Mismatch ======" in mock_stderr.getvalue()
