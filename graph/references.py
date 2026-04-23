"""
References module for Anki knowledge graph.

Finds cross-references between notes within the same deck.
Uses whole-front-field matching: an edge is created only when
one card's entire front field appears in another card's content.

Optimizations:
- Aho-Corasick automaton for O(n + m) multi-pattern substring matching
  instead of O(n²) pairwise comparison
- Multiprocessing to split large decks into parallel chunks
"""

import re
import multiprocessing
from graph.parser import extract_fields, get_front_field, get_other_fields_text

def _get_pool(workers):
    """Create a Pool using fork context (safe on macOS with spawn default)."""
    ctx = multiprocessing.get_context("fork")
    return ctx.Pool(workers)

try:
    import ahocorasick
    HAS_AHO = True
except ImportError:
    HAS_AHO = False

# Edge weight configuration
EDGE_WEIGHTS = {
    'front_in_front': 3.0,   # Card A's front appears inside card B's front
    'front_in_back': 2.0,    # Card A's front appears inside card B's back/other fields
}

# Minimum front field length to consider for matching
MIN_FRONT_LENGTH = 2

# Decks larger than this get parallelized internally
_LARGE_DECK_THRESHOLD = 2000


def _normalize(text):
    """Normalize text for matching: strip HTML, lowercase, collapse whitespace."""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&\w+;', ' ', text)
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def _prepare_note_fields(notes):
    """Pre-compute normalized fields for a list of notes."""
    result = []
    for note in notes:
        front_norm = _normalize(get_front_field(note))
        other_norm = _normalize(get_other_fields_text(note))
        result.append({
            'guid': note['guid'],
            'front': front_norm,
            'front_len': len(front_norm),
            'other': other_norm,
        })
    return result


