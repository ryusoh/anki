# Auto MathJax Inline Button — Anki Editor Addon
# Scans the current field for $...$ patterns on the same line
# and converts them to Anki's native MathJax inline format \(...\).
#
# How it works:
#   1. Button click triggers Python handler
#   2. Python reads the raw HTML of the current field
#   3. Splits into logical lines (by <br>, <div>, </p>, \n)
#   4. On each line, finds $...$ pairs via regex
#   5. Validates each match (not numeric-only, not empty, not prose —
#      stock cashtags like "$INTC ... $SOI" and "$$" as money slang
#      regex-match as pairs but must never convert)
#   6. Replaces $content$ with \(content\)
#   7. Lines that are entirely bare LaTeX (e.g. \frac{...} with no $ at all)
#      are wrapped whole in \[...\] display math; bare LaTeX fragments
#      embedded in a prose line are wrapped inline in \(...\); the interior
#      of an existing multi-line \[...\] block is left untouched
#   8. Writes the modified HTML back and reloads the field

import os
import re

from aqt import gui_hooks
from aqt.editor import Editor
from aqt.utils import tooltip
from bs4 import BeautifulSoup

ADDON_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(ADDON_DIR, "icon.png")

# Regex to split HTML into logical lines.
# We split on <br>, <div>, <p>, and other structural block/table tags,
# or literal newlines, but PRESERVE the delimiters so we can reassemble exactly.
# MathJax formulas do not span across these structural boundaries.
LINE_SPLIT_RE = re.compile(
    r'(<br\s*/?>|</?(?:div|p|table|tbody|thead|tfoot|tr|td|th|ul|ol|li|blockquote|h[1-6])[^>]*>|\n)',
    re.IGNORECASE,
)

# Combined regex: match $$...$$ (block) FIRST, then $...$ (inline).
# - Group 1: block math content (between $$...$$)
# - Group 2: inline math content (between $...$)
# The $$...$$ alternative comes first so it takes priority.
DOLLAR_PAIR_RE = re.compile(r'(?<!\\)\$\$([^$]+?)\$\$|(?<!\\)\$([^$\n]+?)\$')

# Patterns indicating content is already MathJax-wrapped
ALREADY_MATHJAX_RE = re.compile(r'\\[(\(|\[]|<anki-mathjax', re.IGNORECASE)

# Whitelisted LaTeX commands that mark a line as bare LaTeX. A generic
# \[a-zA-Z]+ would false-positive on Windows paths like C:\Users\name.
BARE_LATEX_COMMAND_RE = re.compile(
    r'\\(?:'
    r'frac|dfrac|tfrac|text|times|sqrt|sum|prod|int|cdot|pm|mp|div(?:isionsymbol)?|'
    r'oiiint|oiint|oint|'
    r'leq?|geq?|neq|approx|equiv|propto|infty|log|ln|exp|sin|cos|tan|lim|min|max|inf|sup|argmin|argmax|'
    r'partial|nabla|to|rightarrow|Rightarrow|left|right|over|hat|bar|vec|'
    r'mathbb|mathrm|mathbf|mathit|operatorname|'
    r'alpha|beta|gamma|Gamma|delta|Delta|epsilon|theta|lambdabar|lambda|mu|pi|rho|'
    r'sigma|Sigma|tau|phi|Phi|omega|Omega'
    r')\b'
)

CODE_TAG_RE = re.compile(r'<code>(.*?)</code>', re.IGNORECASE | re.DOTALL)

# \text-like groups whose braces hold prose, not math — their contents must
# not count against the "leftover prose" check below.
TEXT_GROUP_RE = re.compile(r'\\(?:text|textbf|textit|mathrm|mathbf|operatorname)\s*\{[^{}]*\}')

# Any \command token (for stripping when measuring leftover prose)
ANY_LATEX_COMMAND_RE = re.compile(r'\\[a-zA-Z]+')

# CJK ideographs, kana, and fullwidth punctuation. Natural-language text in
# these scripts never appears inside a formula (outside \text{...} groups),
# so it marks $-pair content or a bare line as prose.
CJK_RE = re.compile('[\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]')

