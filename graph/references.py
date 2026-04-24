"""
References module for Anki knowledge graph.

Finds cross-references between notes within the same deck.
Matching modes:
- Whole-front: edge when card A's entire front appears in card B's content
- Sub-phrase with TF-IDF gating: front is split on delimiters and spaces,
  each fragment's IDF is computed across the deck, and only high-IDF
  (rare/discriminative) fragments are matched — no stopword lists needed

Optimizations:
- Aho-Corasick automaton for O(n + m) multi-pattern substring matching
  instead of O(n²) pairwise comparison
- Multiprocessing to split large decks into parallel chunks
"""

import re
import math
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
    'front_in_front': 3.0,        # Card A's full front appears in card B's front
    'front_in_back': 2.0,         # Card A's full front appears in card B's back
    'subphrase_in_front': 2.0,    # High-IDF sub-phrase of A's front in B's front
    'subphrase_in_back': 1.0,     # High-IDF sub-phrase of A's front in B's back
}

# Minimum front field length to consider for matching
MIN_FRONT_LENGTH = 1

# IDF threshold — only sub-phrases rarer than this are kept.
# IDF = ln(N/DF). With N=50000: DF≤6800 → IDF≥2.0, DF≤680 → IDF≥4.3
# 2.0 means the term appears in at most ~13% of cards in the deck.
_MIN_IDF = 2.0

# Delimiters for splitting front fields into sub-phrases
_SPLIT_RE = re.compile(r'[()（）\[\]【】:：\-—–/|,，;；""\"\'?？]')

# Strip Anki cloze deletion markers: {{c1::, {{c2::, etc. and closing }}
_CLOZE_RE = re.compile(r'\{\{c\d+::|\}\}')

# Regex to detect CJK characters (Hanzi, Kanji, Hiragana, Katakana)
_CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u309f\u30a0-\u30ff]')

# Minimum sub-phrase length (chars). Single characters cause spurious
# substring matches: "人" matches inside "人口", "大人", etc.
_MIN_SUBPHRASE_LEN = 2

# Maximum Document Frequency ratio. Sub-phrases appearing in more than
# 2% of the deck are too common to be useful links (e.g. "拼音練習").
_MAX_DF_RATIO = 0.02

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


def _tokenize_front(front_norm):
    """Extract candidate sub-phrases from a front field.

    Strips cloze markers, then splits on structural delimiters.
    Requires sub-phrases to be at least 2 characters to avoid
    single-char substring noise. IDF filtering happens later.
    """
    # Strip cloze syntax before splitting — otherwise ":" in {{c1::answer}}
    # produces garbage fragments like "{{c1" and "answer}}"
    text = _CLOZE_RE.sub('', front_norm).strip()
    tokens = set()
    parts = _SPLIT_RE.split(text)
    for part in parts:
        p = part.strip()
        if not p or p == front_norm or len(p) < _MIN_SUBPHRASE_LEN:
            continue
        tokens.add(p)
    return tokens


def _compute_df(note_fields):
    """Compute Document Frequency (DF) for candidate sub-phrases across a deck.

    Uses Aho-Corasick for O(N * text_length) frequency counting.
    Returns dict: token → occurrence count
    """
    N = len(note_fields)
    if N == 0:
        return {}

    # Collect all candidate tokens from all fronts
    all_tokens = set()
    for nf in note_fields:
        all_tokens.update(nf.get('subphrases_raw', set()))

    if not all_tokens:
        return {}

    df = {}

    if HAS_AHO and len(all_tokens) > 20:
        auto = ahocorasick.Automaton()
        for token in all_tokens:
            auto.add_word(token, token)
        auto.make_automaton()

        for nf in note_fields:
            combined = nf['front'] + ' ' + nf['other']
            found = set()
            for _, matched in auto.iter(combined):
                found.add(matched)
            for token in found:
                df[token] = df.get(token, 0) + 1
    else:
        for nf in note_fields:
            combined = nf['front'] + ' ' + nf['other']
            for token in all_tokens:
                if token in combined:
                    df[token] = df.get(token, 0) + 1

    return df


