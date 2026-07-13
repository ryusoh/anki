import sys
from unittest.mock import MagicMock

# Mock out aqt entirely so we can import the module outside of Anki
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()

from auto_mathjax import _convert_dollar_to_mathjax


# --- Test 1: Basic single conversion ---
def test_basic_single_conversion():
    html = 'hello $x^2$ world'
    expected = 'hello \\(x^2\\) world'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 2: Multiple pairs on same line ---
def test_multiple_on_same_line():
    html = '$a+b$ and $c+d$'
    expected = '\\(a+b\\) and \\(c+d\\)'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 3: Two lines, each converted independently ---
def test_two_lines_independent():
    html = 'line1 $x$<br>line2 $y$'
    expected = 'line1 \\(x\\)<br>line2 \\(y\\)'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 4: Lone dollar sign with no closing pair ---
def test_lone_dollar_no_pair():
    html = 'cost is $100 today'
    assert _convert_dollar_to_mathjax(html) == html  # unchanged


# --- Test 5: Skip purely numeric content ---
def test_skip_purely_numeric():
    html = 'price $100$ tax'
    assert _convert_dollar_to_mathjax(html) == html  # unchanged


# --- Test 6: Empty content between dollars ---
def test_empty_dollar_pair():
    html = 'he paid $$'
    # $$ has nothing between them so our regex [^$\n]+? won't match
    assert _convert_dollar_to_mathjax(html) == html  # unchanged


# --- Test 7: Already MathJax — skip entire segment ---
def test_already_mathjax_inline():
    html = 'already \\(x^2\\) done'
    assert _convert_dollar_to_mathjax(html) == html  # unchanged


# --- Test 8: Already in anki-mathjax tag ---
def test_already_anki_mathjax_tag():
    html = '<anki-mathjax>x</anki-mathjax>'
    assert _convert_dollar_to_mathjax(html) == html  # unchanged


# --- Test 9: Mixed — first line converts, second doesn't ---
def test_mixed_lines():
    html = '$x$ on line1<br>$100 on line2'
    expected = '\\(x\\) on line1<br>$100 on line2'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 10: Dollar pairs inside HTML formatting tags ---
def test_inside_bold_tags():
    html = '<b>$x^2$</b>'
    expected = '<b>\\(x^2\\)</b>'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 11: Dollar pair at end of line before br ---
def test_end_of_line_match():
    html = '$a+b$<br>next line'
    expected = '\\(a+b\\)<br>next line'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 12: Whitespace-only content — skip ---
def test_whitespace_only_skip():
    html = '$ $'
    assert _convert_dollar_to_mathjax(html) == html  # unchanged

    html2 = '$  $'
    assert _convert_dollar_to_mathjax(html2) == html2  # unchanged


# --- Test 13: Spaces inside valid math expression ---
def test_spaces_inside_math():
    html = '$x + y = z$ and plain text'
    expected = '\\(x + y = z\\) and plain text'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 14: Inside div tags ---
def test_inside_div_tags():
    html = '<div>$E=mc^2$</div>'
    expected = '<div>\\(E=mc^2\\)</div>'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 15: LaTeX commands preserved ---
def test_latex_commands_preserved():
    html = '$\\frac{1}{2}$'
    expected = '\\(\\frac{1}{2}\\)'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 16: Two currency amounts on one line — NOT a math pair ---
def test_currency_no_pair():
    """ "$5 and $10" would regex-match as the pair "$5 and $", but both $
    are immediately followed by a digit — that's currency, leave it alone."""
    html = '$5 and $10'
    assert _convert_dollar_to_mathjax(html) == html


