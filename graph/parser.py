"""
Parser module for Anki knowledge graph.

Handles field extraction, tokenization, and deck grouping.
"""

import re
from collections import defaultdict


# Stop words to filter out during tokenization
STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were',
    'this', 'that', 'these', 'those', 'it', 'its',
    'which', 'what', 'where', 'when', 'why', 'how',
    'and', 'or', 'but', 'if', 'then', 'else', 'so',
    'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
    'from', 'as', 'be', 'have', 'has', 'had', 'will',
    'would', 'could', 'should', 'may', 'might', 'must',
    'can', 'into', 'through', 'during', 'before', 'after',
    'above', 'below', 'between', 'under', 'again', 'further',
    'once', 'here', 'there', 'all', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'than', 'too', 'very', 'just',
    'also', 'now', 'about', 'over', 'any', 'being', 'both',
}


def extract_fields(flds):
    """
    Extract structured fields from Anki flds string.
    
    Args:
        flds: Anki flds string (fields separated by ::)
    
    Returns:
        dict with keys:
            - front: First field (typically the question/front of card)
            - back: Second field (typically the answer/back of card)
            - extra: Third field (if exists)
            - all_fields: List of all fields
            - other_fields: All fields except front (as :: separated string)
            - other_fields_text: All fields except front (as space-separated text)
    """
    if not flds:
        flds = ""
    
    # Split by \x1f (Anki's actual field separator) or :: (test fixtures)
    if '\x1f' in flds:
        fields = flds.split('\x1f')
    else:
        fields = flds.split('::')
    
    result = {
        'front': fields[0] if len(fields) > 0 else '',
        'back': fields[1] if len(fields) > 1 else '',
        'extra': fields[2] if len(fields) > 2 else '',
        'all_fields': fields,
    }
    
    # Other fields (everything except front)
    other_fields = fields[1:] if len(fields) > 1 else []
    result['other_fields'] = '::'.join(other_fields)
    result['other_fields_text'] = ' '.join(other_fields)
    
    return result


def tokenize(text, min_length=3, use_stop_words=True):
    """
    Tokenize text into meaningful words.
    
    Args:
        text: Text to tokenize
        min_length: Minimum word length (default: 3)
        use_stop_words: Whether to filter stop words (default: True)
    
    Returns:
        List of lowercase tokens
    """
    if not text:
        return []
    
    # Extract alphabetic words (removes punctuation)
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Filter by length
    tokens = [w for w in words if len(w) >= min_length]
    
    # Filter stop words
    if use_stop_words:
        tokens = [w for w in tokens if w not in STOP_WORDS]
    
    return tokens


def extract_deck_info(note):
    """
    Extract deck information from a note.
    
    Args:
        note: Note dict with deck/deck_id fields
    
    Returns:
        dict with deck, deck_id, guid
    """
    return {
        'deck': note.get('deck'),
        'deck_id': note.get('deck_id'),
        'guid': note.get('guid'),
    }


def group_by_deck(notes):
    """
    Group notes by their deck.
    
    Args:
        notes: List of note dicts
    
    Returns:
        dict: {deck_name: [notes]}
    """
    grouped = defaultdict(list)
    
    for note in notes:
        deck = note.get('deck')
        if deck:
            grouped[deck].append(note)
    
    return dict(grouped)


def get_front_field(note):
    """
    Extract front field from a note.
    
    Args:
        note: Note dict with 'flds' field
    
    Returns:
        Front field text (first field)
    """
    fields = extract_fields(note.get('flds', ''))
    return fields['front']


def get_other_fields_text(note):
    """
    Extract all fields except front as space-separated text.
    
    Args:
        note: Note dict with 'flds' field
    
    Returns:
        All fields except front as space-separated text
    """
    fields = extract_fields(note.get('flds', ''))
    return fields['other_fields_text']