HTML_TAG_RE = re.compile(r'<[^>]+>')

# MathJax open/close delimiters, for tracking a \[...\] (or \(...\)) block
# that spans multiple logical lines: everything until the closer is already
# math and must not be touched.
MATH_DELIM_RE = re.compile(r'\\([\[\]()])')
_MATH_CLOSER = {'[': ']', '(': ')'}

# A "math run" embedded in a prose line: one or more \command tokens (brace
# arguments, nesting depth <= 2) linked by numbers/operators/whitespace.
# Letters are deliberately excluded from the filler so prose words never get
# pulled into a run, and <, >, & break a run so HTML tags/entities stay out.
_EMBEDDED_TOKEN = r'\\[a-zA-Z]+(?:\s*\{(?:[^{}<>&]|\{[^{}<>&]*\})*\})*'
_EMBEDDED_FILLER = r'[0-9\s=+\-*/^_().,%]'
EMBEDDED_RUN_RE = re.compile(
    _EMBEDDED_FILLER + r'*(?:' + _EMBEDDED_TOKEN + _EMBEDDED_FILLER + r'*)+'
)

# Standalone integral symbols: self-contained glyphs that take no operand
# and never appear in prose as anything but LaTeX. Safe to wrap even in CJK
# lines (where embedded-run wrapping is skipped) and even without a braced
# or numeric operand. The \b keeps operand-taking uses like \oint_C out.
STANDALONE_SYMBOL_RE = re.compile(r'\\(?:oiiint|oiint|oint)\b')

# Characters trimmed off the ends of a math run before wrapping: sentence
# punctuation and a leading/trailing "=" that reads as prose glue
# (e.g. "<b>Quick Ratio</b> = \frac{...}").
_RUN_TRIM_CHARS = '.,;:= \t'

# Custom macro definitions for commands MathJax doesn't know natively.
# Each key is a command name (without backslash); the value is the TeX
# replacement body.  When a converted field contains one of these commands,
# a hidden preamble block (\def\cmd{body}) is prepended so MathJax learns
# it before encountering the usage.
CUSTOM_MACROS = {
    'lambdabar': r'\unicode{x019B}',
    # esint closed integrals — Anki's bundled MathJax has no esint
    # extension, so \oiint / \oiiint render as red "undefined control
    # sequence" errors. Emulate the glyphs: a circle overlaid on
    # \iint / \iiint (negative \mkern pulls the integrals back over
    # the \bigcirc; tune the mu value if the overlay looks off-center).
    'oiint': r'\mathop{\bigcirc\mkern-14mu\iint}',
    'oiiint': r'\mathop{\bigcirc\mkern-14mu\iiint}',
}

# Matches <anki-mathjax ...>content</anki-mathjax> blocks (inline and display)
ANKI_MATHJAX_RE = re.compile(
    r'(<anki-mathjax[^>]*>)(.*?)(</anki-mathjax>)', re.DOTALL | re.IGNORECASE
)

# Matches \[...\] and \(...\) MathJax delimiter blocks
MATHJAX_DELIM_RE = re.compile(r'(\\\[)(.*?)(\\\])|(\\\()(.*?)(\\\))', re.DOTALL)


def _is_purely_numeric(s):
    """Check if the text content (tags stripped) is purely numeric/currency-like.

    Returns True for things like '100', '5.99', '1,000', '50.00' — common
    dollar-amount patterns that should NOT be converted to MathJax.
    """
    # Strip any HTML tags to get text-only
    text = re.sub(r'<[^>]+>', '', s).strip()
    # Match: optional sign, digits with optional commas/periods
    return bool(re.match(r'^[+-]?[\d,]+\.?\d*$', text))


def _is_whitespace_only(s):
    """Check if content between $ signs is only whitespace."""
    text = re.sub(r'<[^>]+>', '', s).strip()
    return len(text) == 0


def _decode_entities(s):
    return s.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')


