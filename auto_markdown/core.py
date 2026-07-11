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

# Blockquote: line starts with '> ' or '&gt; '.
_BQ_RE = re.compile(r"^(?:>|&gt;)\s?(.*)")

# Inline patterns — applied within a line.
# Bold **...**  (non-greedy, no newlines).
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# Italic *...* (single asterisk, after bold handled).
_ITALIC_RE = re.compile(r"(?<!\*)\*([^\s*][^*]*?)\*(?!\*)")
# Inline code `...` (backtick pairs, not inside <code> already).
_CODE_RE = re.compile(r"`([^`]+?)`")

# Already-converted patterns — skip to guarantee idempotency.
_ALREADY_HEADING_RE = re.compile(r"^\s*<h[1-6][^>]*>", re.IGNORECASE)
_MATHJAX_RE = re.compile(r"\\[(\[(]|<anki-mathjax", re.IGNORECASE)
_MATHJAX_BLOCKS_RE = re.compile(
    r"(\\\\\(.*?\\\\\)|\\\\\\[.*?\\\\\\]|<anki-mathjax[^>]*>.*?</anki-mathjax>)", re.IGNORECASE
)


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

    # Find and protect MathJax blocks.
    mathjax_blocks = []

    def protect_mathjax(match):
        placeholder = f"__MATHJAX_PLACEHOLDER_{len(mathjax_blocks)}__"
        mathjax_blocks.append(match.group(0))
        return placeholder

    protected_text = _MATHJAX_BLOCKS_RE.sub(protect_mathjax, text)

    # Inline code first — protect code content from bold/italic conversion.
    if "`" in protected_text:
        protected_text = _CODE_RE.sub(r"<code>\1</code>", protected_text)

    # Bold **...** → <b>...</b>
    if "**" in protected_text:
        protected_text = _BOLD_RE.sub(r"<b>\1</b>", protected_text)

    # Italic *...* → <i>...</i>  (only after bold is handled)
    if "*" in protected_text and "<i>" not in protected_text.lower():
        protected_text = _ITALIC_RE.sub(r"<i>\1</i>", protected_text)

    # Restore MathJax blocks.
    for idx, block in enumerate(mathjax_blocks):
        placeholder = f"__MATHJAX_PLACEHOLDER_{idx}__"
        protected_text = protected_text.replace(placeholder, block)

    return protected_text


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
# Code Blocks & Tables Parsing Helpers
# ---------------------------------------------------------------------------


def _parse_code_blocks(parts: list[tuple[str, bool]]) -> list[tuple[str, str]]:
    """Identifies code blocks in the parts list.

    parts is a list of (content, is_br).
    Returns a list of (content, type) where type is 'code_block', 'br', or 'text'.
    """
    result: list[tuple[str, str]] = []
    i = 0
    n = len(parts)
    while i < n:
        content, is_br = parts[i]
        if is_br:
            result.append((content, "br"))
            i += 1
            continue

        stripped = content.strip()
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            # Find the closing ```
            j = i + 1
            code_lines: list[str] = []
            closed = False
            while j < n:
                c2, is_br2 = parts[j]
                if is_br2:
                    code_lines.append(c2)
                    j += 1
                    continue
                if c2.strip() == "```":
                    closed = True
                    break
                code_lines.append(c2)
                j += 1

            if closed:
                # Strip leading/trailing <br>s
                if code_lines and _BR_SPLIT_RE.match(code_lines[0]):
                    code_lines.pop(0)
                if code_lines and _BR_SPLIT_RE.match(code_lines[-1]):
                    code_lines.pop()
                code_content = "".join(code_lines)
                class_attr = f' class="language-{lang}"' if lang else ""
                style = (
                    'style="background-color: #1e1e1e; color: #d4d4d4; padding: 12px 16px; '
                    'border-radius: 6px; overflow-x: auto; font-family: SFMono-Regular, Consolas, '
                    'Liberation Mono, Menlo, monospace; font-size: 0.85em; line-height: 1.5; margin: 10px 0;"'
                )
                code_html = f"<pre {style}><code{class_attr}>{code_content}</code></pre>"
                result.append((code_html, "code_block"))
                i = j + 1
                continue

        result.append((content, "text"))
        i += 1
    return result