def _prepare_note_fields(notes, deck_name=""):
    """Pre-compute normalized fields for a list of notes.
    
    If the deck is a Language deck (日語, 粤語, 呉語, 台語), purely phonetic
    or Latin sub-phrases (those without any CJK characters) are excluded.
    """
    is_cjk_deck = any(k in deck_name for k in ['日語', '粤語', '呉語', '台語'])
    
    result = []
    for note in notes:
        front_norm = _normalize(get_front_field(note))
        other_norm = _normalize(get_other_fields_text(note))
        raw_tokens = _tokenize_front(front_norm) if len(front_norm) >= MIN_FRONT_LENGTH else set()
        
        if is_cjk_deck:
            # Drop sub-phrases that contain absolutely no CJK characters
            # (e.g. "is", "ni", "186", "desu")
            raw_tokens = {t for t in raw_tokens if _CJK_RE.search(t)}
            
        result.append({
            'guid': note['guid'],
            'front': front_norm,
            'front_len': len(front_norm),
            'other': other_norm,
            'subphrases_raw': raw_tokens,  # unfiltered, for DF computation
            'subphrases': [],              # filled after DF filtering
        })
    return result


def _apply_df_filter(note_fields, df):
    """Filter sub-phrases by Max Document Frequency limit. Mutates in place."""
    N = len(note_fields)
    # A term must not appear in more than 2% of the deck (min 10 cards for small decks)
    max_allowed_df = max(10, int(N * _MAX_DF_RATIO))
    
    for nf in note_fields:
        nf['subphrases'] = [
            sp for sp in nf['subphrases_raw']
            if df.get(sp, 0) <= max_allowed_df and sp != nf['front']
        ]


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
    Find references within a single deck.

    Steps:
    1. Tokenize all fronts into candidate sub-phrases
    2. Compute Document Frequency (DF) across the deck
    3. Filter: only keep sub-phrases appearing in <= 2% of cards
    4. Build Aho-Corasick automaton from full fronts + surviving sub-phrases
    5. Scan and create edges

    Args:
        deck_notes: List of notes from one deck
        deck_name: Name of the deck

    Returns:
        List of edge dicts
    """
    if len(deck_notes) < 2:
        return []

    note_fields = _prepare_note_fields(deck_notes, deck_name)

    # Compute DF and filter out overly common sub-phrases
    df = _compute_df(note_fields)
    _apply_df_filter(note_fields, df)

    if HAS_AHO and len(note_fields) > 50:
        if len(note_fields) > _LARGE_DECK_THRESHOLD:
            return _find_refs_aho_parallel(note_fields, deck_name)
        return _find_refs_aho(note_fields, deck_name)
    return _find_refs_bruteforce(note_fields, deck_name)


def _build_automaton(note_fields):
    """Build Aho-Corasick automaton and guid lookup from note fields.

    Indexes both full fronts and IDF-filtered sub-phrases.
    guid_by_pattern maps pattern -> list of (guid, is_subphrase) tuples.
    """
    automaton = ahocorasick.Automaton()
    guid_by_pattern = {}

    for nf in note_fields:
        if nf['front_len'] < MIN_FRONT_LENGTH:
            continue
        front = nf['front']
        # Add full front
        if front not in guid_by_pattern:
            guid_by_pattern[front] = []
            automaton.add_word(front, front)
        guid_by_pattern[front].append((nf['guid'], False))

        # Add IDF-filtered sub-phrases
        for sp in nf.get('subphrases', []):
            if sp == front:
                continue
            if sp not in guid_by_pattern:
                guid_by_pattern[sp] = []
                automaton.add_word(sp, sp)
            guid_by_pattern[sp].append((nf['guid'], True))

    if guid_by_pattern:
        automaton.make_automaton()

    return automaton, guid_by_pattern


def _edge_type(in_front, is_subphrase):
    """Return edge type string based on match location and whether it's a sub-phrase."""
    if in_front:
        return 'subphrase_in_front' if is_subphrase else 'front_in_front'
    return 'subphrase_in_back' if is_subphrase else 'front_in_back'