def _looks_like_math_content(inner):
    """Decide whether the content of a $...$/$$...$$ pair plausibly is math.

    Stock cashtags ($INTC ... $SOI), $$ as slang for money, and prose
    between two currency amounts all regex-match as pairs. A formula never
    spans HTML tags, never contains CJK prose (outside \\text{...} groups),
    and its words are short variable names — unless an explicit \\command
    marks it as LaTeX. A single word with no whitespace ($math$) still
    counts as a variable name.
    """
    if HTML_TAG_RE.search(inner):
        return False
    text = _decode_entities(inner)
    if BARE_LATEX_COMMAND_RE.search(text):
        return True
    stripped = TEXT_GROUP_RE.sub(' ', text)
    stripped = ANY_LATEX_COMMAND_RE.sub(' ', stripped)
    if CJK_RE.search(stripped):
        return False
    # A dangling superscript/subscript operator (^/_) with no operand is not
    # valid LaTeX; MathJax renders it as a red-on-yellow error.
    core = stripped.strip()
    if core and (core[0] in '^_' or core[-1] in '^_'):
        return False
    if re.fullmatch(r'[a-zA-Z]+', text):
        return True
    return all(len(word) <= 2 for word in re.findall(r'[a-zA-Z]+', stripped))


def _track_math_state(open_delim, segment):
    """Advance the open-MathJax-delimiter state ('[', '(' or None) across
    one logical line, so multi-line \\[...\\] blocks are recognized."""
    for m in MATH_DELIM_RE.finditer(segment):
        tok = m.group(1)
        if open_delim is None:
            if tok in _MATH_CLOSER:
                open_delim = tok
        elif tok == _MATH_CLOSER[open_delim]:
            open_delim = None
    return open_delim


def _looks_like_bare_latex(segment):
    """Decide whether a logical line is a bare LaTeX formula (no $ delimiters).

    True only when the line contains a whitelisted LaTeX command, has no $
    or HTML tags, and — once \\text{...} groups and \\commands are stripped —
    nothing prose-like remains (only short variable names like PV, r, n).
    """
    text = segment.replace('&nbsp;', ' ')
    if '$' in text or '<' in text:
        return False
    if not BARE_LATEX_COMMAND_RE.search(text):
        return False
    stripped = TEXT_GROUP_RE.sub(' ', text)
    stripped = ANY_LATEX_COMMAND_RE.sub(' ', stripped)
    if CJK_RE.search(stripped):
        return False
    return all(len(word) <= 2 for word in re.findall(r'[a-zA-Z]+', stripped))


def _convert_code_latex(segment):
    """Convert <code>...</code> blocks containing whitelisted LaTeX commands to \\(...\\)."""

    def repl(m):
        inner = m.group(1)
        if BARE_LATEX_COMMAND_RE.search(inner) and not CJK_RE.search(inner):
            core = inner.strip()
            return '\\(' + core + '\\)'
        return m.group(0)

    return CODE_TAG_RE.sub(repl, segment)


def _wrap_embedded_latex(segment):
    """Wrap bare-LaTeX fragments inside a prose/HTML line in \\(...\\).

    Used when a line mixes prose (or inline tags) with LaTeX, e.g.
    "<b>Quick Ratio</b> = \\frac{100,000}{60,000} = 1.67". Only runs
    containing a whitelisted command are wrapped; surrounding prose,
    tags and entities are untouched.
    """
    segment = _convert_code_latex(segment)
    # A CJK prose line is not a formula card: letters break embedded runs,
    # so wrapping fragments there mangles shapes like (E\ln(1+r)>0).
    # Standalone integral symbols (\oint & friends) are still wrapped —
    # they are unambiguous LaTeX and take no operand.
    if CJK_RE.search(TEXT_GROUP_RE.sub(' ', segment)):
        return STANDALONE_SYMBOL_RE.sub(r'\\(\g<0>\\)', segment)
    # {\displaystyle ...} marks LaTeX source pasted from Wikipedia/MathML —
    # it renders via its own <img>/<math> fallback; wrapping fragments of
    # it (e.g. just "(\log" out of O(\log N)) mangles the source.
    if '\\displaystyle' in segment:
        return segment

    def repl(m):
        run = m.group(0)
        if not BARE_LATEX_COMMAND_RE.search(run):
            return run
        core = run.strip(_RUN_TRIM_CHARS)
        if not core:
            return run
        # A bare \command with no braced or numeric operand (Wikipedia's
        # {\displaystyle O(\log N)} pastes) is not a self-contained formula —
        # unless it is a standalone integral symbol (\oint & friends).
        if not re.search(r'[{0-9]', core) and not STANDALONE_SYMBOL_RE.fullmatch(core):
            return run
        start = run.find(core)
        return run[:start] + '\\(' + core + '\\)' + run[start + len(core) :]

    return EMBEDDED_RUN_RE.sub(repl, segment)


