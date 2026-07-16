import html
import re


def extract_search_terms(query: str) -> list[str]:
    """
    Extracts plain text terms from Anki's search query.
    Ignores terms with colons (e.g., deck:Default), negative terms (-word).
    Strips quotes.
    """
    if not query:
        return []

    terms = []
    query = query.replace('"', ' ').replace("'", ' ')

    words = query.split()
    for word in words:
        if ':' in word or word.startswith('-'):
            continue

        word = word.strip('()')
        if word:
            terms.append(word)

    return terms


# Named / decimal / hex character entities: a term match must never fire
# inside one (searching "BSP" must not hit "&nbsp;"). Shared with the
# injected editor JS, so keep it valid in both Python and JS regex syntax.
ENTITY_PATTERN = r"&[a-zA-Z][a-zA-Z0-9]*;|&#[0-9]+;|&#[xX][0-9a-fA-F]+;"

# HTML constructs a term match must never fire inside: tags and entities.
_SKIP_HTML_PATTERN = rf"<[^>]+>|{ENTITY_PATTERN}"


def highlight_text(text: str, terms: list[str]) -> str:
    """
    Wraps matched terms in the text with a highlight span.
    Avoids matching inside HTML tags (e.g., avoiding altering <span class="match">)
    and inside HTML entities (e.g., "BSP" must not match "&nbsp;").
    """
    if not terms or not text:
        return text

    # Escape terms to be safe in regex
    escaped_terms = [re.escape(term) for term in terms]

    # Create an OR regex pattern
    terms_pattern = "|".join(escaped_terms)

    # We want to match text only OUTSIDE of HTML tags and entities.
    # A standard trick is to match those OR our pattern, and only replace
    # if it's our pattern.
    pattern = re.compile(f"({_SKIP_HTML_PATTERN})|({terms_pattern})", re.IGNORECASE)

    def repl(match):
        # If it matched an HTML tag (Group 1), return it unchanged
        if match.group(1):
            return match.group(1)
        # Otherwise, it matched our term (Group 2), wrap it
        matched_text = match.group(2)
        return f'<span class="search-highlight">{matched_text}</span>'

    return pattern.sub(repl, text)


_TAG_RE = re.compile(r"<[^>]+>")
# Like Anki's strip_html_preserving_media_filenames: an <img> tag's filename
# stays searchable even though the tag itself is stripped.
_IMG_SRC_RE = re.compile(r"<img[^>]+src=[\"']?([^\"'> ]+)[\"']?[^>]*>", re.IGNORECASE)


def note_has_real_match(field_texts: list[str], terms: list[str]) -> bool:
    """
    True if any term appears in the *visible* text of any field.

    Anki's search runs over field text with tags stripped but entities kept,
    so searching "BSP" false-positives on "&nbsp;". Here we strip tags AND
    decode entities before matching, so entity-only hits count as no match.
    Media filenames are kept, matching Anki (searching "bsp" finds
    <img src="bsp.jpg">). Conservative by design: a note is only "unmatched"
    when none of the terms appear anywhere visibly.
    """
    lowered_terms = [term.lower() for term in terms]
    for field_text in field_texts:
        stripped = _IMG_SRC_RE.sub(r" \1 ", field_text)
        visible = html.unescape(_TAG_RE.sub("", stripped)).lower()
        if any(term in visible for term in lowered_terms):
            return True
    return False
