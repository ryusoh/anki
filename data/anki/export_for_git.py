#!/usr/bin/env python3
"""
Export Anki stats to Git-friendly format.
- Cards: Single JSON file (current state)
- Reviews: Partitioned by month (incremental)
"""

import sqlite3
import json
import gzip
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
SOURCE_DB = SCRIPT_DIR / "collection.anki2"
OUTPUT_DIR = SCRIPT_DIR

def fetch_and_anonymize(source_db):
    """Load data from Anki DB, excluding content fields."""
    conn = sqlite3.connect(source_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Cards with deck info
    cur.execute("""
        SELECT c.id, c.nid, c.did, c.ord, c.type, c.queue, c.due, 
               c.ivl, c.factor, c.reps, c.lapses, c.flags,
               d.name as deck_name
        FROM cards c
        LEFT JOIN decks d ON c.did = d.id
    """)
    cards = [dict(row) for row in cur.fetchall()]
    
    # Reviews (full history)
    cur.execute("""
        SELECT id, cid, ease, ivl, lastIvl, factor, time, type
        FROM revlog
        ORDER BY id
    """)
    reviews = [dict(row) for row in cur.fetchall()]
    
    # Decks
    cur.execute("SELECT id, name FROM decks")
    decks = {row[0]: row[1] for row in cur.fetchall()}
    
    # Note types
    cur.execute("SELECT id, name FROM notetypes")
    notetypes = {row[0]: row[1] for row in cur.fetchall()}
    
    # Notes metadata (no content)
    cur.execute("""
        SELECT id, mid, mod, usn, sfld, csum, flags
        FROM notes
    """)
    notes = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    return {
        'cards': cards,
        'reviews': reviews,
        'decks': decks,
        'notetypes': notetypes,
        'notes': notes
    }


def export_for_git():
    """Export data in Git-friendly format."""
    
    print("📦 Fetching data from Anki...")
    data = fetch_and_anonymize(SOURCE_DB)
    
    # Export cards (current snapshot)
    cards_file = OUTPUT_DIR / "cards.json.gz"
    with gzip.open(cards_file, 'wt', encoding='utf-8') as f:
        json.dump(data['cards'], f, ensure_ascii=False)
    print(f"   ✓ cards.json.gz ({cards_file.stat().st_size / 1024:.1f} KB)")
    
    # Export decks
    decks_file = OUTPUT_DIR / "decks.json"
    with open(decks_file, 'w', encoding='utf-8') as f:
        json.dump(data['decks'], f, ensure_ascii=False, indent=2)
    print(f"   ✓ decks.json ({decks_file.stat().st_size / 1024:.1f} KB)")
    
    # Export reviews partitioned by month
    reviews_dir = OUTPUT_DIR / "reviews"
    reviews_dir.mkdir(exist_ok=True)
    
    # Group reviews by YYYY-MM
    reviews_by_month = {}
    for review in data['reviews']:
        # Convert Anki timestamp (ms since epoch) to datetime
        ts = review['id'] / 1000
        dt = datetime.fromtimestamp(ts)
        month_key = dt.strftime('%Y-%m')
        
        if month_key not in reviews_by_month:
            reviews_by_month[month_key] = []
        reviews_by_month[month_key].append(review)
    
    # Write each month to separate file
    for month, reviews in sorted(reviews_by_month.items()):
        month_file = reviews_dir / f"{month}.json.gz"
        with gzip.open(month_file, 'wt', encoding='utf-8') as f:
            json.dump(reviews, f, ensure_ascii=False)
        print(f"   ✓ reviews/{month}.json.gz ({month_file.stat().st_size / 1024:.1f} KB, {len(reviews)} reviews)")
    
    # Summary
    total_reviews = sum(len(r) for r in reviews_by_month.values())
    total_size = sum(
        f.stat().st_size 
        for f in OUTPUT_DIR.glob("*.json*") 
        for f in [f]
    ) + sum(
        f.stat().st_size 
        for f in reviews_dir.glob("*.json*")
        for f in [f]
    )
    
    print()
    print(f"✅ Export complete!")
    print(f"   Total reviews: {total_reviews:,}")
    print(f"   Total size: {total_size / 1024 / 1024:.2f} MB")
    print()
    print("📁 Files ready for Git:")
    print("   • cards.json.gz - Current card states")
    print("   • decks.json - Deck information")
    print("   • reviews/YYYY-MM.json.gz - Monthly review partitions")


if __name__ == "__main__":
    export_for_git()