def _inject_macro_defs(html_str):
    """Prepend hidden \\\\def preambles for custom macros found in *html_str*.

    Scans for commands listed in CUSTOM_MACROS.  For each one found whose
    \\\\def is not already present, a ``\\\\(\\\\def\\\\cmd{body}\\\\)`` preamble is
    prepended (invisible — MathJax processes it but renders nothing).

    Idempotent: re-running on output that already has the preamble is safe.
    """
    if not CUSTOM_MACROS:
        return html_str

    defs_needed = []
    for cmd, body in CUSTOM_MACROS.items():
        cmd_token = '\\' + cmd  # e.g. \lambdabar  (1 backslash)
        def_token = '\\def\\' + cmd  # e.g. \def\lambdabar
        # Command is used somewhere in the field, and not already defined
        if cmd_token in html_str and def_token not in html_str:
            defs_needed.append(f'\\def\\{cmd}{{{body}}}')

    if not defs_needed:
        return html_str

    preamble = '\\(' + ' '.join(defs_needed) + '\\)'
    return preamble + html_str


def _fix_unbalanced_braces(content):
    """Fix unbalanced braces in a LaTeX string.

    Scans left-to-right tracking brace depth.  A ``}`` that would push
    depth below zero is silently dropped (extra closing brace typo).
    After the scan, any remaining unclosed ``{`` are closed by appending
    ``}`` characters.  Escaped braces (``\\{`` / ``\\}``) are treated as
    literal display characters and do not affect depth.
    """
    result = []
    depth = 0
    i = 0
    while i < len(content):
        ch = content[i]
        # Escaped brace — literal, not grouping
        if ch == '\\' and i + 1 < len(content) and content[i + 1] in '{}':
            result.append(content[i : i + 2])
            i += 2
            continue
        if ch == '{':
            depth += 1
            result.append(ch)
        elif ch == '}':
            if depth > 0:
                depth -= 1
                result.append(ch)
            # else: skip this extra }
        else:
            result.append(ch)
        i += 1
    # Append missing closing braces
    result.extend('}' * depth)
    return ''.join(result)


def _fix_mathjax_braces(html_str):
    """Fix unbalanced braces inside all MathJax blocks in *html_str*.

    Covers ``<anki-mathjax>``, ``\\[...\\]``, and ``\\(...\\)`` blocks.
    Content outside math delimiters is untouched.
    """

    def _fix_anki(m):
        fixed = _fix_unbalanced_braces(m.group(2))
        return m.group(1) + fixed + m.group(3)

    def _fix_delim(m):
        if m.group(1) is not None:
            opener, content, closer = m.group(1), m.group(2), m.group(3)
        else:
            opener, content, closer = m.group(4), m.group(5), m.group(6)
        return opener + _fix_unbalanced_braces(content) + closer

    html_str = ANKI_MATHJAX_RE.sub(_fix_anki, html_str)
    return MATHJAX_DELIM_RE.sub(_fix_delim, html_str)


