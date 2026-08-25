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


def test_bare_lambdabar_line_wrapped_as_block():
    """A bare \\lambdabar line is LaTeX too: \\lambdabar must match as its own
    command — \\lambda's trailing word boundary cannot prefix-match it."""
    html = '<div>\\lambdabar</div>'
    result = _convert_dollar_to_mathjax(html)
    # The bare line should be wrapped in display math
    assert '\\[\\lambdabar\\]' in result
    # A macro preamble should also be injected
    assert '\\def\\lambdabar' in result


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


# --- Dangling superscript/subscript: invalid LaTeX must not be wrapped ---


def test_dangling_superscript_not_wrapped():
    """$x^$ has a ^ with no operand — MathJax renders it as a red-on-yellow
    error. The add-on must leave it alone."""
    assert _convert_dollar_to_mathjax('$x^$') == '$x^$'


def test_dangling_subscript_not_wrapped():
    """$x_$ has a _ with no operand — also invalid LaTeX."""
    assert _convert_dollar_to_mathjax('$x_$') == '$x_$'


def test_leading_subscript_not_wrapped():
    """$^x$ is not valid standalone math."""
    assert _convert_dollar_to_mathjax('$^x$') == '$^x$'


def test_valid_superscript_still_converts():
    """$x^2$ and $x^*$ are valid and should still convert."""
    assert _convert_dollar_to_mathjax('$x^2$') == '\\(x^2\\)'
    assert _convert_dollar_to_mathjax('$x^*$') == '\\(x^*\\)'


# --- Prose protection (shapes found by tools/sweep_transform.py) ---
# Cashtags, money slang, and finance commentary regex-match as $ pairs but
# must never convert. Each test pins the shape of a real mangled note.


