#!/usr/bin/env python3
"""
Migrate existing staged files to hash map.

Run this if you already have files staged in data/cloudflare/ but no hash map.
This will compute hashes from existing staged files so future uploads are incremental.
"""

import gzip
import hashlib
import json
import sys
from pathlib import Path

# Add graph module to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'graph'))

from hash_map import compute_note_hash, save_hash_map  # noqa: E402


def get_staging_dir():
    """Get local staging directory for R2 files."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "data" / "cloudflare").exists():
            return parent / "data" / "cloudflare"
    
    # Fallback to script location
    staging = SCRIPT_DIR.parent / "cloudflare"
    staging.mkdir(exist_ok=True)
    return staging


def compute_file_hash(file_path):
    """Compute SHA256 hash of file content."""
    with open(file_path, 'rb') as f:
        content = f.read()
    return hashlib.sha256(content).hexdigest()


def main():
    staging_dir = get_staging_dir()
    hash_map_file = staging_dir / "hash_map.json"
    
    print(f"🔍 Scanning staged files in: {staging_dir}")
    
    # Check if hash map already exists
    if hash_map_file.exists():
        print(f"⚠️  Hash map already exists at: {hash_map_file}")
        response = input("   Overwrite existing hash map? (y/N): ")
        if response.strip().lower() != 'y':
            print("   ⊘ Migration cancelled")
            return
    
    hash_map = {}
    
    # Load collection file hashes
    collection_files = [
        "collection/notes.json.gz",
        "collection/cards.json.gz",
        "collection/reviews.json.gz",
        "collection/decks.json",
        "collection/notetypes.json.gz",
        "collection/cards-data.json.gz",
        "collection/media-registry.json",
        "collection/collection-config.json",
    ]
    
    print("\n📦 Computing collection file hashes...")
    for key in collection_files:
        file_path = staging_dir / key
        if file_path.exists():
            hash_map[key] = compute_file_hash(file_path)
            print(f"   ✓ {key}")
        else:
            print(f"   ⊘ {key} (not found)")
    
    # Load individual note hashes
    notes_dir = staging_dir / "notes"
    if notes_dir.exists():
        note_files = list(notes_dir.glob("*.json.gz"))
        print(f"\n📝 Computing individual note hashes ({len(note_files):,} files)...")
        
        errors = []
        for i, note_file in enumerate(note_files, 1):
            try:
                # Read note to get GUID
                with gzip.open(note_file, 'rt', encoding='utf-8') as f:
                    content = f.read()
                    if not content:
                        raise ValueError("Empty file")
                    note = json.loads(content)
                    guid = note.get('guid')
                    if guid:
                        hash_map[guid] = compute_note_hash(note)
                    else:
                        # Use filename hash as fallback
                        hash_map[note_file.name] = compute_file_hash(note_file)
            except Exception as e:
                errors.append((note_file.name, str(e)))
            
            # Progress indicator
            if i % 10000 == 0:
                print(f"   Progress: {i:,}/{len(note_files):,}")
        
        # Report errors - DON'T silently skip corrupted files
        if errors:
            print(f"\n   ⚠️  {len(errors)} corrupted file(s) detected:")
            for filename, error in errors[:10]:  # Show first 10
                print(f"      - {filename}: {error}")
            if len(errors) > 10:
                print(f"      ... and {len(errors) - 10} more")
            
            response = input("\n   Continue anyway? (y/N): ")
            if response.strip().lower() != 'y':
                print("   ⊘ Migration cancelled - fix corrupted files first")
                sys.exit(1)
        
        print(f"   ✓ Processed {len(note_files) - len(errors):,} valid note files")
    else:
        print("\n⚠️  No individual notes found in staging directory")
    
    # Save hash map
    print(f"\n💾 Saving hash map to: {hash_map_file}")
    save_hash_map(hash_map, hash_map_file)
    
    print("\n✅ Migration complete!")
    print(f"   Hash map entries: {len(hash_map):,}")
    print(f"   Collection files: {len([k for k in hash_map if k.startswith('collection/')])}")
    print(f"   Individual notes: {len([k for k in hash_map if not k.startswith('collection/')])}")
    print("\n   Future uploads will be incremental (only changed files)")


if __name__ == "__main__":
    main()
