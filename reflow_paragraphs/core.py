"""Reflow hard-wrapped PDF text into normal paragraphs.

Text pasted from a PDF arrives wrapped at the PDF's column width: one visual
paragraph becomes many short lines broken mid-sentence. Everything else in a
field must survive untouched — dictionary-style word lists, and especially
rich structured HTML (Wiktionary definitions nest `<ul><li><dl><dd><div>`).

Ground rules, learned from real fields (see tests/fixtures/):

- Only `<br>` is a line break. `<div>` and friends are STRUCTURE, never line
  separators, and literal newline characters are insignificant whitespace.
- Heuristics run on a line's VISIBLE text (tags stripped); joining preserves
  the raw HTML, so inline markup like `<i>…</i>` per line survives.
- A line containing block-level tags, or showing no text (an `<img>`), or
  holding only `[sound:…]` refs, is structural: a hard boundary, kept verbatim.
- If nothing reflowed, the field is returned byte-identical.

The prose discriminator is segment-shaped: multi-word lines whose visible
text on average fills the column width, with at least one break landing
mid-sentence. Word lists fail by a wide margin (single words are short);
already-normal paragraphs fail because every break ends a sentence.
"""

from __future__ import annotations

import re

# Mean visible length a segment's body must reach to count as column-filling
# wrapped prose. Book columns wrap around 50-70 chars; word lists sit far below.
MIN_FILL_LEN = 40

