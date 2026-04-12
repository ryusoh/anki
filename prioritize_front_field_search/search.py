import re

def strip_html(text: str) -> str:
    """Very basic HTML stripping for scoring purposes."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Basic entity replacement
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return text

def score_front_match(text: str, term: str) -> int:
    """
    Calculates a ranking score for how well a search term matches the Front field text.
    4: Exact match (case-insensitive)
    3: Word match
    2: Substring match (single word)
    1: Substring match (multiple words)
    0: No match
    """
    text = strip_html(text).lower().strip()
    term = term.lower().strip()

    if not term:
        return 0

    if text == term:
        return 4

    # Word match
    # Use re.escape for term to handle special characters
    if re.search(r'\b' + re.escape(term) + r'\b', text):
        return 3

    # Substring match
    if term in text:
        # Check if text is a single word
        if len(text.split()) <= 1:
            return 2
        return 1

    return 0

def _extract_term_from_field(field: str, value: str) -> str:
    """Helper to extract search terms from a specific field match."""
    if field.lower() not in ("front", "-front"):
        return ""

    term = value
    if term.startswith('"') and term.endswith('"'):
        term = term[1:-1]
    term = term.replace('*', '')
    return term

def _process_query_part(part: str) -> str:
    """Helper to process a non-field query part."""
    if part.upper() == "OR" or (part.startswith('-') and not part == '-'):
        return ""

    if part.startswith('"') and part.endswith('"') and len(part) >= 2:
        return part[1:-1]
    return part.replace('*', '')

def extract_terms(query: str) -> list[str]:
    """
    Extracts the search terms from a query string that we should use for ranking.
    Includes normal terms and terms from Front: field searches.
    """
    if not query:
        return []

    terms = []
    for match in re.finditer(r'[a-zA-Z0-9_-]+:"(?:[^"\\]|\\.)*"|[^"\s]+|"(?:[^"\\]|\\.)*"', query):
        part = match.group(0)
        field_match = re.match(r'^([^:]+):(.*)$', part)

        if field_match:
            term = _extract_term_from_field(*field_match.groups())
            if term:
                terms.append(term)
        else:
            term = _process_query_part(part)
            if term:
                terms.append(term)

    return terms


def _transform_tier1_part(part: str) -> tuple[str, bool]:
    """Helper to transform a single query part for Tier 1."""
    if part.upper() == "OR" or re.match(r'^-?[a-zA-Z0-9_]+:', part) or (part.startswith('-') and not part == '-'):
        return part, False

    if part.startswith('"') and part.endswith('"') and len(part) >= 2:
        return f'"Front:*{part[1:-1]}*"', True

    if '*' in part:
        return f'Front:{part}', True

    return f'Front:*{part}*', True

def build_tier1_query(query: str) -> str:
    """
    Given a raw Anki query string, transforms it into a Tier 1 query
    where normal terms are enforced to match the Front field.
    Special directives (deck:, is:, OR, -, etc) are left intact.
    """
    if not query:
        return ""

    tier_1_parts = []
    has_normal_terms = False

    for match in re.finditer(r'[a-zA-Z0-9_-]+:"(?:[^"\\]|\\.)*"|[^"\s]+|"(?:[^"\\]|\\.)*"', query):
        transformed, is_normal = _transform_tier1_part(match.group(0))
        tier_1_parts.append(transformed)
        has_normal_terms = has_normal_terms or is_normal

    if not has_normal_terms:
        return ""

    return " ".join(tier_1_parts).strip()

def sort_tier1_by_score(ids: list[int], note_data: dict[int, str], terms: list[str]) -> list[int]:
    """
    Sorts a list of IDs by their match score in the Front field.
    Preserves original order for items with equal scores (stable sort).
    """
    if not terms or not ids:
        return ids

    score_map = {}
    for item_id in ids:
        front_text = note_data.get(item_id, "")
        # Calculate total score across all terms
        score = sum(score_front_match(front_text, term) for term in terms)
        score_map[item_id] = score

    # Sort descending by score. Python's sort is stable.
    return sorted(ids, key=lambda x: score_map[x], reverse=True)
