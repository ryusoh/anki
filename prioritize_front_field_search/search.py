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

def extract_terms(query: str) -> list[str]:
    """
    Extracts the search terms from a query string that we should use for ranking.
    Includes normal terms and terms from Front: field searches.
    """
    if not query:
        return []

    terms = []
    # Split query string keeping quoted strings as single units
    for match in re.finditer(r'(?:[^\s"]|"(?:\\.|[^"])*")+', query):
        part = match.group(0)
        if part.upper() == "OR":
            continue
        
        # Check for field-specific search
        field_match = re.match(r'^([^:]+):(.*)$', part)
        if field_match:
            field, value = field_match.groups()
            # If it's a Front field search, we want the term
            if field.lower() == "front" or field.lower() == "-front":
                term = value
                # Remove quotes and wildcards
                if term.startswith('"') and term.endswith('"'):
                    term = term[1:-1]
                term = term.replace('*', '')
                if term:
                    terms.append(term)
            continue
            
        if part.startswith('-') and not part == '-':
            # Negated term, usually not used for ranking but could be
            continue

        # Normal search term
        if part.startswith('"') and part.endswith('"') and len(part) >= 2:
            terms.append(part[1:-1])
        else:
            # Remove wildcards for scoring
            terms.append(part.replace('*', ''))

    return [t for t in terms if t]

def build_tier1_query(query: str) -> str:
    """
    Given a raw Anki query string, transforms it into a Tier 1 query
    where normal terms are enforced to match the Front field.
    Special directives (deck:, is:, OR, -, etc) are left intact.
    """
    if not query:
        return ""

    parts = []
    # Split query string keeping quoted strings as single units
    for match in re.finditer(r'(?:[^\s"]|"(?:\\.|[^"])*")+', query):
        parts.append(match.group(0))

    tier_1_parts = []
    has_normal_terms = False

    for part in parts:
        if part.upper() == "OR":
            tier_1_parts.append(part)
        elif re.match(r'^-?[a-zA-Z0-9_]+:', part):
            # Special field-like prefixes (deck:, is:, tag:, note:, Front:)
            tier_1_parts.append(part)
        elif part.startswith('-') and not part == '-':
            # Negated normal terms
            tier_1_parts.append(part)
        else:
            has_normal_terms = True
            # Normal search term
            if part.startswith('"') and part.endswith('"') and len(part) >= 2:
                inner = part[1:-1]
                tier_1_parts.append(f'"Front:*{inner}*"')
            else:
                if '*' in part:
                    tier_1_parts.append(f'Front:{part}')
                else:
                    tier_1_parts.append(f'Front:*{part}*')

    # If there are no normal terms, we don't need to tier it, return empty.
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
