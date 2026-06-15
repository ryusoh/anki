"""
Hash map module for incremental staging.

Computes content hashes for notes and tracks changes between runs.
"""

import hashlib
import json
from pathlib import Path


def compute_note_hash(note):
    """
    Compute SHA256 hash of note content.

    Hash is based on content fields only (not GUID or metadata).
    This allows detecting when a note's content changes.

    Args:
        note: Note dict with guid, flds, tags, mid, etc.

    Returns:
        SHA256 hex string (64 characters)
    """
    # Hash content fields only (not guid, id, mod, etc.)
    content = {
        'flds': note.get('flds', ''),
        'tags': note.get('tags', ''),
        'mid': note.get('mid', 0),
    }

    # Create deterministic JSON string
    content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)

    # Compute SHA256
    hash_obj = hashlib.sha256(content_str.encode('utf-8'))
    return hash_obj.hexdigest()


def create_hash_map():
    """
    Create empty hash map.

    Returns:
        Empty dict
    """
    return {}


def load_hash_map(hash_map_file):
    """
    Load hash map from file.

    Args:
        hash_map_file: Path to hash_map.json

    Returns:
        Dict {guid: hash} or empty dict if file doesn't exist
    """
    hash_map_file = Path(hash_map_file)

    if not hash_map_file.exists():
        return {}

    try:
        with open(hash_map_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_hash_map(hash_map, hash_map_file):
    """
    Save hash map to file.

    Args:
        hash_map: Dict {guid: hash}
        hash_map_file: Path to save to
    """
    hash_map_file = Path(hash_map_file)
    hash_map_file.parent.mkdir(parents=True, exist_ok=True)

    with open(hash_map_file, 'w', encoding='utf-8') as f:
        json.dump(hash_map, f, indent=2, ensure_ascii=False)


def find_changed_notes(notes, old_hash_map):
    """
    Find notes that changed since last run.

    Args:
        notes: List of current note dicts
        old_hash_map: Dict {guid: hash} from last run

    Returns:
        Tuple of (changed_notes, unchanged_notes)
    """
    changed = []
    unchanged = []

    for note in notes:
        guid = note.get('guid')
        if not guid:
            continue

        current_hash = compute_note_hash(note)
        old_hash = old_hash_map.get(guid)

        if old_hash is None or old_hash != current_hash:
            # New note or content changed
            changed.append(note)
        else:
            # Content unchanged
            unchanged.append(note)

    return changed, unchanged


def update_hash_map(old_hash_map, notes):
    """
    Update hash map with current notes.

    Args:
        old_hash_map: Previous hash map
        notes: List of current note dicts

    Returns:
        Updated hash map
    """
    updated = dict(old_hash_map)

    for note in notes:
        guid = note.get('guid')
        if guid:
            updated[guid] = compute_note_hash(note)

    return updated
