#!/usr/bin/env python3
"""
Anonymize Anki database - preserve stats, remove card content.
Outputs a privacy-safe SQLite database for analytics.
"""

import sqlite3
import shutil
from pathlib import Path

# Paths
SOURCE_DB = Path("/Users/lz/Library/Application Support/Anki2/addons21/data/anki/collection.anki2")
OUTPUT_DB = Path("/Users/lz/Library/Application Support/Anki2/addons21/data/anki/collection_anonymized.anki2")

# Tables to export with their columns (excluding content fields)
TABLES_TO_EXPORT = {
    # Cards: scheduling stats only
    "cards": [
        "id", "nid", "did", "ord", "mod", "usn",
        "type", "queue", "due", "ivl", "factor",
        "reps", "lapses", "left", "odue", "odid", "flags"
    ],
    # Notes: metadata only, NO flds (actual content)
    "notes": [
        "id", "guid", "mid", "mod", "usn",
        "sfld", "csum", "flags"
        # Excluded: tags, flds (content), data
    ],
    # Review log: all stats, no personal info
    "revlog": [
        "id", "cid", "usn", "ease", "ivl",
        "lastIvl", "factor", "time", "type"
    ],
    # Decks: names and config
    "decks": ["id", "name", "mtime_secs", "usn"],
    # Deck config
    "deck_config": ["id", "name", "mtime_secs", "usn"],
    # Note types: structure only
    "notetypes": ["id", "name", "mtime_secs", "usn"],
    # Col: collection metadata (single row)
    "col": ["id", "crt", "mod", "scm", "ver", "dty", "usn", "ls"],
}


def anonymize_database():
    """Create anonymized copy of Anki database."""
    
    if not SOURCE_DB.exists():
        print(f"❌ Source database not found: {SOURCE_DB}")
        return False
    
    # Remove existing output
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()
    
    print(f"📋 Anonymizing database...")
    print(f"   Source: {SOURCE_DB}")
    print(f"   Output: {OUTPUT_DB}")
    print()
    
    # Connect to source
    src = sqlite3.connect(SOURCE_DB)
    dst = sqlite3.connect(OUTPUT_DB)
    
    src_cur = src.cursor()
    dst_cur = dst.cursor()
    
    # Create tables with content columns removed
    for table, columns in TABLES_TO_EXPORT.items():
        cols_str = ", ".join(columns)
        
        # Create table
        dst_cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                {cols_str}
            )
        """)
        
        # Copy data (excluding content fields)
        src_cur.execute(f"SELECT {cols_str} FROM {table}")
        rows = src_cur.fetchall()
        
        placeholders = ", ".join(["?" for _ in columns])
        dst_cur.executemany(
            f"INSERT INTO {table} VALUES ({placeholders})",
            rows
        )
        
        print(f"   ✓ {table}: {len(rows)} rows")
    
    # Create indexes for performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_cards_usn ON cards (usn)",
        "CREATE INDEX IF NOT EXISTS ix_cards_nid ON cards (nid)",
        "CREATE INDEX IF NOT EXISTS ix_cards_sched ON cards (did, queue, due)",
        "CREATE INDEX IF NOT EXISTS ix_notes_usn ON notes (usn)",
        "CREATE INDEX IF NOT EXISTS ix_notes_csum ON notes (csum)",
        "CREATE INDEX IF NOT EXISTS ix_revlog_usn ON revlog (usn)",
        "CREATE INDEX IF NOT EXISTS ix_revlog_cid ON revlog (cid)",
    ]
    
    for idx in indexes:
        dst_cur.execute(idx)
    
    dst.commit()
    
    # Close connections
    src.close()
    dst.close()
    
    # Report sizes
    src_size = SOURCE_DB.stat().st_size
    dst_size = OUTPUT_DB.stat().st_size
    
    print()
    print(f"✅ Anonymization complete!")
    print(f"   Original:  {src_size / 1024 / 1024:.1f} MB")
    print(f"   Anonymized: {dst_size / 1024 / 1024:.1f} MB")
    print(f"   Reduction: {(1 - dst_size/src_size) * 100:.1f}%")
    print()
    print("📊 Preserved data:")
    print("   • Card scheduling stats (due, interval, reps, lapses)")
    print("   • Review history (ease, time, type)")
    print("   • Deck structure")
    print("   • Note type definitions")
    print()
    print("🔒 Removed data:")
    print("   • Card content (flds field)")
    print("   • Tags")
    print("   • Custom data fields")
    
    return True


if __name__ == "__main__":
    anonymize_database()