def find_references(notes, progress_callback=None):
    """
    Find all cross-references between notes within the same deck.

    Args:
        notes: List of note dicts with guid, deck, flds fields
        progress_callback: Optional callable(deck_name, deck_index, total_decks, deck_size)

    Returns:
        List of edge dicts: {source, target, type, weight, deck}
    """
    if not notes:
        return []

    from graph.parser import group_by_deck
    grouped = group_by_deck(notes)
    total_decks = len(grouped)

    all_edges = []
    for i, (deck, deck_notes) in enumerate(grouped.items()):
        if progress_callback:
            progress_callback(deck, i, total_decks, len(deck_notes))
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

    For large decks, parallelizes by splitting target notes into chunks
    and scanning each chunk against the full Aho-Corasick automaton.

    Args:
        deck_notes: List of notes from one deck
        deck_name: Name of the deck

    Returns:
        List of edge dicts
    """
    if len(deck_notes) < 2:
        return []

    note_fields = _prepare_note_fields(deck_notes)

    if HAS_AHO and len(note_fields) > 50:
        if len(note_fields) > _LARGE_DECK_THRESHOLD:
            return _find_refs_aho_parallel(note_fields, deck_name)
        return _find_refs_aho(note_fields, deck_name)
    return _find_refs_bruteforce(note_fields, deck_name)


def _build_automaton(note_fields):
    """Build Aho-Corasick automaton and guid lookup from note fields."""
    automaton = ahocorasick.Automaton()
    guid_by_front = {}

    for nf in note_fields:
        if nf['front_len'] < MIN_FRONT_LENGTH:
            continue
        front = nf['front']
        if front not in guid_by_front:
            guid_by_front[front] = []
            automaton.add_word(front, front)
        guid_by_front[front].append(nf['guid'])

    if guid_by_front:
        automaton.make_automaton()

    return automaton, guid_by_front


def _scan_chunk(args):
    """Scan a chunk of target notes against a pre-built automaton. For multiprocessing."""
    chunk, all_note_fields, deck_name = args

    automaton, guid_by_front = _build_automaton(all_note_fields)
    if not guid_by_front:
        return []

    edges = []
    seen_edges = set()

    for tgt in chunk:
        tgt_guid = tgt['guid']

        for end_idx, matched_front in automaton.iter(tgt['front']):
            for src_guid in guid_by_front[matched_front]:
                if src_guid == tgt_guid:
                    continue
                edge_key = (src_guid, tgt_guid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        'source': src_guid,
                        'target': tgt_guid,
                        'type': 'front_in_front',
                        'weight': EDGE_WEIGHTS['front_in_front'],
                        'deck': deck_name,
                    })

        matched_in_front = {ek[0] for ek in seen_edges if ek[1] == tgt_guid}
        for end_idx, matched_front in automaton.iter(tgt['other']):
            for src_guid in guid_by_front[matched_front]:
                if src_guid == tgt_guid or src_guid in matched_in_front:
                    continue
                edge_key = (src_guid, tgt_guid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        'source': src_guid,
                        'target': tgt_guid,
                        'type': 'front_in_back',
                        'weight': EDGE_WEIGHTS['front_in_back'],
                        'deck': deck_name,
                    })

    return edges


def _find_refs_aho_parallel(note_fields, deck_name):
    """
    Parallel Aho-Corasick: each worker builds its own automaton from ALL
    source fronts, but only scans a chunk of target notes.
    """
    workers = min(multiprocessing.cpu_count(), 8)
    chunk_size = max(1, len(note_fields) // workers)
    chunks = []
    for i in range(0, len(note_fields), chunk_size):
        chunks.append((note_fields[i:i + chunk_size], note_fields, deck_name))

    with _get_pool(workers) as pool:
        results = pool.map(_scan_chunk, chunks)

    # Merge and deduplicate edges across chunks
    seen = set()
    edges = []
    for chunk_edges in results:
        for e in chunk_edges:
            key = (e['source'], e['target'])
            if key not in seen:
                seen.add(key)
                edges.append(e)

    return edges


def _find_refs_aho(note_fields, deck_name):
    """
    Single-threaded Aho-Corasick: build automaton from all front fields,
    then scan each note's text once.
    """
    automaton, guid_by_front = _build_automaton(note_fields)
    if not guid_by_front:
        return []

    edges = []
    seen_edges = set()

    for tgt in note_fields:
        tgt_guid = tgt['guid']

        for end_idx, matched_front in automaton.iter(tgt['front']):
            for src_guid in guid_by_front[matched_front]:
                if src_guid == tgt_guid:
                    continue
                edge_key = (src_guid, tgt_guid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        'source': src_guid,
                        'target': tgt_guid,
                        'type': 'front_in_front',
                        'weight': EDGE_WEIGHTS['front_in_front'],
                        'deck': deck_name,
                    })

        matched_in_front = {ek[0] for ek in seen_edges if ek[1] == tgt_guid}
        for end_idx, matched_front in automaton.iter(tgt['other']):
            for src_guid in guid_by_front[matched_front]:
                if src_guid == tgt_guid or src_guid in matched_in_front:
                    continue
                edge_key = (src_guid, tgt_guid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        'source': src_guid,
                        'target': tgt_guid,
                        'type': 'front_in_back',
                        'weight': EDGE_WEIGHTS['front_in_back'],
                        'deck': deck_name,
                    })

    return edges


def _find_refs_bruteforce(note_fields, deck_name):
    """Fallback O(n²) pairwise matching with length pre-filtering."""
    edges = []
    seen_edges = set()

    for src in note_fields:
        src_front = src['front']
        src_len = src['front_len']
        if src_len < MIN_FRONT_LENGTH:
            continue

        for tgt in note_fields:
            if src['guid'] == tgt['guid']:
                continue

            edge_key = (src['guid'], tgt['guid'])
            if edge_key in seen_edges:
                continue

            if src_len <= len(tgt['front']) and src_front in tgt['front']:
                seen_edges.add(edge_key)
                edges.append({
                    'source': src['guid'],
                    'target': tgt['guid'],
                    'type': 'front_in_front',
                    'weight': EDGE_WEIGHTS['front_in_front'],
                    'deck': deck_name,
                })
            elif src_len <= len(tgt['other']) and src_front in tgt['other']:
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