def test_currency_pair_in_prose_untouched():
    """The closing sentence of the 'Quick Assets' card: two dollar amounts
    in one sentence must not be paired into math."""
    html = (
        '<div>This means the company has $1.67 in liquid assets '
        'for every $1 of current liabilities.</div>'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_digit_leading_math_still_converts():
    """A $ pair whose content starts with a digit is still math when the
    closing $ is NOT followed by a digit."""
    html = '$2x$ terms'
    expected = '\\(2x\\) terms'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Test 17: Dollar on separate lines, no pairs ---
def test_dollars_on_separate_lines():
    html = 'Cost $5<br>Refund $10'
    assert _convert_dollar_to_mathjax(html) == html  # unchanged


# --- Test 18: Idempotent — running twice gives same result ---
def test_idempotent():
    html = 'hello $x^2$ world'
    first_pass = _convert_dollar_to_mathjax(html)
    second_pass = _convert_dollar_to_mathjax(first_pass)
    assert first_pass == second_pass == 'hello \\(x^2\\) world'


# --- Test 19: Empty string ---
def test_empty_string():
    assert _convert_dollar_to_mathjax('') == ''


# --- Test 20: No dollar signs at all ---
def test_no_dollar_signs():
    html = 'just plain text with <b>HTML</b> tags'
    assert _convert_dollar_to_mathjax(html) == html


# --- Test 21: Numeric with comma (currency format) ---
def test_numeric_with_comma():
    html = '$1,000$'
    assert _convert_dollar_to_mathjax(html) == html  # unchanged — purely numeric


# --- Test 22: Decimal number ---
def test_decimal_number():
    html = '$5.99$'
    assert _convert_dollar_to_mathjax(html) == html  # unchanged — purely numeric


# --- Test 23: Mixed math and text on complex line ---
def test_complex_line():
    html = 'Given $x > 0$ and $y < 0$, find $x + y$'
    expected = 'Given \\(x > 0\\) and \\(y < 0\\), find \\(x + y\\)'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Integration Tests ---
# These verify the button handler properly syncs the field before reading


def test_on_auto_mathjax_calls_save_first():
    """The button handler MUST call call_after_note_saved() to sync
    the webview content to editor.note.fields before reading it.
    Without this, the field data is stale and conversions are lost."""
    from auto_mathjax import on_auto_mathjax

    editor = MagicMock()
    on_auto_mathjax(editor)

    # Verify call_after_note_saved was called (not direct field access)
    editor.call_after_note_saved.assert_called_once()


def test_apply_mathjax_converts_and_reloads():
    """After syncing, _apply_mathjax should convert field content and reload."""
    from auto_mathjax import _apply_mathjax

    editor = MagicMock()
    editor.note.fields = ['$x^2$']
    editor.currentField = 0
    editor.addMode = False

    _apply_mathjax(editor)

    assert editor.note.fields[0] == '\\(x^2\\)'
    editor.loadNoteKeepingFocus.assert_called_once()


# --- Double-Dollar (Block Math) Tests ---


def test_double_dollar_block_math():
    """$$...$$ should convert to \\[...\\] (block MathJax)."""
    html = '$$E = mc^2$$'
    expected = '\\[E = mc^2\\]'
    assert _convert_dollar_to_mathjax(html) == expected


def test_double_dollar_no_leftover_signs():
    """After converting $$...$$, no $ signs should remain."""
    html = '<div><div>$$E = 2h\\nu$$</div></div>'
    result = _convert_dollar_to_mathjax(html)
    # Check no stray $ left
    assert '$' not in result
    assert '\\[E = 2h\\nu\\]' in result


def test_mixed_block_and_inline():
    """$$...$$ (block) and $...$ (inline) should both convert correctly."""
    html = '$$E = mc^2$$<br>and $x^2$ is inline'
    expected = '\\[E = mc^2\\]<br>and \\(x^2\\) is inline'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Bare LaTeX (no $ delimiters) Tests ---


def test_bare_latex_line_wrapped_as_block():
    """A whole line of bare LaTeX (no $ at all) should be wrapped in \\[...\\]."""
    html = (
        '<div>\\text{Percentage of Total Assets} = '
        '\\frac{\\text{Line Item}}{\\text{Total Assets}} \\times 100</div>'
    )
    expected = (
        '<div>\\[\\text{Percentage of Total Assets} = '
        '\\frac{\\text{Line Item}}{\\text{Total Assets}} \\times 100\\]</div>'
    )
    assert _convert_dollar_to_mathjax(html) == expected


def test_bare_latex_real_card_field():
    """The exact field HTML from the 'Vertical Common-Sized BS How it Works' card."""
    html = (
        '<div><b>Formula:</b></div><div><br></div><div>\n'
        '<div>\\text{Percentage of Total Assets} = '
        '\\frac{\\text{Line Item}}{\\text{Total Assets}} \\times 100</div></div>'
        '<div><br></div><div><b>Example:</b></div>'
    )
    result = _convert_dollar_to_mathjax(html)
    assert (
        '\\[\\text{Percentage of Total Assets} = '
        '\\frac{\\text{Line Item}}{\\text{Total Assets}} \\times 100\\]'
    ) in result
    # Surrounding prose/structure untouched
    assert result.startswith('<div><b>Formula:</b></div>')
    assert result.endswith('<div><b>Example:</b></div>')


def test_bare_latex_short_variables_ok():
    """Short variable names around commands still count as a formula line."""
    html = '<div>PV = \\frac{FV}{(1+r)^n}</div>'
    expected = '<div>\\[PV = \\frac{FV}{(1+r)^n}\\]</div>'
    assert _convert_dollar_to_mathjax(html) == expected


def test_bare_latex_fragment_in_prose_wrapped_inline():
    """Prose stays prose; only the embedded LaTeX fragment is wrapped inline."""
    html = 'The result is \\frac{1}{2} of the total amount'
    expected = 'The result is \\(\\frac{1}{2}\\) of the total amount'
    assert _convert_dollar_to_mathjax(html) == expected


def test_bare_latex_windows_path_not_wrapped():
    """Backslash paths are not LaTeX."""
    html = 'C:\\Users\\name\\frames'
    assert _convert_dollar_to_mathjax(html) == html


def test_bare_latex_plain_prose_not_wrapped():
    html = 'each item is expressed as a percentage of total assets'
    assert _convert_dollar_to_mathjax(html) == html


def test_bare_latex_already_mathjax_skipped():
    html = '\\[\\frac{a}{b}\\]'
    assert _convert_dollar_to_mathjax(html) == html


def test_bare_latex_idempotent():
    html = '<div>\\frac{a}{b} \\times 100</div>'
    first = _convert_dollar_to_mathjax(html)
    second = _convert_dollar_to_mathjax(first)
    assert first == second == '<div>\\[\\frac{a}{b} \\times 100\\]</div>'


def test_bare_latex_line_with_dollars_left_to_dollar_logic():
    """If a line has $ pairs, the dollar logic owns it — no whole-line wrap."""
    html = 'formula $\\frac{a}{b}$ here'
    expected = 'formula \\(\\frac{a}{b}\\) here'
    assert _convert_dollar_to_mathjax(html) == expected


def test_bare_latex_line_with_inline_tags_wraps_fragments():
    """Inline HTML tags never end up inside math — each fragment wraps alone."""
    html = '<b>\\frac{a}{b}</b> \\times 100'
    expected = '<b>\\(\\frac{a}{b}\\)</b> \\(\\times 100\\)'
    assert _convert_dollar_to_mathjax(html) == expected


def test_embedded_latex_quick_assets_card():
    """The exact formula line from the 'Quick Assets' card: bold prose label,
    &nbsp; entities, then a bare \\frac fragment with numbers around it."""
    html = '<div><b>Quick Ratio</b>&nbsp;=&nbsp; ' '\\frac{100,000}{60,000} = 1.67&nbsp;</div>'
    expected = (
        '<div><b>Quick Ratio</b>&nbsp;=&nbsp; ' '\\(\\frac{100,000}{60,000} = 1.67\\)&nbsp;</div>'
    )
    assert _convert_dollar_to_mathjax(html) == expected


def test_embedded_latex_nested_text_args():
    """\\frac with nested \\text{...} arguments stays one fragment."""
    html = '<div><b>Ratio</b>: \\frac{\\text{Quick Assets}}' '{\\text{Current Liabilities}}</div>'
    expected = (
        '<div><b>Ratio</b>: \\(\\frac{\\text{Quick Assets}}'
        '{\\text{Current Liabilities}}\\)</div>'
    )
    assert _convert_dollar_to_mathjax(html) == expected


def test_embedded_latex_sentence_period_not_swallowed():
    """Trailing sentence punctuation stays outside the math wrap."""
    html = 'computed as \\frac{1}{2}.'
    expected = 'computed as \\(\\frac{1}{2}\\).'
    assert _convert_dollar_to_mathjax(html) == expected


def test_embedded_latex_numbers_only_line_untouched():
    """A plain arithmetic line with no LaTeX command must stay untouched."""
    html = '<div><b>Quick Assets</b>&nbsp;=&nbsp; 50,000 + 20,000 + 30,000 = 100,000&nbsp;</div>'
    assert _convert_dollar_to_mathjax(html) == html


def test_embedded_latex_idempotent():
    html = '<b>Quick Ratio</b> = \\frac{100,000}{60,000} = 1.67'
    first = _convert_dollar_to_mathjax(html)
    second = _convert_dollar_to_mathjax(first)
    assert first == second == '<b>Quick Ratio</b> = \\(\\frac{100,000}{60,000} = 1.67\\)'


def test_embedded_latex_skipped_when_dollars_present():
    """Lines containing $ are left to the dollar logic entirely."""
    html = 'Cash: $50,000 plus \\frac{1}{2}'
    assert _convert_dollar_to_mathjax(html) == html


def test_real_world_input():
    """The user's exact real-world input — mixed block and inline math."""
    html = (
        '<ul><li><div>能量叠加公式：</div>'
        '<div><div>$$E = 2h\\nu = 2 \\times 0.8\\text{ eV} = 1.6\\text{ eV} &gt; 1.12\\text{ eV}$$</div></div>'
        '</li><li><div>1.6 eV 的总能量瞬间击穿了硅的能隙约束，电子成功跃迁。原本透明的硅波导，突然变成了'
        '<b>吸收光信号的黑洞</b>。最致命的是，TPA的发生概率与光强（Intensity, $I$）的'
        '<b>平方</b>成正比（$I^2$）。光功率稍微加一点，信号吸收率呈指数级飙升。</div></li></ul>'
    )
    result = _convert_dollar_to_mathjax(html)

    # Block math: $$ should be fully removed, converted to \[...\]
    assert '$$' not in result
    assert (
        '\\[E = 2h\\nu = 2 \\times 0.8\\text{ eV} = 1.6\\text{ eV} &gt; 1.12\\text{ eV}\\]'
        in result
    )
    # No stray $ around the block math
    assert '$\\[' not in result
    assert '\\]$' not in result

    # Inline math: $I$ and $I^2$ should convert to \(...\)
    assert '\\(I\\)' in result
    assert '\\(I^2\\)' in result
    # No stray $ for inline either
    assert '$I$' not in result
    assert '$I^2$' not in result