_BR_SPLIT_RE = re.compile(r"\s*<br\s*/?>\s*", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_TAG_RE = re.compile(
    r"</?(?:div|p|ul|ol|li|dl|dt|dd|table|thead|tbody|tr|td|th|blockquote|h[1-6]|pre|hr)\b",
    re.IGNORECASE,
)
_SOUND_ONLY_RE = re.compile(r"^(?:\[sound:[^\]]+\]\s*)+$")
_STRONG_TERMINAL_RE = re.compile(r'[.!?]["”\'’)]?$')

# An attribute-less <div> whose content holds no block break (no div, no br):
# a "leaf div", the shape Anki gives each pasted line in div-per-line fields.
# Structured divs (attributes, nesting) never match.
_LEAF_DIV_RE = re.compile(r"<div>((?:(?!</?div\b|<br)[\s\S])*?)</div>", re.IGNORECASE)

# A visible line ending in one of these may be a deliberate line end (sentence,
# header like "Similar:", closing quote); one not ending in these broke
# mid-sentence and can only be a wrap artifact.
_TERMINAL_CHARS = '.!?:;"”…'


def _visible(line: str) -> str:
    """The text a line renders: tags stripped, nbsp as space, trimmed."""
    return _TAG_RE.sub("", line).replace("&nbsp;", " ").strip()


def _is_structural(line: str) -> bool:
    """A line that is markup structure or a list/glossary label rather than
    prose: never reflowed, and a hard boundary between prose segments."""
    if _BLOCK_TAG_RE.search(line):
        return True
    visible = _visible(line)
    if not visible or _SOUND_ONLY_RE.match(visible):
        return True
    # Header lines ("Similar:", "同義語:") and CJK glossary markers ("【记】…")
    # label the lines around them; joining them into prose mangles the entry.
    # Note: A colon-ended line is only structural if it's not column-filling.
    return (visible.endswith((":", "：")) and len(visible) < MIN_FILL_LEN) or visible.startswith(
        ("【", "[")
    )


def _open_junction(line: str, next_line: str) -> bool:
    """A line break that can only be a wrap artifact: the line stops without
    finishing a sentence. A short line (a lone paragraph-opening word) only
    counts when the next line continues in lowercase — a short heading
    followed by a new sentence ("foible (n.)" / "1640s, …") is deliberate.
    """
    visible = _visible(line)
    if len(visible) >= MIN_FILL_LEN:
        if _STRONG_TERMINAL_RE.search(visible):
            return False
        return True
    if visible.endswith(tuple(_TERMINAL_CHARS)):
        return False
    return _visible(next_line)[:1].islower()


def _is_wrapped_prose(lines: list[str]) -> bool:
    """A segment of hard-wrapped prose: visible lines that on average fill
    the column, and MOST breaks land mid-sentence.

    The mean (not a per-line cliff) tolerates the odd wrapped line that runs
    short; word/phrase lists still fail it by a wide margin. The strict
    majority of open junctions separates wrapped prose (nearly every break is
    mid-sentence) from glossary blocks, where most lines end deliberately.
    """
    if len(lines) < 2:
        return False
    body = [_visible(line) for line in lines[:-1]]
    if sum(len(line) for line in body) / len(body) < MIN_FILL_LEN:
        return False
    junctions = [_open_junction(a, b) for a, b in zip(lines[:-1], lines[1:])]
    return sum(junctions) * 2 >= len(junctions)


def _ends_wrapped_paragraph(line: str) -> bool:
    """The last line of a wrapped paragraph: its visible text runs short of
    the column AND finishes a sentence. A short line broken mid-sentence is a
    wrap artifact; a list item ("release") is short but ends no sentence.
    """
    visible = _visible(line)
    return len(visible) < MIN_FILL_LEN and visible.endswith(tuple(_TERMINAL_CHARS))


def _segments(block: list[str]) -> list[list[str]]:
    """Split a run of prose lines at wrapped-paragraph boundaries.

    PDFs often separate paragraphs only by indentation, which paste discards,
    so two wrapped paragraphs can arrive as one adjacent run of lines.
    """
    segments: list[list[str]] = []
    current: list[str] = []
    for line in block:
        current.append(line)
        if _ends_wrapped_paragraph(line):
            segments.append(current)
            current = []
    if current:
        segments.append(current)
    return segments


def _join_segment(lines: list[str]) -> str:
    joined = ""
    for line in lines:
        stripped = line.strip()
        if not joined:
            joined = stripped
        elif joined.endswith("-") and stripped[:1].islower():
            # PDF end-of-line hyphenation: "ex-" + "hausted" → "exhausted".
            joined = joined[:-1] + stripped
        else:
            joined += " " + stripped
    return joined


def _reflow_lines(lines: list[str]) -> tuple[list[str], bool]:
    """Reflow wrapped-prose runs in `lines`; structural lines pass verbatim.

    Returns the output lines and whether any join actually happened.
    """
    out: list[str] = []
    changed = False
    block: list[str] = []

    def flush() -> None:
        nonlocal changed
        for segment in _segments(block):
            if _is_wrapped_prose(segment):
                out.append(_join_segment(segment))
                changed = True
            else:
                out.extend(segment)
        block.clear()

    for line in lines:
        if _is_structural(line):
            flush()
            out.append(line)
        else:
            block.append(line)
    flush()
    return out, changed


def reflow_text(text: str) -> str:
    """Reflow hard-wrapped prose in plain text; blank lines stay paragraph
    separators and non-prose lines pass through unchanged."""
    out, _ = _reflow_lines(text.split("\n"))
    return "\n".join(out)


def _reflow_leaf_div_runs(html: str) -> tuple[str, bool]:
    """Reflow runs of adjacent leaf divs — the div-per-line paste format.

    A run is ≥2 leaf divs separated only by whitespace. Its inner lines go
    through the same prose classification; a run where nothing joins keeps
    its original bytes, so nested dictionary div-soup is never rewritten.
    """
    matches = list(_LEAF_DIV_RE.finditer(html))
    pieces: list[str] = []
    changed = False
    pos = 0
    i = 0
    while i < len(matches):
        j = i
        while j + 1 < len(matches) and not html[matches[j].end() : matches[j + 1].start()].strip():
            j += 1
        run = matches[i : j + 1]
        if len(run) >= 2:
            out, run_changed = _reflow_lines([m.group(1) for m in run])
            if run_changed:
                pieces.append(html[pos : run[0].start()])
                pieces.append("".join(f"<div>{line}</div>" for line in out))
                pos = run[-1].end()
                changed = True
        i = j + 1
    pieces.append(html[pos:])
    return "".join(pieces), changed


def reflow_field_html(html: str) -> str:
    """Reflow an Anki field's HTML.

    Two real paste formats (see tests): lines separated by `<br>` variants,
    and one leaf `<div>` per line. Literal whitespace around a `<br>` (Anki
    stores "line<br>\\n") belongs to the break. If no prose segment was
    joined, the original field is returned byte-identical so untouched
    fields are never rewritten.
    """
    html_divs, changed_divs = _reflow_leaf_div_runs(html)
    lines = _BR_SPLIT_RE.split(html_divs)
    out, changed_brs = _reflow_lines(lines)
    if changed_brs:
        return "<br>".join(out)
    if changed_divs:
        return html_divs
    return html