def test_cashtag_list_not_math():
    """Note 1448934758847: a run of stock cashtags pairs up as $META $AMZN..."""
    html = (
        'So yes, please keep telling me about how $META $AMZN $GOOG and $MSFT '
        'are "cheap" on PE ratios where the E is a total mirage. <br>'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_cashtag_pair_short_tickers_not_math():
    """Note 1764066539029: $GOOG ... $NVDA — short tickers with prose between."""
    html = '<div>$GOOG TPU vs $NVDA GPU</div>'
    assert _convert_dollar_to_mathjax(html) == html


def test_cashtag_adjacent_tickers_not_math():
    """Note about oil ETFs: $USO $OXY $XOM — content of the pair is one
    3-letter ticker plus trailing space."""
    html = '$USO $OXY $XOM  The eco-friendly International Energy Agency'
    assert _convert_dollar_to_mathjax(html) == html


def test_cashtag_japanese_prose_not_math():
    """Note 1428668343805: $INTC ... $SOI with Japanese prose between."""
    html = (
        '<div>1月に$INTCに35ドルの価格目標を出したとき、Bernsteinをピエロだと非難したよ。 '
        '一方、他の機関はこっそりロングポジションを取る（$SOIで見られるように）。</div>'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_cashtag_single_letter_cjk_not_math():
    """Note 1780799245450: $MAと$V — two-letter/one-letter tickers, only CJK
    between the $ signs."""
    html = '<div>$MAと$Vはさらに極端です。彼らはほとんど在庫を持たず。</div>'
    assert _convert_dollar_to_mathjax(html) == html


def test_cashtag_anchor_then_currency_not_math():
    """Note 1440881107480: linked $baba cashtag pairs with the $ of US$100.80."""
    html = (
        '<a href="https://stocktwits.com/symbol/BABA">$baba</a> '
        'indicating an open at around US$100.80'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_cashtag_linked_pair_not_math():
    """Note 1448934757006: two linked cashtags — the pair content spans
    HTML tags, which a formula never does."""
    html = (
        'YouTube is a hybrid of '
        '<a href="https://x.com/search?q=%24NFLX&amp;src=cashtag_click">$NFLX</a>, '
        '<a href="https://x.com/search?q=%24SPOT&amp;src=cashtag_click">$SPOT</a> '
        '&amp; TikTok -- with better margins.'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_double_dollar_money_slang_not_math():
    """Note 1436157395396: $$ as slang for money — the block-math branch
    must not pair 'big $$. ... pool $$.' into \\[...\\]."""
    html = (
        'You can’t run a campaign for POTUS without big $$. Most candidates '
        'don’t have it, so they lean on donors who pool $$. That group '
        'defines the campaign, tells people what to say.'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_double_dollar_money_slang_question_not_math():
    """Note 1631256811209 shape: 'making $$ off this? ... his $$?'"""
    html = (
        'Is always legitimate to ask ‘is this guy making $$ off this? '
        'Who is paying? Is what he says dictated by how he makes his $$?’'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_trailing_currency_prose_not_math():
    """Note 1500235933005: amounts written as 60$ / 40$ pair across prose."""
    html = (
        'A lot of American companies become unprofitable with wti around 60$. '
        'They have to use the lowest cost wells. One of the reasons Warren '
        'buffet is buying OXY is they can break even around 40$ a barrel.'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_lone_dollar_prose_pair_not_math():
    """Note 1421507902490: 'tax drag $ and ... tax drag $ and ...' — bare $
    used as the word 'dollars', twice on one logical line."""
    html = (
        '<li>As investment horizon increases: tax drag $ and tax drag % '
        'increases</li><li>As investment return increases: tax drag $ and '
        'tax drag % increases</li>'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_cashtag_slash_pair_not_math():
    """Note 1606615521635: $ORCL/$MSFT — the closing $ of the pair is really
    the next ticker's prefix (immediately followed by a letter)."""
    html = (
        "<div>I don't care for $ORCL/$MSFT as longs, but as a barometer for "
        "OAI, I don't think these stocks can languish forever</div>"
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_cashtag_two_letter_ticker_not_math():
    """Note 1740033936309: $BIDU $TENCENT $JD $BABA $PDD — the two-letter
    ticker $JD would pass the short-word check, but its closing $ starts
    the next cashtag."""
    html = (
        '<dd>$BIDU $TENCENT $JD $BABA $PDD  Look at the way these gems are '
        'bought up with any attempt to sell them down.</dd>'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_usenet_message_id_not_math():
    """Note 1775888044474: message-ID 5npiei$lrn$1@thor.atcon.com — a $ pair
    inside an identifier, with a digit right after the closing $."""
    html = 'message-ID <span>&lt;</span>5npiei$lrn$1@thor.atcon.com<span>&gt;</span>:'
    assert _convert_dollar_to_mathjax(html) == html


def test_mathml_annotation_displaystyle_untouched():
    """Note 1780300730631: MathML <annotation>{\\displaystyle ...} sources
    (Wikipedia paste) must not get fragments wrapped."""
    html = (
        '<annotation>{\\displaystyle \\left\\langle A\\bullet B\\right\\rangle '
        '={\\overline {\\left\\langle B\\bullet A\\right\\rangle }}}</annotation>'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_mathml_annotation_displaystyle_with_digits_untouched():
    """Same note: {\\displaystyle ... \\Re _{\\geq 0}} — digits inside the
    run must not defeat the displaystyle guard."""
    html = (
        '<annotation>{\\displaystyle \\left\\langle A\\bullet A\\right\\rangle '
        '\\in \\Re _{\\geq 0}}</annotation>'
    )
    assert _convert_dollar_to_mathjax(html) == html


# --- Real math must still convert despite the prose guards ---


def test_inline_greek_in_cjk_prose_still_converts():
    """Note with 角速度（$\\omega$）: CJK around the pair is fine — only CJK
    inside the pair marks prose."""
    html = '<div>角速度（$\\omega$）表示<b>物体绕轴旋转的快慢</b>。</div>'
    expected = '<div>角速度（\\(\\omega\\)）表示<b>物体绕轴旋转的快慢</b>。</div>'
    assert _convert_dollar_to_mathjax(html) == expected


def test_inline_single_letter_with_prose_after_still_converts():
    """Note with $g$ (General Intelligence): a one-letter variable converts
    even though prose follows the pair."""
    html = 'To hold <b>$g$ (General Intelligence)</b> constant'
    expected = 'To hold <b>\\(g\\) (General Intelligence)</b> constant'
    assert _convert_dollar_to_mathjax(html) == expected


def test_single_word_pair_still_converts():
    """$math$ — a single word with no whitespace reads as a variable name,
    not prose (also pinned by test_missing.py fixtures)."""
    assert _convert_dollar_to_mathjax('$math$') == '\\(math\\)'


# --- Wikipedia {\displaystyle ...} pastes (note 1639716063357) ---


def test_wikipedia_displaystyle_paste_untouched():
    """{\\displaystyle O(\\log N)} next to its rendered <img> fallback:
    wrapping just '(\\log' would mangle it — a bare command with no braced
    or numeric operand is not a self-contained formula."""
    html = (
        '<dd><i>Time complexity:</i>&nbsp;{\\displaystyle O(\\log N)}'
        '<img src="14eea297b4387decf341763c39dc038e05744272">.</dd>'
    )
    assert _convert_dollar_to_mathjax(html) == html


# --- Interior of an existing multi-line \[...\] block (notes 1764121857247,
# --- 1764836660467): lines between \[ and \] are already math ---


def test_multiline_display_block_interior_untouched():
    # The \[...\] content itself must not be mangled; <pre> wrappers that
    # would hide it from the reviewer's MathJax are removed.
    html = (
        '<div><pre><pre><div>\\[\\begin{bmatrix}\n'
        '\\lambda &amp; 1 &amp; 0 &amp; \\cdots \\\\\n'
        '0 &amp; \\cdots &amp; 0 &amp; \\lambda\n'
        '\\end{bmatrix}\\]</div>'
    )
    result = _convert_dollar_to_mathjax(html)
    assert '<pre>' not in result
    assert '\\[\\begin{bmatrix}' in result
    assert '\\end{bmatrix}\\]' in result


def test_multiline_display_block_continuation_untouched():
    html = (
        '<div>\\[\\frac{\\partial L}{\\partial x_0}\n'
        '= \\frac{\\partial L}{\\partial x_n}\n'
        '\\cdot \\frac{\\partial x_n}{\\partial x_{n-1}}\n'
        '\\frac{\\partial x_1}{\\partial x_0}\\]<br>'
    )
    assert _convert_dollar_to_mathjax(html) == html


def test_conversion_resumes_after_display_block():
    """The in-math state must close at \\] so later lines still convert."""
    html = '\\[a\n+ b\\]<br>then $x^2$ here'
    expected = '\\[a\n+ b\\]<br>then \\(x^2\\) here'
    assert _convert_dollar_to_mathjax(html) == expected


# --- CJK prose lines with stray LaTeX fragments (notes 1753244189584 &
# --- the Bernoulli-head note): never display-wrap a prose sentence ---


def test_cjk_prose_line_not_display_wrapped():
    html = '<ul><li><div>只玩几何优势为正的游戏：确保 (E\\ln(1+r)&gt;0)。</div>'
    assert _convert_dollar_to_mathjax(html) == html


def test_cjk_prose_rho_not_wrapped():
    html = (
        '<div>把压力 P、速度 v 和海拔 z 全部除以 \\rho g，都能化成“液柱高度”'
        '这个统一单位——这就是伯努利方程里的压头、速度头、位置头概念。</div>'
    )
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


# --- Macro injection: \lambdabar → \def\lambdabar{...} preamble ---


def test_lambdabar_inline_gets_def_preamble():
    r"""$\lambdabar$ converts to \\(...\\) and a \\def preamble is injected."""
    html = r'$\lambdabar = \lambda_C / 2\pi$'
    result = _convert_dollar_to_mathjax(html)
    # The preamble block should appear exactly once
    assert r'\def\lambdabar' in result
    # The original math should still be wrapped
    assert r'\(\lambdabar = \lambda_C / 2\pi\)' in result


def test_lambdabar_already_wrapped_gets_def_preamble():
    r"""Already-wrapped \\(\lambdabar\\) still gets a \\def preamble."""
    html = r'\(\lambdabar\)'
    result = _convert_dollar_to_mathjax(html)
    assert r'\def\lambdabar' in result


def test_lambdabar_bare_block_gets_def_preamble():
    r"""A bare \lambdabar line wrapped as display math gets a \def preamble."""
    html = r'<div>\lambdabar</div>'
    result = _convert_dollar_to_mathjax(html)
    assert r'\def\lambdabar' in result
    assert r'\[\lambdabar\]' in result


def test_lambdabar_def_injected_only_once():
    r"""Multiple occurrences of \lambdabar produce only one \def."""
    html = r'$\lambdabar$ and $\lambdabar$'
    result = _convert_dollar_to_mathjax(html)
    assert result.count(r'\def\lambdabar') == 1


def test_no_lambdabar_no_preamble():
    r"""Fields without \lambdabar get no preamble injection."""
    html = r'$\lambda$'
    result = _convert_dollar_to_mathjax(html)
    assert r'\def\lambdabar' not in result


def test_lambdabar_def_not_duplicated_on_rerun():
    r"""Running the converter on already-converted output doesn't add a second \def."""
    html = r'$\lambdabar$'
    first = _convert_dollar_to_mathjax(html)
    second = _convert_dollar_to_mathjax(first)
    assert second.count(r'\def\lambdabar') == 1


# --- Macro injection: \oiint / \oiiint (esint closed integrals) ---
# Anki's bundled MathJax has no esint extension, so \oiint / \oiiint render
# as red "undefined control sequence" errors. They get \def preambles that
# emulate the glyphs (circle overlaid on \iint / \iiint) via CUSTOM_MACROS.


def test_oiint_anki_mathjax_gets_def_preamble():
    r"""A field using <anki-mathjax>\oiint</anki-mathjax> gets a \def\oiint preamble."""
    html = r'closed surface: <anki-mathjax>\oiint</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert r'\def\oiint{' in result
    # Emulated as a circle overlaid on \iint
    assert r'\iint' in result
    # The original math block is untouched
    assert r'<anki-mathjax>\oiint</anki-mathjax>' in result


def test_oiiint_anki_mathjax_gets_def_preamble():
    r"""A field using <anki-mathjax>\oiiint</anki-mathjax> gets a \def\oiiint preamble."""
    html = r'closed volume: <anki-mathjax>\oiiint</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert r'\def\oiiint{' in result
    assert r'\iiint' in result


def test_oiint_defs_not_duplicated_on_rerun():
    r"""Re-running the converter on converted output adds no second \def."""
    html = r'<anki-mathjax>\oiint</anki-mathjax> and <anki-mathjax>\oiiint</anki-mathjax>'
    first = _convert_dollar_to_mathjax(html)
    assert first.count(r'\def\oiint{') == 1
    assert first.count(r'\def\oiiint{') == 1
    second = _convert_dollar_to_mathjax(first)
    assert second.count(r'\def\oiint{') == 1
    assert second.count(r'\def\oiiint{') == 1


def test_no_closed_integral_no_preamble():
    r"""Fields without \oiint / \oiiint get no closed-integral preamble."""
    html = r'<anki-mathjax>\oint_C</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert r'\def\oiint{' not in result
    assert r'\def\oiiint{' not in result


# --- Standalone integral symbols (\oint / \oiint / \oiiint) in prose ---
# Chinese physics notes mention the symbols inline ("你问的 \oint 是…"),
# not as formulas. These self-contained glyphs take no operand, so they are
# wrapped even in CJK prose lines (where embedded-run wrapping is normally
# skipped); \oint_C-style uses with operands are left alone.


def test_standalone_oint_wrapped_in_cjk_prose():
    r"""A bare \oint symbol inside a CJK prose line is wrapped inline."""
    html = r'<ul><li>你问的 <b>\oint</b> 是沿<b>闭合曲线</b>的线积分。&nbsp;</li></ul>'
    result = _convert_dollar_to_mathjax(html)
    assert r'<b>\(\oint\)</b>' in result
    # CJK prose and surrounding tags are untouched
    assert '你问的' in result
    assert '<b>闭合曲线</b>' in result


def test_standalone_oiint_and_oint_wrapped_in_cjk_prose():
    r"""Mixed \oint / \oiint symbols in one CJK line are each wrapped."""
    html = r'<li>如果说 \oint 常用于计算环路环量（如安培环路定理），那么 \oiint 就是计算闭合曲面通量（如高斯定理）。</li>'
    result = _convert_dollar_to_mathjax(html)
    assert r'\(\oint\)' in result
    assert r'\(\oiint\)' in result


def test_oint_with_subscript_not_wrapped_in_cjk_prose():
    r"""\oint_C takes an operand — not a standalone symbol, left alone."""
    html = r'<li>沿闭合路径的积分 \oint_C 表示环量。</li>'
    result = _convert_dollar_to_mathjax(html)
    assert r'\(\oint' not in result


def test_standalone_oiint_symbol_gets_macro_preamble():
    r"""A \oiint symbol wrapped from prose also triggers the \def preamble."""
    html = r'<li>高斯定理用的是 <b>\oiint</b>，即沿闭合曲面的面积分。</li>'
    result = _convert_dollar_to_mathjax(html)
    assert r'\(\oiint\)' in result
    assert r'\def\oiint{' in result


def test_standalone_symbols_not_double_wrapped_on_rerun():
    r"""Re-running the converter does not re-wrap an already-wrapped \oint."""
    html = r'<li>你问的 <b>\oint</b> 是沿闭合曲线的线积分。</li>'
    first = _convert_dollar_to_mathjax(html)
    second = _convert_dollar_to_mathjax(first)
    assert second == first


def test_standalone_oint_wrapped_in_english_prose():
    r"""A bare \oint symbol in an English prose line is also wrapped."""
    html = r'the symbol \oint denotes a closed loop integral'
    result = _convert_dollar_to_mathjax(html)
    assert r'\(\oint\)' in result


# --- &nbsp; cleaning inside <anki-mathjax> blocks ---


def test_amp_nbsp_stripped_from_anki_mathjax_block():
    r"""&amp;nbsp; padding inside a block <anki-mathjax> is removed."""
    html = (
        '<anki-mathjax block="true">'
        '&amp;nbsp;&amp;nbsp; U(P_0) = \\frac{1}{4\\pi}'
        '\n&amp;nbsp;&amp;nbsp; </anki-mathjax>'
    )
    result = _convert_dollar_to_mathjax(html)
    assert '&amp;nbsp;' not in result
    assert 'U(P_0) = \\frac{1}{4\\pi}' in result


def test_amp_nbsp_stripped_from_anki_mathjax_inline():
    r"""&amp;nbsp; inside an inline <anki-mathjax> is removed."""
    html = '<anki-mathjax>&amp;nbsp;x^2&amp;nbsp;</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert '&amp;nbsp;' not in result
    assert 'x^2' in result


def test_plain_nbsp_entity_stripped_from_anki_mathjax():
    r"""Plain &nbsp; entity inside <anki-mathjax> is also removed."""
    html = '<anki-mathjax>&nbsp;\\alpha&nbsp;</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert '&nbsp;' not in result
    assert '\\alpha' in result


def test_unicode_nbsp_stripped_from_anki_mathjax():
    r"""Unicode NBSP (U+00A0) inside <anki-mathjax> is removed."""
    html = '<anki-mathjax>\u00a0\\beta\u00a0</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert '\u00a0' not in result
    assert '\\beta' in result


def test_nbsp_outside_anki_mathjax_preserved():
    r"""&nbsp; outside <anki-mathjax> is not touched."""
    html = 'hello&nbsp;<anki-mathjax>x</anki-mathjax>&nbsp;world'
    result = _convert_dollar_to_mathjax(html)
    assert result.startswith('hello&nbsp;')
    assert result.endswith('&nbsp;world')


def test_amp_nbsp_stripped_from_display_math_block():
    r"""&amp;nbsp; inside \\[...\\] display math is cleaned."""
    html = '\\[&amp;nbsp;&amp;nbsp; U(P_0) = \\frac{1}{4\\pi}\\]'
    result = _convert_dollar_to_mathjax(html)
    assert '&amp;nbsp;' not in result
    assert '\\[U(P_0) = \\frac{1}{4\\pi}\\]' in result


def test_amp_nbsp_stripped_from_inline_math():
    r"""&amp;nbsp; inside \\(...\\) inline math is cleaned."""
    html = '\\(&amp;nbsp;x^2&amp;nbsp;\\)'
    result = _convert_dollar_to_mathjax(html)
    assert '&amp;nbsp;' not in result
    assert '\\(x^2\\)' in result


def test_real_kirchhoff_field_cleaned():
    r"""Real card: &amp;nbsp; padding inside \\[...\\] display math with newline."""
    html = (
        '&nbsp;&nbsp;&nbsp;&nbsp;'
        '\\[&amp;nbsp;&amp;nbsp;&amp;nbsp; U(P_0) = \\frac{1}{4\\pi}'
        '\n&amp;nbsp;&amp;nbsp;&amp;nbsp; \\]'
    )
    result = _convert_dollar_to_mathjax(html)
    assert '&amp;nbsp;' not in result
    assert 'U(P_0) = \\frac{1}{4\\pi}' in result
    # nbsp OUTSIDE the math block is preserved
    assert result.startswith('&nbsp;')


# --- MathJax inside <pre> tags (reviewer skips them; editor does not) ---


def test_mathjax_inside_pre_is_unwrapped():
    r"""\[...\] inside <pre> is unwrapped so the reviewer MathJax sees it.

    The editor renders \\(...\\) / \\[...\\] as <anki-mathjax> regardless of
    surrounding <pre>, but MathJax tex2jax in the reviewer skips <pre> by
    default. The add-on must unwrap math so it renders during review.
    """
    html = '<pre>\\[x^2\\]</pre>'
    assert _convert_dollar_to_mathjax(html) == '\\[x^2\\]'


def test_inline_mathjax_inside_pre_is_unwrapped():
    r"""\\(...\\) inside <pre> is unwrapped too."""
    html = '<p><pre>\\(x^2\\)</pre></p>'
    assert _convert_dollar_to_mathjax(html) == '<p>\\(x^2\\)</p>'


def test_real_card_mathjax_unwrapped_from_nested_pre():
    r"""Real card with front field '相似标准型' had MathJax inside nested <pre>."""
    html = (
        '<div><pre><pre><div>\\[\\begin{bmatrix}\n'
        '\\lambda &amp; 1 &amp; 0 &amp; \\cdots \\\\\n'
        '0 &amp; \\lambda &amp; 1 &amp; \\cdots \\\\\n'
        '\\vdots &amp; &amp; \\ddots &amp; 1 \\\\\n'
        '0 &amp; \\cdots &amp; 0 &amp; \\lambda\n'
        '\\end{bmatrix}\\]</div></pre><pre></pre><pre></pre></pre></div>'
    )
    result = _convert_dollar_to_mathjax(html)
    assert '<pre>' not in result
    assert '</pre>' not in result
    assert '\\[\\begin{bmatrix}' in result
    assert '\\end{bmatrix}\\]' in result


# --- Unbalanced-brace fixing inside MathJax blocks ---


def test_extra_closing_brace_in_anki_mathjax_fixed():
    r"""Extra } inside <anki-mathjax> is removed."""
    html = '<anki-mathjax>E_{\\mathbf{p}}}</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert result == '<anki-mathjax>E_{\\mathbf{p}}</anki-mathjax>'


def test_extra_closing_brace_in_block_anki_mathjax_fixed():
    r"""Extra } in display <anki-mathjax block="true"> is removed."""
    html = '<anki-mathjax block="true">' '\\frac{1}{2E_{\\mathbf{p}}}} e^{-ip}' '</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert '\\frac{1}{2E_{\\mathbf{p}}} e^{-ip}' in result
    # Braces should now balance
    import re

    m = re.search(r'<anki-mathjax[^>]*>(.*?)</anki-mathjax>', result, re.DOTALL)
    content = m.group(1)
    assert content.count('{') == content.count('}')


def test_extra_closing_brace_in_backslash_square_fixed():
    r"""Extra } inside \[...\] is removed."""
    html = '\\[\\frac{a}{b}}\\]'
    result = _convert_dollar_to_mathjax(html)
    assert result == '\\[\\frac{a}{b}\\]'


def test_extra_closing_brace_in_backslash_paren_fixed():
    r"""Extra } inside \(...\) is removed."""
    html = '\\(E_{\\mathbf{p}}}\\)'
    result = _convert_dollar_to_mathjax(html)
    assert result == '\\(E_{\\mathbf{p}}\\)'


def test_missing_closing_brace_in_anki_mathjax_appended():
    r"""Missing } inside <anki-mathjax> is appended."""
    html = '<anki-mathjax>\\frac{a}{b</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert result == '<anki-mathjax>\\frac{a}{b}</anki-mathjax>'


def test_escaped_braces_not_counted():
    r"""Literal \{ and \} are display characters, not grouping — don't touch."""
    html = '<anki-mathjax>\\{a, b\\}</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert result == html  # unchanged — already balanced


def test_balanced_braces_untouched():
    r"""Already-balanced content is not modified."""
    html = '<anki-mathjax>\\frac{a}{b}</anki-mathjax>'
    result = _convert_dollar_to_mathjax(html)
    assert result == html


def test_user_wightman_card_braces_fixed():
    r"""The user's exact card: two blocks with extra } are fixed."""
    import re

    html = (
        '<anki-mathjax block="true">W(x-y) = \\int \\frac{d^3p}{(2\\pi)^3} '
        '\\frac{1}{2E_{\\mathbf{p}}}} e^{-ip \\cdot (x-y)}</anki-mathjax>'
        '<br>\u5176\u4e2d <anki-mathjax>p^0 = E_{\\mathbf{p}}} = '
        '\\sqrt{\\mathbf{p}^2 + m^2}</anki-mathjax>'
    )
    result = _convert_dollar_to_mathjax(html)
    for m in re.finditer(r'<anki-mathjax[^>]*>(.*?)</anki-mathjax>', result, re.DOTALL):
        content = m.group(1)
        assert content.count('{') == content.count('}'), f"Unbalanced: {content}"
    # Specific fix: the FOUR consecutive } (typo) are now THREE (correct)
    assert '\\mathbf{p}}}}' not in result


def test_brace_fix_idempotent():
    r"""Running brace fix twice gives the same result."""
    html = '<anki-mathjax>E_{\\mathbf{p}}}</anki-mathjax>'
    first = _convert_dollar_to_mathjax(html)
    second = _convert_dollar_to_mathjax(first)
    assert first == second


# --- Table conversion Tests ---


def test_table_conversion():
    r"""Ensure MathJax inside HTML tables converts correctly."""
    html = '<table><tr><td><anki-mathjax>W(x,y)</anki-mathjax></td><td>$x^2$</td></tr></table>'
    expected = (
        '<table><tr><td><anki-mathjax>W(x,y)</anki-mathjax></td><td>\\(x^2\\)</td></tr></table>'
    )
    assert _convert_dollar_to_mathjax(html) == expected


def test_autoclose_unclosed_mathjax_at_boundaries():
    r"""Ensure unclosed \( or \[ delimiters are auto-closed at structural HTML boundaries."""
    # Unclosed inline math in a table cell
    html = '<td>\\(1/(k_E^2+m^2)</td>'
    expected = '<td>\\(1/(k_E^2+m^2)\\)</td>'
    assert _convert_dollar_to_mathjax(html) == expected

    # Unclosed display math at the end of the field
    html2 = '\\[math block without end'
    expected2 = '\\[math block without end\\]'
    assert _convert_dollar_to_mathjax(html2) == expected2


def test_code_tag_latex_conversion():
    r"""LaTeX inside <code>...</code> tags on a CJK line is converted to \(...\)."""
    html = (
        '<li><b>发送方窗口变量约束:</b> 必须满足 <code>LastByteSent - SendBase \\le \\min(\\text{cwnd}, \\text{RcvWindow})</code>。'
        '其中 <code>SendBase</code> 为最早未被 ACK 确认的字节序号。</li>'
    )
    expected = (
        '<li><b>发送方窗口变量约束:</b> 必须满足 \\(LastByteSent - SendBase \\le \\min(\\text{cwnd}, \\text{RcvWindow})\\)。'
        '其中 <code>SendBase</code> 为最早未被 ACK 确认的字节序号。</li>'
    )
    assert _convert_dollar_to_mathjax(html) == expected


def test_bare_latex_min_max_commands():
    r"""\min, \max, \inf, \sup are recognized in BARE_LATEX_COMMAND_RE."""
    html = '$a \\min b$'
    assert _convert_dollar_to_mathjax(html) == '\\(a \\min b\\)'


def test_mangled_mathjax_html_repair():
    r"""Mangled HTML tags inside/around MathJax (e.g. \varepsilon^* turned into <i>) are repaired."""
    html = (
        r'<b>电位移矢量</b>（Electric Displacement Field，符号 <anki-mathjax>\mathbf{D}</anki-mathjax>），'
        r'也叫<b>电通量密度</b>，是经典电磁学中的一个基本场量。'
        r'它正是复介电常数 <anki-mathjax>\varepsilon^<i></i></anki-mathjax><i> 定义中直接关联的矢量：'
        r'<anki-mathjax>\mathbf{D} = \varepsilon^</anki-mathjax></i> \mathbf{E}。'
    )
    expected = (
        r'<b>电位移矢量</b>（Electric Displacement Field，符号 <anki-mathjax>\mathbf{D}</anki-mathjax>），'
        r'也叫<b>电通量密度</b>，是经典电磁学中的一个基本场量。'
        r'它正是复介电常数 <anki-mathjax>\varepsilon^*</anki-mathjax> 定义中直接关联的矢量：'
        r'<anki-mathjax>\mathbf{D} = \varepsilon^* \mathbf{E}</anki-mathjax>。'
    )
    assert _convert_dollar_to_mathjax(html) == expected


def test_mangled_mathjax_delim_repair():
    r"""Mangled HTML tags in \(...\) delimiters are also repaired cleanly."""
    html = r'\(x^<i>\)<i> text \(\mathbf{y} = z^\)</i> \mathbf{w}'
    expected = r'\(x^*\) text \(\mathbf{y} = z^* \mathbf{w}\)'
    assert _convert_dollar_to_mathjax(html) == expected


# --- Subscript and Greek LaTeX Command Tests (e.g. \beta_j) ---


def test_subscript_latex_commands_dollar_conversion():
    r"""LaTeX commands with underscore subscripts ($...$) must convert to \(...\)."""
    assert _convert_dollar_to_mathjax(r'$\beta_j$') == r'\(\beta_j\)'
    assert _convert_dollar_to_mathjax(r'$\beta_{j}$') == r'\(\beta_{j}\)'
    assert _convert_dollar_to_mathjax(r'$\sum_i x_i$') == r'\(\sum_i x_i\)'
    assert _convert_dollar_to_mathjax(r'$\alpha_1 + \beta_j = 1$') == r'\(\alpha_1 + \beta_j = 1\)'


def test_bare_subscript_latex_line_conversion():
    r"""A bare line consisting of LaTeX commands with subscripts wraps in \[...\]."""
    assert _convert_dollar_to_mathjax(r'<div>\beta_j</div>') == r'<div>\[\beta_j\]</div>'
    assert _convert_dollar_to_mathjax(r'\beta_{j}') == r'\[\beta_{j}\]'
    assert (
        _convert_dollar_to_mathjax(r'\sum_{j=1}^{p} \beta_j^2') == r'\[\sum_{j=1}^{p} \beta_j^2\]'
    )


def test_subscript_latex_table_cell_conversion():
    r"""Table cell containing bare \beta_j is wrapped in \[...\]."""
    html = '<tr><td style="border: 1px solid #ccc;">\\beta_j</td></tr>'
    expected = '<tr><td style="border: 1px solid #ccc;">\\[\\beta_j\\]</td></tr>'
    assert _convert_dollar_to_mathjax(html) == expected


def test_subscript_latex_code_tag_conversion():
    r"""<code>\beta_j</code> is converted to inline MathJax \(...\)."""
    assert _convert_dollar_to_mathjax(r'<code>\beta_j</code>') == r'\(\beta_j\)'


def test_embedded_subscript_latex_conversion():
    r"""Embedded \beta_j in English prose is wrapped inline in \(...\)."""
    html = r'where \beta_j is the regression coefficient'
    expected = r'where \(\beta_j\) is the regression coefficient'
    assert _convert_dollar_to_mathjax(html) == expected