def _clean_mathjax_nbsp(html_str):
    """Remove ``&nbsp;`` noise from inside MathJax blocks.

    Covers all three delimiter styles: ``<anki-mathjax>``, ``\\[...\\]``,
    and ``\\(...\\)``.  Handles ``&amp;nbsp;`` (double-encoded), ``&nbsp;``
    (HTML entity), and the Unicode non-breaking space U+00A0.
    Content outside math blocks is left untouched.
    """

    def _scrub_content(content):
        content = content.replace('&amp;nbsp;', '')
        content = content.replace('&nbsp;', '')
        content = content.replace('\xa0', '')
        return content.strip()

    def _scrub_anki(m):
        return m.group(1) + _scrub_content(m.group(2)) + m.group(3)

    def _scrub_delim(m):
        # Groups 1-3 for \[...\], groups 4-6 for \(...\)
        if m.group(1) is not None:
            opener, content, closer = m.group(1), m.group(2), m.group(3)
        else:
            opener, content, closer = m.group(4), m.group(5), m.group(6)
        return opener + _scrub_content(content) + closer

    html_str = ANKI_MATHJAX_RE.sub(_scrub_anki, html_str)
    return MATHJAX_DELIM_RE.sub(_scrub_delim, html_str)


def _unwrap_mathjax_from_pre(html_str):
    """Unwrap MathJax blocks that are trapped inside ``<pre>`` tags.

    Anki's editor renders ``\\(...\\)`` / ``\\[...\\]`` by converting them to
    ``<anki-mathjax>`` itself, so it does not care about ``<pre>`` wrappers.
    The reviewer's MathJax tex2jax preprocessor, however, skips ``<pre>``
    (and ``<code>``) by default, so the same field shows raw code during
    review. Remove ``<pre>`` wrappers whose only real content is a MathJax
    block, and drop any ``<pre>`` tags left empty by the unwrap.
    """
    if '<pre' not in html_str.lower():
        return html_str

    soup = BeautifulSoup(html_str, 'html.parser')
    math_block_re = re.compile(r'\\\[.*\\\]|\\\(.*\\\)', re.DOTALL)

    changed = True
    while changed:
        changed = False
        for pre in soup.find_all('pre'):
            text = pre.get_text(strip=True)
            if re.fullmatch(math_block_re, text):
                pre.unwrap()
                changed = True
                break

    for pre in list(soup.find_all('pre')):
        if not pre.get_text(strip=True):
            pre.decompose()

    return str(soup)


