#!/usr/bin/env python3
"""
Generate review_stats_data.json from Anki reviews for terminal display.
Aggregates review counts, time spent, and retention by day.
"""

import json
import gzip
import os
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
REVIEWS_DIR = SCRIPT_DIR / "reviews"
OUTPUT_FILE = Path(os.environ.get("ANKI_REVIEW_STATS_OUTPUT", str(SCRIPT_DIR / "review_stats_data.json")))
CARDS_FILE = SCRIPT_DIR / "cards.json.gz"


def parse_review_timestamp(ts_ms):
    """Convert review timestamp (ms) to date string."""
    return datetime.fromtimestamp(ts_ms / 1000).date()


def _init_stats(date_str):
    return {
        "date": date_str, "count": 0, "time": 0,
        "time_mature": 0, "time_young": 0, "time_learn": 0, "time_relearn": 0, "time_filtered": 0,
        "mature": 0, "young": 0, "again": 0, "hard": 0, "good": 0, "easy": 0,
        "learn": 0, "review": 0, "relearn": 0, "filtered": 0
    }


def _accumulate_review_stats(stats, review):
    stats["count"] += 1
    rev_time = review.get("time", 0)
    stats["time"] += rev_time

    if review.get("ivl", 0) >= 21:
        stats["mature"] += 1
        stats["time_mature"] += rev_time
    else:
        stats["young"] += 1
        stats["time_young"] += rev_time

    ease = review.get("ease", 0)
    if ease == 1:
        stats["again"] += 1
    elif ease == 2:
        stats["hard"] += 1
    elif ease == 3:
        stats["good"] += 1
    elif ease == 4:
        stats["easy"] += 1

    rtype = review.get("type", 0)
    if rtype == 0:
        stats["learn"] += 1
        stats["time_learn"] += rev_time
    elif rtype == 1:
        stats["review"] += 1
    elif rtype == 2:
        stats["relearn"] += 1
        stats["time_relearn"] += rev_time
    elif rtype == 3:
        stats["filtered"] += 1
        stats["time_filtered"] += rev_time


def _process_stats_dict(s_dict):
    result_list = []
    for date_str in sorted(s_dict.keys()):
        stats = s_dict[date_str]
        total_answered = stats["again"] + stats["hard"] + stats["good"] + stats["easy"]
        retention = (stats["good"] + stats["easy"]) / total_answered if total_answered > 0 else 0
        stats["retention"] = round(retention, 4)
        stats["time"] = round(stats["time"] / 1000, 1)
        stats["time_mature"] = round(stats["time_mature"] / 1000, 1)
        stats["time_young"] = round(stats["time_young"] / 1000, 1)
        stats["time_learn"] = round(stats["time_learn"] / 1000, 1)
        stats["time_relearn"] = round(stats["time_relearn"] / 1000, 1)
        stats["time_filtered"] = round(stats["time_filtered"] / 1000, 1)
        result_list.append(stats)
    return result_list


def aggregate_reviews():
    """Aggregate all reviews by day, globally and by deck."""
    if not REVIEWS_DIR.exists():
        return None, None
    
    # Load cid -> deck_name mapping
    cid_to_deck = {}
    if CARDS_FILE.exists():
        try:
            with gzip.open(CARDS_FILE, "rt", encoding="utf-8") as f:
                cards = json.load(f)
                for card in cards:
                    if "id" in card and "deck_name" in card:
                        # deck_name often contains the full path like Language\x1fEnglish
                        cid_to_deck[card["id"]] = card["deck_name"].replace('\x1f', '::')
        except Exception as e:
            print(f"Warning: Failed to load cards mapping: {e}")
    
    # Collect all reviews
    all_reviews = []
    for review_file in sorted(REVIEWS_DIR.glob("*.json.gz")):
        with gzip.open(review_file, "rt", encoding="utf-8") as f:
            reviews = json.load(f)
            all_reviews.extend(reviews)
    
    if not all_reviews:
        return None, None
    
    # Sort by timestamp
    all_reviews.sort(key=lambda r: r["id"])
    
    # Aggregate by day and by deck
    daily_stats = {}
    deck_daily_stats = {}
    
    for review in all_reviews:
        date_str = parse_review_timestamp(review["id"]).isoformat()
        
        # Determine deck
        cid = review.get("cid")
        deck_name = cid_to_deck.get(cid, "Unknown") if cid else "Unknown"
        
        # Initialize global stats for the day if missing
        if date_str not in daily_stats:
            daily_stats[date_str] = _init_stats(date_str)
        
        # Initialize deck stats for the day if missing
        if deck_name not in deck_daily_stats:
            deck_daily_stats[deck_name] = {}
        if date_str not in deck_daily_stats[deck_name]:
            deck_daily_stats[deck_name][date_str] = _init_stats(date_str)
        
        # Accumulate stats
        for stats in (daily_stats[date_str], deck_daily_stats[deck_name][date_str]):
            _accumulate_review_stats(stats, review)
    
    result_global = _process_stats_dict(daily_stats)
    
    result_by_deck = {}
    for deck_name, d_stats in deck_daily_stats.items():
        result_by_deck[deck_name] = _process_stats_dict(d_stats)
    
    return result_global, result_by_deck


def _read_existing_review_total(path):
    """Read the total review count from an existing JSON file (fail-open helper)."""
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("reviews", [])
        return sum(d.get("count", 0) for d in entries)
    except Exception as e:
        print(f"Error aggregating day counts: {e}")
        return 0


def _should_write_reviews(new_reviews, old_path):
    """Return True if new data looks valid enough to overwrite old_path.

    Fail-open: if the old file had data but the new generation is empty or
    suspiciously small (< 10% of old total), keep the old file.
    """
    new_total = sum(r["count"] for r in new_reviews)
    old_total = _read_existing_review_total(old_path)

    if old_total == 0:
        return True

    if new_total == 0:
        print(f"   ⚠ New data is empty; keeping old file ({old_total:,} reviews)")
        return False

    if new_total < old_total * 0.1:
        print(
            f"   ⚠ New data suspiciously small ({new_total:,} vs old {old_total:,}); "
            f"keeping old file"
        )
        return False

    return True


def main():
    print("📊 Generating review stats from Anki data...")
    
    reviews, reviews_by_deck = aggregate_reviews()
    
    if not reviews:
        # Fail-open: if old file exists, keep it
        old_total = _read_existing_review_total(OUTPUT_FILE)
        if old_total > 0:
            print(f"   ⚠ No new review data; keeping old file ({old_total:,} reviews)")
            return True
        print("   ❌ No review data found")
        return False
    
    # Fail-open: validate before overwriting
    if not _should_write_reviews(reviews, OUTPUT_FILE):
        print(f"   ✗ {OUTPUT_FILE.name} skipped (fail-open: old data preserved)")
        return True

    output = {
        "reviews": reviews,
        "reviewsByDeck": reviews_by_deck
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    total_reviews = sum(r["count"] for r in reviews)
    total_time = sum(r["time"] for r in reviews)
    avg_retention = sum(r["retention"] * r["count"] for r in reviews) / total_reviews if total_reviews > 0 else 0
    
    print(f"   ✓ {OUTPUT_FILE.name} generated")
    print(f"   Date range: {reviews[0]['date']} to {reviews[-1]['date']}")
    print(f"   Total reviews: {total_reviews:,}")
    print(f"   Total time: {total_time / 3600:.1f} hours")
    print(f"   Avg retention: {avg_retention * 100:.1f}%")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
