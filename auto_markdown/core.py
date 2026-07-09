"""Convert markdown-formatted text in Anki field HTML to rendered HTML.

Anki stores field content as HTML with ``<br>`` line breaks. This module
splits on those boundaries, recognises markdown syntax (headings, bold,
italic, inline code, lists, blockquotes, horizontal rules), and converts
each pattern to the corresponding HTML tag.

Ground rules (from docs/creating-an-addon.md "Field HTML reality"):

- Only ``<br>`` is a line break; literal ``\\n`` is whitespace.
- If nothing changed, the original is returned **byte-identical**.
- Already-converted HTML (``<h4>``, ``<b>``, ``<code>``) and MathJax
  (``\\(…\\)``, ``\\[…\\]``, ``<anki-mathjax>``) are left untouched.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Split HTML on <br> variants, preserving delimiters for reassembly.
_BR_SPLIT_RE = re.compile(r"(<br\s*/?>)", re.IGNORECASE)

# Heading: line starts with 1-6 '#' then mandatory space.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# Unordered list item: line starts with '- ' (not '---' for <hr>).
_UL_RE = re.compile(r"^-\s+(.+)$")

# Ordered list item: line starts with '1. ', '2. ', etc.
_OL_RE = re.compile(r"^\d+\.\s+(.+)$")

# Horizontal rule: exactly '---', '***', or '___' (with optional trailing space).
_HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})\s*$")

# Blockquote: line starts with '> '.
_BQ_RE = re.compile(r"^>\s?(.*)")

# Inline patterns — applied within a line.
# Bold **...**  (non-greedy, no newlines).
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# Italic *...* (single asterisk, after bold handled).
_ITALIC_RE = re.compile(r"(?<!\*)\*([^\s*][^*]*?)\*(?!\*)")
# Inline code `...` (backtick pairs, not inside <code> already).
_CODE_RE = re.compile(r"`([^`]+?)`")

# Already-converted patterns — skip to guarantee idempotency.
_ALREADY_HEADING_RE = re.compile(r"^\s*<h[1-6][^>]*>", re.IGNORECASE)
_ALREADY_HTML_BOLD_RE = re.compile(r"<b\b", re.IGNORECASE)
_ALREADY_HTML_CODE_RE = re.compile(r"<code\b", re.IGNORECASE)
_MATHJAX_RE = re.compile(r"\\[(\[(]|<anki-mathjax", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Inline conversion
# ---------------------------------------------------------------------------


def _convert_inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code) to HTML tags.

    Order matters: code first (protect content), then bold, then italic.
    Already-converted content is skipped.
    """
    if not text:
        return text

    # Skip MathJax content entirely.
    if _MATHJAX_RE.search(text):
        return text

    # Inline code first — protect code content from bold/italic conversion.
    if "`" in text and not _ALREADY_HTML_CODE_RE.search(text):
        text = _CODE_RE.sub(r"<code>\1</code>", text)

    # Bold **...** → <b>...</b>
    if "**" in text and not _ALREADY_HTML_BOLD_RE.search(text):
        text = _BOLD_RE.sub(r"<b>\1</b>", text)

    # Italic *...* → <i>...</i>  (only after bold is handled)
    if "*" in text and "<i>" not in text.lower():
        text = _ITALIC_RE.sub(r"<i>\1</i>", text)

    return text


# ---------------------------------------------------------------------------
# Line-level conversion
# ---------------------------------------------------------------------------


