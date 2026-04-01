"""
References module for Anki knowledge graph.

Finds cross-references between notes within the same deck.
"""

from graph.parser import extract_fields, tokenize, get_front_field, get_other_fields_text


# Edge weight configuration
EDGE_WEIGHTS = {
    'front_reference': {
        'front': 3.0,      # Front field references another Front (component relationship)
        'back': 2.0,       # Front field references in Back field
    },
    'field_reference': {
        'front': 1.5,      # Other field references Front
        'back': 1.0,       # Other field references in Back (content reference)
    },
}


def find_references(notes):
    """
    Find all cross-references between notes within the same deck.

    Cross-deck references are NOT created. Only references within
    the same deck are considered valid.

    Args:
        notes: List of note dicts with guid, deck, flds fields

    Returns:
        List of edge dicts: {source, target, type, word, weight, deck}
    """
    if not notes:
        return []

    # Group notes by deck first
    from graph.parser import group_by_deck
    grouped = group_by_deck(notes)

    all_edges = []

    # Find references within each deck
    for deck, deck_notes in grouped.items():
        deck_edges = find_references_for_deck_only(deck_notes, deck)
        all_edges.extend(deck_edges)

    return all_edges


def find_references_for_deck(notes, deck_name):
    """
    Find references for notes in a specific deck.

    Args:
        notes: List of all notes
        deck_name: Deck name to filter by

    Returns:
        List of edge dicts for notes in the specified deck
    """
    deck_notes = [n for n in notes if n.get('deck') == deck_name]
    return find_references_for_deck_only(deck_notes, deck_name)


def find_references_for_deck_only(deck_notes, deck_name):
    """
    Find references within a single deck.

    Args:
        deck_notes: List of notes from one deck
        deck_name: Name of the deck

    Returns:
        List of edge dicts
    """
    if len(deck_notes) < 2:
        return []

    # Build index: word -> list of note guids that have this word in Front field
    front_word_index = {}

    for note in deck_notes:
        front = get_front_field(note)
        tokens = tokenize(front)

        for token in tokens:
            if token not in front_word_index:
                front_word_index[token] = []
            front_word_index[token].append(note['guid'])

    # Find references
    edges = []
    seen_edges = set()  # Prevent duplicate edges

    for note in deck_notes:
        # Get all fields except front
        other_text = get_other_fields_text(note)
        other_tokens = set(tokenize(other_text))

        # Also tokenize front field (for front-to-front references)
        front = get_front_field(note)
        front_tokens = set(tokenize(front))

        # Check if any token matches another note's Front field
        all_tokens = other_tokens | front_tokens

        for token in all_tokens:
            if token in front_word_index:
                for source_guid in front_word_index[token]:
                    # Skip self-references
                    if source_guid == note['guid']:
                        continue

                    # Determine edge type and location
                    if token in front_tokens and token in other_tokens:
                        # Token appears in both front and other fields
                        edge_type = 'front_reference'
                        location = 'front'
                    elif token in front_tokens:
                        # Token only in front field
                        edge_type = 'front_reference'
                        location = 'front'
                    else:
                        # Token only in other fields
                        edge_type = 'field_reference'
                        location = 'back'

                    # Create unique edge key
                    edge_key = (source_guid, note['guid'], token)

                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)

                        weight = EDGE_WEIGHTS.get(edge_type, {}).get(location, 1.0)

                        edges.append({
                            'source': source_guid,
                            'target': note['guid'],
                            'type': edge_type,
                            'word': token,
                            'weight': weight,
                            'deck': deck_name,
                            'location': location,
                        })

    return edges


def calculate_edge_weight(edge_type, location):
    """
    Calculate edge weight based on type and location.

    Args:
        edge_type: 'front_reference' or 'field_reference'
        location: 'front' or 'back'

    Returns:
        float: Edge weight
    """
    return EDGE_WEIGHTS.get(edge_type, {}).get(location, 1.0)
