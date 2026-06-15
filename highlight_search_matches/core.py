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


def highlight_text(text: str, terms: list[str]) -> str:
    """
    Wraps matched terms in the text with a highlight span.
    Avoids matching inside HTML tags (e.g., avoiding altering <span class="match">).
    """
    if not terms or not text:
        return text

    # Escape terms to be safe in regex
    escaped_terms = [re.escape(term) for term in terms]

    # Create an OR regex pattern
    terms_pattern = "|".join(escaped_terms)

    # We want to match text only OUTSIDE of HTML tags.
    # A standard trick is to match tags OR our pattern, and only replace if it's our pattern.
    # (<[^>]+>) matches HTML tags
    pattern = re.compile(f"(<[^>]+>)|({terms_pattern})", re.IGNORECASE)

    def repl(match):
        # If it matched an HTML tag (Group 1), return it unchanged
        if match.group(1):
            return match.group(1)
        # Otherwise, it matched our term (Group 2), wrap it
        matched_text = match.group(2)
        return f'<span class="search-highlight">{matched_text}</span>'

    return pattern.sub(repl, text)
