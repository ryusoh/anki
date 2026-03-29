"""
References module for Anki knowledge graph.

Finds cross-references between notes within the same deck.
Uses whole-front-field matching: an edge is created only when
one card's entire front field appears in another card's content.
"""

import re
from graph.parser import extract_fields, get_front_field, get_other_fields_text


# Edge weight configuration
EDGE_WEIGHTS = {
    'front_in_front': 3.0,   # Card A's front appears inside card B's front
    'front_in_back': 2.0,    # Card A's front appears inside card B's back/other fields
}

# Minimum front field length to consider for matching
MIN_FRONT_LENGTH = 2


def _normalize(text):
    """Normalize text for matching: strip HTML, lowercase, collapse whitespace."""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&\w+;', ' ', text)
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def find_references(notes):
    """
    Find all cross-references between notes within the same deck.

    A reference exists when card A's entire front field appears as a
    substring in card B's content. This produces far fewer, more
    meaningful edges than per-token matching.

    Args:
        notes: List of note dicts with guid, deck, flds fields

    Returns:
        List of edge dicts: {source, target, type, weight, deck}
    """
    if not notes:
        return []

    from graph.parser import group_by_deck
    grouped = group_by_deck(notes)

    all_edges = []
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
    Find references within a single deck using whole-front-field matching.

    For each pair of cards, checks if card A's entire front field text
    appears as a substring inside card B's front or back fields.

    Args:
        deck_notes: List of notes from one deck
        deck_name: Name of the deck

    Returns:
        List of edge dicts
    """
    if len(deck_notes) < 2:
        return []

    # Pre-compute normalized fields for each note
    note_fields = []
    for note in deck_notes:
        front_raw = get_front_field(note)
        other_raw = get_other_fields_text(note)
        front_norm = _normalize(front_raw)
        other_norm = _normalize(other_raw)
        note_fields.append({
            'guid': note['guid'],
            'front': front_norm,
            'other': other_norm,
            'all_text': front_norm + ' ' + other_norm,
        })

    edges = []
    seen_edges = set()

    for src in note_fields:
        src_front = src['front']
        if len(src_front) < MIN_FRONT_LENGTH:
            continue

        for tgt in note_fields:
            if src['guid'] == tgt['guid']:
                continue

            edge_key = (src['guid'], tgt['guid'])
            if edge_key in seen_edges:
                continue

            # Check if src's front field appears in tgt's fields
            if src_front in tgt['front']:
                seen_edges.add(edge_key)
                edges.append({
                    'source': src['guid'],
                    'target': tgt['guid'],
                    'type': 'front_in_front',
                    'weight': EDGE_WEIGHTS['front_in_front'],
                    'deck': deck_name,
                })
            elif src_front in tgt['other']:
                seen_edges.add(edge_key)
                edges.append({
                    'source': src['guid'],
                    'target': tgt['guid'],
                    'type': 'front_in_back',
                    'weight': EDGE_WEIGHTS['front_in_back'],
                    'deck': deck_name,
                })

    return edges


def calculate_edge_weight(edge_type):
    """
    Calculate edge weight based on type.

    Args:
        edge_type: 'front_in_front' or 'front_in_back'

    Returns:
        float: Edge weight
    """
    return EDGE_WEIGHTS.get(edge_type, 1.0)
