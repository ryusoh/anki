import re

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
            # Negated normal terms like -apple
            # Should these also be restricted to Front? If the original query is `apple -banana`,
            # it means "apple but not banana". If Tier 1 is "Front:*apple* -Front:*banana*",
            # wait, if the original query had -banana, it strictly filters out ANY card with banana.
            # If we change -banana to -Front:*banana*, it would INCLUDE cards that have banana in the Back field!
            # That's wrong. If a term is negated, we must NOT constrain it to Front,
            # because we want to preserve the global negation.
            # So negated terms should just be passed through as special terms.
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