def _convert_dollar_to_mathjax(html_str):
    """Convert $...$ patterns to \\(...\\) MathJax inline notation.

    Only matches pairs of $ on the same logical line. Skips content that
    is already MathJax-wrapped, purely numeric, or whitespace-only.

    Additionally, a logical line consisting entirely of bare LaTeX (commands
    like \\frac/\\text but no $ delimiters at all) is wrapped whole in
    \\[...\\] display math.

    Args:
        html_str: Raw HTML content of an Anki field.

    Returns:
        Modified HTML string with $...$ converted to \\(...\\).
    """
    if not html_str:
        return html_str

    # Split into segments (alternating: content, delimiter, content, ...)
    segments = LINE_SPLIT_RE.split(html_str)

    result_parts = []
    open_delim = None  # inside a \[...\] / \(...\) block spanning lines
    for segment in segments:
        # If this segment is a delimiter (tag/newline), pass through unchanged
        if LINE_SPLIT_RE.match(segment):
            # Auto-close unclosed MathJax blocks before structural HTML boundaries
            if open_delim is not None and not segment.lower().startswith(('<br', '\n')):
                closer = '\\)' if open_delim == '(' else '\\]'
                result_parts.append(closer)
                open_delim = None
            result_parts.append(segment)
            continue

        # Interior of a multi-line \[...\] block opened on an earlier line
        # is already math — pass through until the closing delimiter.
        if open_delim is not None:
            result_parts.append(segment)
            open_delim = _track_math_state(open_delim, segment)
            continue

        # Skip segments that already contain MathJax notation
        if ALREADY_MATHJAX_RE.search(segment):
            result_parts.append(segment)
            open_delim = _track_math_state(open_delim, segment)
            continue

        # Find and replace $$...$$ and $...$ pairs in this segment
        def replace_match(m):
            block_inner = m.group(1)  # from $$...$$
            inline_inner = m.group(2)  # from $...$

            if block_inner is not None:
                # $$...$$ → \[...\] (block/display MathJax)
                if _is_whitespace_only(block_inner):
                    return m.group(0)
                # $$ as slang for money: "big $$. ... pool $$." pairs up
                # with prose between — leave it alone.
                if not _looks_like_math_content(block_inner):
                    return m.group(0)
                return '\\[' + block_inner + '\\]'

            # $...$ → \(...\) (inline MathJax)
            inner = inline_inner

            # Skip purely numeric content (e.g., $100$)
            if _is_purely_numeric(inner):
                return m.group(0)  # return unchanged

            # A real closing $ is never immediately followed by a letter or
            # digit: that $ is the prefix of the next cashtag ($JD $BABA,
            # $ORCL/$MSFT), a currency amount ("for every $1 of ..."), or
            # part of an identifier (5npiei$lrn$1@thor.atcon.com).
            nxt = m.string[m.end()] if m.end() < len(m.string) else ''
            if nxt.isascii() and nxt.isalnum():
                return m.group(0)  # return unchanged

            # Skip whitespace-only content
            if _is_whitespace_only(inner):
                return m.group(0)  # return unchanged

            # Stock cashtags ($INTC ... $SOI) and other prose between two
            # $ signs regex-match as a pair but are not math.
            if not _looks_like_math_content(inner):
                return m.group(0)  # return unchanged

            # Convert to MathJax inline
            return '\\(' + inner + '\\)'

        converted = DOLLAR_PAIR_RE.sub(replace_match, segment)

        # Bare LaTeX (no $ anywhere): a whole-line formula becomes display
        # math; otherwise wrap just the embedded fragments inline.
        if converted == segment and '$' not in segment:
            if _looks_like_bare_latex(segment):
                core = segment.strip()
                lead = segment[: len(segment) - len(segment.lstrip())]
                trail = segment[len(segment.rstrip()) :]
                converted = lead + '\\[' + core + '\\]' + trail
            else:
                converted = _wrap_embedded_latex(segment)

        result_parts.append(converted)

    if open_delim is not None:
        closer = '\\)' if open_delim == '(' else '\\]'
        result_parts.append(closer)

    converted_html = ''.join(result_parts)
    converted_html = _clean_mathjax_nbsp(converted_html)
    converted_html = _fix_mathjax_braces(converted_html)
    converted_html = _unwrap_mathjax_from_pre(converted_html)
    return _inject_macro_defs(converted_html)


def _apply_mathjax(editor):
    """Read current field, convert $...$ to MathJax, write back."""
    if editor.note is None or editor.currentField is None:
        return
    idx = editor.currentField
    if idx < 0 or idx >= len(editor.note.fields):
        return

    html_str = editor.note.fields[idx]
    new_html = _convert_dollar_to_mathjax(html_str)

    # Only update if something actually changed. Always say what happened —
    # a silent no-op is indistinguishable from "the button did nothing",
    # which makes wrong-field focus impossible to diagnose.
    if new_html == html_str:
        tooltip(
            f"auto_mathjax: nothing to convert in field {idx + 1} — "
            "click into the field that contains the math first."
        )
        return

    editor.note.fields[idx] = new_html
    if not editor.addMode:
        try:
            editor.note.flush()
        except Exception as e:
            print(f"Error flushing note in auto_mathjax: {e}")
    try:
        editor.loadNoteKeepingFocus()
    except Exception as e:
        print(f"Error loading note in auto_mathjax: {e}")

    tooltip(f"auto_mathjax: converted field {idx + 1}.")


def on_auto_mathjax(editor: Editor) -> None:
    """Button handler: sync field from webview, then convert $...$ to MathJax."""
    editor.call_after_note_saved(lambda: _apply_mathjax(editor))


def on_editor_did_init_buttons(buttons: list, editor: Editor) -> None:
    btn = editor.addButton(
        ICON_PATH,
        "autoMathJax",
        on_auto_mathjax,
        tip="Auto MathJax: convert $...$ to inline MathJax (current field)",
    )
    buttons.append(btn)


gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
