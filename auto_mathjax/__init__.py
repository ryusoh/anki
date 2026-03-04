# Auto MathJax Inline Button — Anki Editor Addon
# Scans the current field for $...$ patterns on the same line
# and converts them to Anki's native MathJax inline format \(...\).
#
# How it works:
#   1. Button click triggers Python handler
#   2. Python reads the raw HTML of the current field
#   3. Splits into logical lines (by <br>, <div>, </p>, \n)
#   4. On each line, finds $...$ pairs via regex
#   5. Validates each match (not numeric-only, not empty, etc.)
#   6. Replaces $content$ with \(content\)
#   7. Writes the modified HTML back and reloads the field

import os
import re
from aqt import gui_hooks
from aqt.editor import Editor

ADDON_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(ADDON_DIR, "icon.png")

# Regex to split HTML into logical lines.
# We split on <br>, <br/>, <div>, </div>, </p>, or literal newlines,
# but PRESERVE the delimiters so we can reassemble exactly.
LINE_SPLIT_RE = re.compile(r'(<br\s*/?>|</?div[^>]*>|</p[^>]*>|\n)', re.IGNORECASE)

# Combined regex: match $$...$$ (block) FIRST, then $...$ (inline).
# - Group 1: block math content (between $$...$$)
# - Group 2: inline math content (between $...$)
# The $$...$$ alternative comes first so it takes priority.
DOLLAR_PAIR_RE = re.compile(r'(?<!\\)\$\$([^$]+?)\$\$|(?<!\\)\$([^$\n]+?)\$')

# Patterns indicating content is already MathJax-wrapped
ALREADY_MATHJAX_RE = re.compile(r'\\[(\(|\[]|<anki-mathjax', re.IGNORECASE)


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


def _convert_dollar_to_mathjax(html_str):
    """Convert $...$ patterns to \\(...\\) MathJax inline notation.

    Only matches pairs of $ on the same logical line. Skips content that
    is already MathJax-wrapped, purely numeric, or whitespace-only.

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
    for segment in segments:
        # If this segment is a delimiter (tag/newline), pass through unchanged
        if LINE_SPLIT_RE.match(segment):
            result_parts.append(segment)
            continue

        # Skip segments that already contain MathJax notation
        if ALREADY_MATHJAX_RE.search(segment):
            result_parts.append(segment)
            continue

        # Find and replace $$...$$ and $...$ pairs in this segment
        def replace_match(m):
            block_inner = m.group(1)   # from $$...$$
            inline_inner = m.group(2)  # from $...$

            if block_inner is not None:
                # $$...$$ → \[...\] (block/display MathJax)
                if _is_whitespace_only(block_inner):
                    return m.group(0)
                return '\\[' + block_inner + '\\]'

            # $...$ → \(...\) (inline MathJax)
            inner = inline_inner

            # Skip purely numeric content (e.g., $100$)
            if _is_purely_numeric(inner):
                return m.group(0)  # return unchanged

            # Skip whitespace-only content
            if _is_whitespace_only(inner):
                return m.group(0)  # return unchanged

            # Convert to MathJax inline
            return '\\(' + inner + '\\)'

        converted = DOLLAR_PAIR_RE.sub(replace_match, segment)
        result_parts.append(converted)

    return ''.join(result_parts)


def _apply_mathjax(editor):
    """Read current field, convert $...$ to MathJax, write back."""
    if editor.note is None or editor.currentField is None:
        return
    idx = editor.currentField
    if idx < 0 or idx >= len(editor.note.fields):
        return

    html_str = editor.note.fields[idx]
    new_html = _convert_dollar_to_mathjax(html_str)

    # Only update if something actually changed
    if new_html == html_str:
        return

    editor.note.fields[idx] = new_html
    if not editor.addMode:
        try:
            editor.note.flush()
        except Exception:
            pass
    try:
        editor.loadNoteKeepingFocus()
    except Exception:
        pass


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