def _convert_line(line: str) -> tuple[str, str]:
    """Convert a single logical line of markdown to HTML.

    Returns (converted_html, line_type) where line_type is one of:
    'heading', 'ul', 'ol', 'hr', 'bq', 'normal'.
    """
    stripped = line.strip()

    # Skip already-converted headings.
    if _ALREADY_HEADING_RE.match(stripped):
        return (line, "normal")

    # Horizontal rule (must check before ul, since '***' overlaps '*').
    m = _HR_RE.match(stripped)
    if m:
        return ("<hr>", "hr")

    # Heading.
    m = _HEADING_RE.match(stripped)
    if m:
        level = len(m.group(1))
        content = _convert_inline(m.group(2))
        return (f"<h{level}>{content}</h{level}>", "heading")

    # Unordered list item.
    m = _UL_RE.match(stripped)
    if m:
        content = _convert_inline(m.group(1))
        return (f"<li>{content}</li>", "ul")

    # Ordered list item.
    m = _OL_RE.match(stripped)
    if m:
        content = _convert_inline(m.group(1))
        return (f"<li>{content}</li>", "ol")

    # Blockquote.
    m = _BQ_RE.match(stripped)
    if m:
        content = _convert_inline(m.group(1))
        return (content, "bq")

    # Normal line — just apply inline conversion.
    return (_convert_inline(line), "normal")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def convert_markdown_field(html: str) -> str:
    """Convert markdown syntax in an Anki field to HTML.

    Splits the field on ``<br>`` boundaries, converts each logical line,
    groups consecutive list items into ``<ul>``/``<ol>`` wrappers, and
    reassembles. Returns the original string byte-identical if nothing
    changed.

    Args:
        html: Raw HTML content of an Anki field.

    Returns:
        HTML string with markdown converted, or the original if unchanged.
    """
    if not html:
        return html

    # Split on <br>, preserving delimiters.
    parts = _BR_SPLIT_RE.split(html)

    converted_parts: list[tuple[str, str]] = []
    for part in parts:
        # Delimiters (the <br> tags themselves) pass through.
        if _BR_SPLIT_RE.match(part):
            converted_parts.append((part, "br"))
        else:
            converted_parts.append(_convert_line(part))

    # Group consecutive list items and blockquote lines.
    output = _assemble(converted_parts)
    result = "".join(output)

    # Byte-identical guarantee.
    if result == html:
        return html
    return result


def _assemble(parts: list[tuple[str, str]]) -> list[str]:
    """Assemble converted parts, wrapping consecutive list/blockquote items.

    Consecutive 'ul' items → <ul>…</ul>, 'ol' → <ol>…</ol>,
    'bq' → <blockquote>…</blockquote>.
    <br> delimiters between same-type items are absorbed into the group;
    <br> delimiters at group boundaries are kept.
    """
    output: list[str] = []
    i = 0
    n = len(parts)

    while i < n:
        text, kind = parts[i]

        if kind in ("ul", "ol"):
            # Collect consecutive list items of the same type, skipping <br> between them.
            tag = kind
            items: list[str] = [text]
            j = i + 1
            while j < n:
                t2, k2 = parts[j]
                if k2 == "br":
                    # Look ahead: if next non-br is same list type, skip this <br>.
                    peek = j + 1
                    if peek < n and parts[peek][1] == tag:
                        j += 1  # skip the <br>
                        continue
                    else:
                        break
                elif k2 == tag:
                    items.append(t2)
                    j += 1
                else:
                    break
            wrapper = "ul" if tag == "ul" else "ol"
            output.append(f"<{wrapper}>{''.join(items)}</{wrapper}>")
            i = j

        elif kind == "bq":
            # Collect consecutive blockquote lines, turning <br> between them
            # back into <br> inside the blockquote.
            lines: list[str] = [text]
            j = i + 1
            while j < n:
                t2, k2 = parts[j]
                if k2 == "br":
                    peek = j + 1
                    if peek < n and parts[peek][1] == "bq":
                        lines.append("<br>")
                        j += 1  # skip the <br> part
                        continue
                    else:
                        break
                elif k2 == "bq":
                    lines.append(t2)
                    j += 1
                else:
                    break
            output.append(f"<blockquote>{''.join(lines)}</blockquote>")
            i = j

        else:
            output.append(text)
            i += 1

    return output
