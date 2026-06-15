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
DECKS_FILE = SCRIPT_DIR / "decks.json"
# Output to data/anki for web terminal and stats_page_customizer add-on
OUTPUT_FILE = SCRIPT_DIR / "custom_stats_data.json"

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
        try:
            cur = conn.cursor()
            cur.execute("SELECT crt FROM col")
            crt = cur.fetchone()[0]
        finally:
            conn.close()

        # Anki's day 0 is the collection creation date
        crt_date = datetime.fromtimestamp(crt).replace(hour=0, minute=0, second=0, microsecond=0)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (today - crt_date).days
    except Exception as e:
        print(f"Error calculating epoch days: {e}")
        # Fallback to 2007 epoch
        anki_epoch = datetime(2007, 1, 1)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (today - anki_epoch).days


def build_cid_to_deck(cards, decks_map=None):
    """Build card-ID-to-deck-name mapping using did + decks.json for current names.

    Prefers resolving via did -> decks_map (canonical, always current).
    Falls back to per-card deck_name (may be stale after deck merges/renames).
    """
    if decks_map is None:
        decks_map = {}
    cid_to_deck = {}
    for card in cards:
        cid = card.get("id")
        if cid is None:
            continue
        did = card.get("did")
        if did is not None and did in decks_map:
            raw = decks_map[did]
        elif "deck_name" in card:
            raw = card["deck_name"]
        else:
            continue
        cid_to_deck[cid] = raw.replace('\x1f', '::')
    return cid_to_deck


def calculate_future_due(cards_data, cid_to_deck=None, max_days=None, anki_today=None):
    """
    Calculate future due cards.
    
    Cards are considered:
    - mature: interval >= 21 days
    - young: interval < 21 days
    
    Args:
        cards_data: List of card dicts
        cid_to_deck: Dictionary mapping card ID to deck name
        max_days: Limit range (None for all cards)
        anki_today: Anki day number for today (defaults to get_anki_today())
    
    Returns tuple of (global_stats, by_deck_stats).
    """
    if anki_today is None:
        anki_today = get_anki_today()
    
    if cid_to_deck is None:
        cid_to_deck = {}

    if max_days is None:
        # Find the maximum due date to determine range
        review_cards_due = [c.get("due", 0) for c in cards_data if c.get("queue") == 2]
        if not review_cards_due:
            max_days = 0
        else:
            max_due = max(review_cards_due)
            max_days = max(0, max_due - anki_today + 1)  # Include today
    
    # Use day buckets
    day_buckets = {}
    deck_day_buckets = {}
    
    for card in cards_data:
        due = card.get("due", 0)
        ivl = card.get("ivl", 0)
        queue = card.get("queue", 0)
        cid = card.get("id")
        
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

        deck_name = cid_to_deck.get(cid, "Unknown") if cid else "Unknown"

        # Initialize bucket if needed
        if days_from_now not in day_buckets:
            day_buckets[days_from_now] = {"mature": 0, "young": 0}

        if deck_name not in deck_day_buckets:
            deck_day_buckets[deck_name] = {}
        if days_from_now not in deck_day_buckets[deck_name]:
            deck_day_buckets[deck_name][days_from_now] = {"mature": 0, "young": 0}
        
        # Determine if mature or young
        is_mature = ivl >= 21
        
        if is_mature:
            day_buckets[days_from_now]["mature"] += 1
            deck_day_buckets[deck_name][days_from_now]["mature"] += 1
        else:
            day_buckets[days_from_now]["young"] += 1
            deck_day_buckets[deck_name][days_from_now]["young"] += 1
    
    # Convert to list format
    # Global
    result_global = []
    for day in range(max_days):
        if day in day_buckets:
            result_global.append({
                "day": day,
                "mature": day_buckets[day]["mature"],
                "young": day_buckets[day]["young"]
            })
        else:
            result_global.append({
                "day": day,
                "mature": 0,
                "young": 0
            })

    # By Deck (we don't need zero-fill for days a deck has no reviews, to save space, 
    # but the frontend chart logic natively handles missing days if we just provide existing ones).
    # To match frontend expectations, we can just output the existing days per deck.
    result_by_deck = {}
    for deck_name, dt_buckets in deck_day_buckets.items():
        deck_list = []
        for d in sorted(dt_buckets.keys()):
            deck_list.append({
                "day": d,
                "mature": dt_buckets[d]["mature"],
                "young": dt_buckets[d]["young"]
            })
        result_by_deck[deck_name] = deck_list

    return result_global, result_by_deck


def _read_existing_total(path):
    """Read the total card count from an existing JSON file (fail-open helper)."""
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("futureDue", [])
        return sum(d.get("mature", 0) + d.get("young", 0) for d in entries)
    except Exception as e:
        print(f"Error aggregating review totals: {e}")
        return 0


def _should_write(new_stats, old_path, label=""):
    """Return True if new_stats look valid enough to overwrite old_path.

    Fail-open: if the old file had data but the new generation is empty or
    suspiciously small (< 10% of old total), keep the old file.
    """
    new_total = sum(d["mature"] + d["young"] for d in new_stats)
    old_total = _read_existing_total(old_path)

    if old_total == 0:
        # No old data to protect; always write
        return True

    if new_total == 0:
        print(f"   ⚠ {label}New data is empty; keeping old file ({old_total:,} cards)")
        return False

    if new_total < old_total * 0.1:
        print(
            f"   ⚠ {label}New data suspiciously small ({new_total:,} vs old {old_total:,}); "
            f"keeping old file"
        )
        return False

    return True


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

    # Load deck ID -> current name mapping from decks.json
    decks_map = {}
    if DECKS_FILE.exists():
        try:
            with open(DECKS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            decks_map = {int(k): v for k, v in raw.items()}
        except Exception as e:
            print(f"Warning: Failed to load decks.json: {e}")

    cid_to_deck = build_cid_to_deck(cards_data, decks_map)

    # Generate stats for web terminal and stats_page_customizer add-on
    web_stats, web_by_deck = calculate_future_due(cards_data, cid_to_deck, max_days=None)
    web_output = {
        "futureDue": web_stats,
        "futureDueByDeck": web_by_deck
    }

    # Fail-open: only overwrite if new data looks valid
    if _should_write(web_stats, OUTPUT_FILE, label=f"{OUTPUT_FILE.name}: "):
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(web_output, f, indent=2)
        web_total = sum(d["mature"] + d["young"] for d in web_stats)
        max_day = max(d["day"] for d in web_stats) if web_stats else 0
        print(f"   ✓ {OUTPUT_FILE.name} ({max_day:,} days, {web_total:,} cards)")
    else:
        print(f"   ✗ {OUTPUT_FILE.name} skipped (fail-open: old data preserved)")

    # Generate full forecast for analytics (all cards, compressed)
    full_stats, full_by_deck = calculate_future_due(cards_data, cid_to_deck, max_days=None)
    full_output = {
        "futureDue": full_stats,
        "futureDueByDeck": full_by_deck
    }
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
        except Exception as e:
            print(f"Error opening CUSTOM_STATS_DATA: {e}")

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
