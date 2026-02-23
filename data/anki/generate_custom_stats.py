#!/usr/bin/env python3
"""
Generate custom_stats_data.json from Anki cards.json.gz for terminal display.
Creates future due chart data based on card intervals and due dates.
"""

import json
import gzip
import sqlite3
from pathlib import Path
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CARDS_FILE = SCRIPT_DIR / "cards.json.gz"
OUTPUT_FILE = SCRIPT_DIR.parent.parent / "custom_stats_data.json"

# Find Anki collection to get crt (creation time)
def find_anki_collection():
    """Find the Anki collection.anki2 file."""
    anki_base = Path.home() / "Library" / "Application Support" / "Anki2"
    for profile_dir in anki_base.iterdir():
        if profile_dir.is_dir():
            collection_db = profile_dir / "collection.anki2"
            if collection_db.exists():
                return collection_db
    return None


def get_anki_today():
    """Get today's Anki day number based on collection creation time."""
    collection_db = find_anki_collection()
    if not collection_db:
        # Fallback: use 2007 epoch (old Anki versions)
        anki_epoch = datetime(2007, 1, 1)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (today - anki_epoch).days
    
    try:
        conn = sqlite3.connect(collection_db)
        cur = conn.cursor()
        cur.execute("SELECT crt FROM col")
        crt = cur.fetchone()[0]
        conn.close()
        
        # Anki's day 0 is the collection creation date
        crt_date = datetime.fromtimestamp(crt).replace(hour=0, minute=0, second=0, microsecond=0)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (today - crt_date).days
    except Exception:
        # Fallback to 2007 epoch
        anki_epoch = datetime(2007, 1, 1)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (today - anki_epoch).days


def calculate_future_due(cards_data, days=30):
    """
    Calculate future due cards for the next N days.
    
    Cards are considered:
    - mature: interval >= 21 days
    - young: interval < 21 days
    
    Returns list of {day, mature, young} dicts.
    """
    anki_today = get_anki_today()
    day_buckets = {i: {"mature": 0, "young": 0} for i in range(days)}
    
    for card in cards_data:
        due = card.get("due", 0)
        ivl = card.get("ivl", 0)
        queue = card.get("queue", 0)
        
        # Only count review cards (queue=2)
        if queue != 2:
            continue
        
        # Calculate days from now
        days_from_now = due - anki_today
        
        # Only count cards due within the next N days (0 to days-1)
        if 0 <= days_from_now < days:
            # Determine if mature or young
            if ivl >= 21:
                day_buckets[days_from_now]["mature"] += 1
            else:
                day_buckets[days_from_now]["young"] += 1
    
    # Convert to list format
    result = []
    for day in range(days):
        result.append({
            "day": day,
            "mature": day_buckets[day]["mature"],
            "young": day_buckets[day]["young"]
        })
    
    return result


def main():
    if not CARDS_FILE.exists():
        print(f"❌ Cards file not found: {CARDS_FILE}")
        print("   Run 'make fetch' or 'python3 data/anki/fetch' first.")
        return False
    
    print("📊 Generating custom stats from Anki data...")
    
    # Load cards
    with gzip.open(CARDS_FILE, "rt", encoding="utf-8") as f:
        cards_data = json.load(f)
    
    print(f"   Loaded {len(cards_data):,} cards")
    
    # Calculate future due
    future_due = calculate_future_due(cards_data, days=30)
    
    # Build output
    output = {
        "futureDue": future_due
    }
    
    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    total_mature = sum(d["mature"] for d in future_due)
    total_young = sum(d["young"] for d in future_due)
    
    print(f"   ✓ {OUTPUT_FILE.name} generated")
    print(f"   Total due in 30 days: {total_mature + total_young:,} cards")
    print(f"     - Mature: {total_mature:,}")
    print(f"     - Young: {total_young:,}")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