def _scan_chunk(args):
    """Scan a chunk of target notes against a pre-built automaton. For multiprocessing."""
    chunk, all_note_fields, deck_name = args

    automaton, guid_by_pattern = _build_automaton(all_note_fields)
    if not guid_by_pattern:
        return []

    edges = []
    seen_edges = set()

    for tgt in chunk:
        tgt_guid = tgt['guid']

        for end_idx, matched in automaton.iter(tgt['front']):
            for src_guid, is_sub in guid_by_pattern[matched]:
                if src_guid == tgt_guid:
                    continue
                edge_key = (src_guid, tgt_guid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    etype = _edge_type(True, is_sub)
                    edges.append({
                        'source': src_guid,
                        'target': tgt_guid,
                        'type': etype,
                        'weight': EDGE_WEIGHTS[etype],
                        'deck': deck_name,
                    })

        matched_in_front = {ek[0] for ek in seen_edges if ek[1] == tgt_guid}
        for end_idx, matched in automaton.iter(tgt['other']):
            for src_guid, is_sub in guid_by_pattern[matched]:
                if src_guid == tgt_guid or src_guid in matched_in_front:
                    continue
                edge_key = (src_guid, tgt_guid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    etype = _edge_type(False, is_sub)
                    edges.append({
                        'source': src_guid,
                        'target': tgt_guid,
                        'type': etype,
                        'weight': EDGE_WEIGHTS[etype],
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
    Single-threaded Aho-Corasick: build automaton from all front fields
    and IDF-filtered sub-phrases, then scan each note's text once.
    """
    automaton, guid_by_pattern = _build_automaton(note_fields)
    if not guid_by_pattern:
        return []

    edges = []
    seen_edges = set()

    for tgt in note_fields:
        tgt_guid = tgt['guid']

        for end_idx, matched in automaton.iter(tgt['front']):
            for src_guid, is_sub in guid_by_pattern[matched]:
                if src_guid == tgt_guid:
                    continue
                edge_key = (src_guid, tgt_guid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    etype = _edge_type(True, is_sub)
                    edges.append({
                        'source': src_guid,
                        'target': tgt_guid,
                        'type': etype,
                        'weight': EDGE_WEIGHTS[etype],
                        'deck': deck_name,
                    })

        matched_in_front = {ek[0] for ek in seen_edges if ek[1] == tgt_guid}
        for end_idx, matched in automaton.iter(tgt['other']):
            for src_guid, is_sub in guid_by_pattern[matched]:
                if src_guid == tgt_guid or src_guid in matched_in_front:
                    continue
                edge_key = (src_guid, tgt_guid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    etype = _edge_type(False, is_sub)
                    edges.append({
                        'source': src_guid,
                        'target': tgt_guid,
                        'type': etype,
                        'weight': EDGE_WEIGHTS[etype],
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

        # Collect all patterns: full front + IDF-filtered sub-phrases
        patterns = [(src_front, False)]
        for sp in src.get('subphrases', []):
            if sp != src_front:
                patterns.append((sp, True))

        for tgt in note_fields:
            if src['guid'] == tgt['guid']:
                continue

            edge_key = (src['guid'], tgt['guid'])
            if edge_key in seen_edges:
                continue

            for pattern, is_sub in patterns:
                plen = len(pattern)
                if plen <= len(tgt['front']) and pattern in tgt['front']:
                    seen_edges.add(edge_key)
                    etype = _edge_type(True, is_sub)
                    edges.append({
                        'source': src['guid'],
                        'target': tgt['guid'],
                        'type': etype,
                        'weight': EDGE_WEIGHTS[etype],
                        'deck': deck_name,
                    })
                    break
                elif plen <= len(tgt['other']) and pattern in tgt['other']:
                    seen_edges.add(edge_key)
                    etype = _edge_type(False, is_sub)
                    edges.append({
                        'source': src['guid'],
                        'target': tgt['guid'],
                        'type': etype,
                        'weight': EDGE_WEIGHTS[etype],
                        'deck': deck_name,
                    })
                    break

    return edges


def find_references_incremental(all_deck_notes, changed_guids, deck_name):
    """
    Find references involving changed notes only.

    Instead of O(n²) over the full deck, this does:
    - Build automaton from ALL fronts, scan only changed notes' text → edges TO changed
    - Build automaton from only CHANGED fronts, scan all notes' text → edges FROM changed

    Args:
        all_deck_notes: All notes in the deck (including unchanged)
        changed_guids: Set of guids that are new or modified
        deck_name: Name of the deck

    Returns:
        List of edge dicts involving at least one changed node
    """
    if not HAS_AHO or len(all_deck_notes) < 2:
        # Fallback: just do full rebuild for this deck
        return find_references_for_deck_only(all_deck_notes, deck_name)

    all_fields = _prepare_note_fields(all_deck_notes)

    # Compute IDF from all notes and filter sub-phrases
    idf = _compute_idf(all_fields)
    _apply_idf_filter(all_fields, idf)

    changed_fields = [nf for nf in all_fields if nf['guid'] in changed_guids]

    if not changed_fields:
        return []

    edges = []
    seen_edges = set()

    # 1) Edges TO changed notes: scan changed notes' text against ALL patterns
    automaton_all, guid_by_pattern_all = _build_automaton(all_fields)
    if guid_by_pattern_all:
        for tgt in changed_fields:
            _scan_target(tgt, automaton_all, guid_by_pattern_all, deck_name, edges, seen_edges)

    # 2) Edges FROM changed notes: scan ALL notes' text against changed patterns only
    automaton_changed, guid_by_pattern_changed = _build_automaton(changed_fields)
    if guid_by_pattern_changed:
        for tgt in all_fields:
            if tgt['guid'] in changed_guids:
                continue  # already handled above
            _scan_target(tgt, automaton_changed, guid_by_pattern_changed, deck_name, edges, seen_edges)

    return edges


def _scan_target(tgt, automaton, guid_by_pattern, deck_name, edges, seen_edges):
    """Scan a single target note against an automaton, appending found edges."""
    tgt_guid = tgt['guid']

    for end_idx, matched in automaton.iter(tgt['front']):
        for src_guid, is_sub in guid_by_pattern[matched]:
            if src_guid == tgt_guid:
                continue
            edge_key = (src_guid, tgt_guid)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                etype = _edge_type(True, is_sub)
                edges.append({
                    'source': src_guid,
                    'target': tgt_guid,
                    'type': etype,
                    'weight': EDGE_WEIGHTS[etype],
                    'deck': deck_name,
                })

    matched_in_front = {ek[0] for ek in seen_edges if ek[1] == tgt_guid}
    for end_idx, matched in automaton.iter(tgt['other']):
        for src_guid, is_sub in guid_by_pattern[matched]:
            if src_guid == tgt_guid or src_guid in matched_in_front:
                continue
            edge_key = (src_guid, tgt_guid)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                etype = _edge_type(False, is_sub)
                edges.append({
                    'source': src_guid,
                    'target': tgt_guid,
                    'type': etype,
                    'weight': EDGE_WEIGHTS[etype],
                    'deck': deck_name,
                })


def calculate_edge_weight(edge_type):
    """
    Calculate edge weight based on type.

    Args:
        edge_type: One of front_in_front, front_in_back, subphrase_in_front, subphrase_in_back

    Returns:
        float: Edge weight
    """
    return EDGE_WEIGHTS.get(edge_type, 1.0)
