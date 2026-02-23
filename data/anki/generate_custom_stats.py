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


def calculate_future_due(cards_data, max_days=None):
    """
    Calculate future due cards.
    
    Cards are considered:
    - mature: interval >= 21 days
    - young: interval < 21 days
    
    Args:
        cards_data: List of card dicts
        max_days: Limit range (None for all cards)
    
    Returns list of {day, mature, young} dicts.
    """
    anki_today = get_anki_today()
    
    if max_days is None:
        # Find the maximum due date to determine range
        max_due = max(c.get("due", 0) for c in cards_data if c.get("queue") == 2)
        max_days = max_due - anki_today + 1  # Include today
    
    # Use day buckets
    day_buckets = {}
    
    for card in cards_data:
        due = card.get("due", 0)
        ivl = card.get("ivl", 0)
        queue = card.get("queue", 0)
        
        # Only count review cards (queue=2)
        if queue != 2:
            continue
        
        # Calculate days from now
        days_from_now = due - anki_today
        
        # Skip overdue cards (negative days)
        if days_from_now < 0:
            continue
        
        # Skip if beyond max_days
        if days_from_now >= max_days:
            continue
        
        # Initialize bucket if needed
        if days_from_now not in day_buckets:
            day_buckets[days_from_now] = {"mature": 0, "young": 0}
        
        # Determine if mature or young
        if ivl >= 21:
            day_buckets[days_from_now]["mature"] += 1
        else:
            day_buckets[days_from_now]["young"] += 1
    
    # Convert to list format
    result = []
    for day in range(max_days):
        if day in day_buckets:
            result.append({
                "day": day,
                "mature": day_buckets[day]["mature"],
                "young": day_buckets[day]["young"]
            })
        else:
            # No cards due on this day
            result.append({
                "day": day,
                "mature": 0,
                "young": 0
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

    # Generate web terminal stats (10 years - covers all ranges except "all")
    web_stats = calculate_future_due(cards_data, max_days=3650)
    web_output = {"futureDue": web_stats}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(web_output, f, indent=2)
    web_total = sum(d["mature"] + d["young"] for d in web_stats)
    print(f"   ✓ {OUTPUT_FILE.name} (10 years, {web_total:,} cards)")

    # Generate full forecast for analytics (all cards, compressed)
    full_stats = calculate_future_due(cards_data, max_days=None)
    full_output = {"futureDue": full_stats}
    full_file = SCRIPT_DIR / "full_forecast.json.gz"
    
    # Only write if content changed
    new_content = json.dumps(full_output)
    write_full = True
    if full_file.exists():
        try:
            with gzip.open(full_file, "rt", encoding="utf-8") as f:
                existing_content = f.read()
            if new_content == existing_content:
                write_full = False
        except Exception:
            pass
    
    if write_full:
        with gzip.open(full_file, "wt", encoding="utf-8") as f:
            f.write(new_content)
    
    full_total = sum(d["mature"] + d["young"] for d in full_stats)
    max_day = max(d["day"] for d in full_stats) if full_stats else 0
    status = "updated" if write_full else "unchanged"
    print(f"   ✓ {full_file.name} ({max_day:,} days, {full_total:,} cards, {full_file.stat().st_size / 1024:.1f} KB) [{status}]")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