def _is_table_row(content: str) -> bool:
    stripped = content.strip()
    return stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 1


def _is_separator_row(content: str) -> bool:
    if not _is_table_row(content):
        return False
    cells = [c.strip() for c in content.split("|")[1:-1]]
    if not cells:
        return False
    for cell in cells:
        if not cell:
            return False
        if not re.match(r"^:?-+:?$", cell):
            return False
    return True


# A table row glued onto preceding HTML with no <br> before it — Anki's
# paste sometimes opens/closes a block tag (e.g. `</ul><div>`) right before
# a table's first row instead of inserting <br>. `.*` is greedy so this
# anchors on the LAST such tag, which is the boundary immediately before
# the row; inline tags (<b>, <i>, ...) that can legitimately appear inside
# a cell are not in the tag set, so they can't be mistaken for the boundary.
_BLOCK_BOUNDARY_TABLE_ROW_RE = re.compile(
    r"^(.*</?(?:div|ul|ol|li|p|blockquote|h[1-6])\b[^>]*>)\s*(\|.+\|)\s*$",
    re.IGNORECASE | re.DOTALL,
)


def _split_leading_block_boundary_row(parts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Splits a table row glued onto preceding HTML into (prefix, row) parts.

    Without this, a part like `</ul><div>| a | b |` fails `_is_table_row`
    (it doesn't start with '|'), so `_parse_tables` never sees the row.
    """
    result: list[tuple[str, str]] = []
    for content, kind in parts:
        if kind == "text" and not _is_table_row(content):
            m = _BLOCK_BOUNDARY_TABLE_ROW_RE.match(content)
            if m and _is_table_row(m.group(2).strip()):
                result.append((m.group(1), "text"))
                result.append((m.group(2).strip(), "text"))
                continue
        result.append((content, kind))
    return result


def _parse_alignment(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    elif cell.startswith(":"):
        return "left"
    elif cell.endswith(":"):
        return "right"
    return ""


def _parse_tables(parts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Groups table rows and parses them into HTML tables."""
    result: list[tuple[str, str]] = []
    i = 0
    n = len(parts)
    while i < n:
        content, kind = parts[i]
        if kind != "text" or not _is_table_row(content):
            result.append((content, kind))
            i += 1
            continue

        # Found candidate header row. Look ahead for separator.
        has_sep = False
        sep_index = -1

        j = i + 1
        if j < n and parts[j][1] == "br":
            j += 1
        if j < n and parts[j][1] == "text" and _is_separator_row(parts[j][0]):
            has_sep = True
            sep_index = j

        if not has_sep:
            result.append((content, kind))
            i += 1
            continue

        # Parse alignments from separator
        sep_content = parts[sep_index][0]
        sep_cells = [c.strip() for c in sep_content.split("|")[1:-1]]
        alignments = [_parse_alignment(c) for c in sep_cells]
        num_cols = len(sep_cells)

        # Parse header row
        header_cells = [c.strip() for c in content.split("|")[1:-1]]
        while len(header_cells) < num_cols:
            header_cells.append("")
        header_cells = header_cells[:num_cols]

        header_html_parts = []
        for col_idx, cell in enumerate(header_cells):
            align = alignments[col_idx] if col_idx < len(alignments) else ""
            align_css = f"text-align: {align};" if align else ""
            style = f'style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; {align_css}"'
            cell_html = _convert_inline(cell)
            header_html_parts.append(f"<th {style}>{cell_html}</th>")

        thead_html = f"<thead><tr>{''.join(header_html_parts)}</tr></thead>"

        tbody_rows = []
        curr = sep_index + 1

        while curr < n:
            if parts[curr][1] == "br":
                curr += 1
                continue

            if (
                parts[curr][1] == "text"
                and _is_table_row(parts[curr][0])
                and not _is_separator_row(parts[curr][0])
            ):
                row_content = parts[curr][0]
                row_cells = [c.strip() for c in row_content.split("|")[1:-1]]
                while len(row_cells) < num_cols:
                    row_cells.append("")
                row_cells = row_cells[:num_cols]

                row_html_parts = []
                for col_idx, cell in enumerate(row_cells):
                    align = alignments[col_idx] if col_idx < len(alignments) else ""
                    align_css = f"text-align: {align};" if align else ""
                    style = f'style="border: 1px solid #ccc; padding: 6px 10px; {align_css}"'
                    cell_html = _convert_inline(cell)
                    row_html_parts.append(f"<td {style}>{cell_html}</td>")
                tbody_rows.append(f"<tr>{''.join(row_html_parts)}</tr>")
                curr += 1
            else:
                break

        tbody_html = f"<tbody>{''.join(tbody_rows)}</tbody>" if tbody_rows else ""
        table_html = f'<table style="border-collapse: collapse;">{thead_html}{tbody_html}</table>'

        result.append((table_html, "table"))
        i = curr

    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


BLOCK_KINDS = {"heading", "ul", "ol", "table", "code_block", "bq", "hr"}


def _clean_spacings(parts: list[tuple[str, str]]) -> list[str]:
    """Cleans up redundant spacings next to block elements and collapses spaces."""
    result: list[str] = []
    i = 0
    n = len(parts)
    while i < n:
        text, kind = parts[i]
        # Check if this starts a spacing sequence
        if kind == "br" or (kind == "normal" and not text.strip().replace("&nbsp;", "")):
            j = i
            br_count = 0
            while j < n:
                t2, k2 = parts[j]
                if k2 == "br":
                    br_count += 1
                    j += 1
                elif k2 == "normal" and not t2.strip().replace("&nbsp;", ""):
                    j += 1
                else:
                    break

            # Determine if adjacent to a block element
            touches_block = False
            if i > 0 and parts[i - 1][1] in BLOCK_KINDS:
                touches_block = True
            if j < n and parts[j][1] in BLOCK_KINDS:
                touches_block = True

            if touches_block:
                # Subtract 2 <br>s since paragraph breaks are implicit due to block margins.
                new_br_count = max(0, br_count - 2)
            else:
                new_br_count = br_count

            for _ in range(new_br_count):
                result.append("<br>")
            i = j
        else:
            result.append(text)
            i += 1
    return result


def _upgrade_existing_tables(html: str) -> str:
    """Upgrades old unstyled <table> elements to the new styled layout."""
    if "table" not in html.lower():
        return html

    # 1. Bare <table> -> <table style="border-collapse: collapse;">
    html = re.sub(
        r"<table>",
        r'<table style="border-collapse: collapse;">',
        html,
        flags=re.IGNORECASE,
    )

    # 2. Upgrade <th> with alignment parsing
    def upgrade_th(m):
        attrs = m.group(1) or ""
        if "border:" in attrs and "padding:" in attrs:
            return m.group(0)
        align_css = ""
        m_align = re.search(r"text-align:\s*(\w+);?", attrs)
        if m_align:
            align_css = f"text-align: {m_align.group(1)};"

        style = f'style="border: 1px solid #ccc; padding: 6px 10px; background-color: rgba(150, 150, 150, 0.1); font-weight: bold; {align_css}"'
        return f"<th {style}>"

    html = re.sub(r"<th\b([^>]*)>", upgrade_th, html, flags=re.IGNORECASE)

    # 3. Upgrade <td> with alignment parsing
    def upgrade_td(m):
        attrs = m.group(1) or ""
        if "border:" in attrs and "padding:" in attrs:
            return m.group(0)
        align_css = ""
        m_align = re.search(r"text-align:\s*(\w+);?", attrs)
        if m_align:
            align_css = f"text-align: {m_align.group(1)};"

        style = f'style="border: 1px solid #ccc; padding: 6px 10px; {align_css}"'
        return f"<td {style}>"

    html = re.sub(r"<td\b([^>]*)>", upgrade_td, html, flags=re.IGNORECASE)

    return html


def _upgrade_existing_code_blocks(html: str) -> str:
    """Upgrades old unstyled <pre> elements to the new dark-styled layout."""
    if "<pre" not in html.lower():
        return html

    def upgrade_pre(m):
        attrs = m.group(1) or ""
        if "background:" in attrs or "background-color:" in attrs:
            return m.group(0)

        style = (
            'style="background-color: #1e1e1e; color: #d4d4d4; padding: 12px 16px; '
            'border-radius: 6px; overflow-x: auto; font-family: SFMono-Regular, Consolas, '
            'Liberation Mono, Menlo, monospace; font-size: 0.85em; line-height: 1.5; margin: 10px 0;"'
        )
        other_attrs = attrs.strip()
        if other_attrs:
            return f"<pre {style} {other_attrs}>"
        return f"<pre {style}>"

    html = re.sub(r"<pre\b([^>]*)>", upgrade_pre, html, flags=re.IGNORECASE)
    return html


def _upgrade_existing_blockquotes(html: str) -> str:
    """Upgrades old unstyled <blockquote> elements to the new styled layout."""
    if "<blockquote" not in html.lower():
        return html

    def upgrade_blockquote(m):
        attrs = m.group(1) or ""
        if "border-left:" in attrs:
            return m.group(0)

        style = (
            'style="border-left: 4px solid #ccc; padding: 6px 12px; margin: 10px 0; '
            'background-color: rgba(150, 150, 150, 0.08);"'
        )
        other_attrs = attrs.strip()
        if other_attrs:
            return f"<blockquote {style} {other_attrs}>"
        return f"<blockquote {style}>"

    html = re.sub(r"<blockquote\b([^>]*)>", upgrade_blockquote, html, flags=re.IGNORECASE)
    return html


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
    split_parts = _BR_SPLIT_RE.split(html)
    parts_tuples = []
    for part in split_parts:
        if _BR_SPLIT_RE.match(part):
            parts_tuples.append((part, True))
        else:
            parts_tuples.append((part, False))

    # Parse code blocks
    parts = _parse_code_blocks(parts_tuples)

    # Split off table rows glued onto preceding HTML with no <br>.
    parts = _split_leading_block_boundary_row(parts)

    # Parse tables
    parts = _parse_tables(parts)

    # Parse individual lines
    converted_parts: list[tuple[str, str]] = []
    for content, kind in parts:
        if kind == "text":
            converted_parts.append(_convert_line(content))
        else:
            converted_parts.append((content, kind))

    # Group consecutive list items and blockquote lines.
    grouped = _assemble(converted_parts)

    # Clean up redundant spacings (e.g. <br> after block elements).
    output = _clean_spacings(grouped)
    result = "".join(output)

    # Upgrade any old unstyled HTML tables.
    result = _upgrade_existing_tables(result)

    # Upgrade any old unstyled HTML code blocks.
    result = _upgrade_existing_code_blocks(result)

    # Upgrade any old unstyled HTML blockquotes.
    result = _upgrade_existing_blockquotes(result)

    # Byte-identical guarantee.
    if result == html:
        return html
    return result


def _assemble(parts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Assemble converted parts, wrapping consecutive list/blockquote items.

    Consecutive 'ul' items → <ul>…</ul>, 'ol' → <ol>…</ol>,
    'bq' → <blockquote>…</blockquote>.
    <br> delimiters between same-type items are absorbed into the group;
    <br> delimiters at group boundaries are kept.
    """
    output: list[tuple[str, str]] = []
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
            output.append((f"<{wrapper}>{''.join(items)}</{wrapper}>", tag))
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
            style = (
                'style="border-left: 4px solid #ccc; padding: 6px 12px; margin: 10px 0; '
                'background-color: rgba(150, 150, 150, 0.08);"'
            )
            output.append((f"<blockquote {style}>{''.join(lines)}</blockquote>", "bq"))
            i = j

        else:
            output.append((text, kind))
            i += 1

    return output
