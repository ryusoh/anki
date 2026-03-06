#!/usr/bin/env python3
"""
Generate review_stats_data.json from Anki reviews for terminal display.
Aggregates review counts, time spent, and retention by day.
"""

import json
import gzip
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
REVIEWS_DIR = SCRIPT_DIR / "reviews"
OUTPUT_FILE = SCRIPT_DIR / "review_stats_data.json"


def parse_review_timestamp(ts_ms):
    """Convert review timestamp (ms) to date string."""
    return datetime.fromtimestamp(ts_ms / 1000).date()


def aggregate_reviews():
    """Aggregate all reviews by day."""
    if not REVIEWS_DIR.exists():
        return None
    
    # Collect all reviews
    all_reviews = []
    for review_file in sorted(REVIEWS_DIR.glob("*.json.gz")):
        with gzip.open(review_file, "rt", encoding="utf-8") as f:
            reviews = json.load(f)
            all_reviews.extend(reviews)
    
    if not all_reviews:
        return None
    
    # Sort by timestamp
    all_reviews.sort(key=lambda r: r["id"])
    
    # Aggregate by day
    daily_stats = {}
    for review in all_reviews:
        date_str = parse_review_timestamp(review["id"]).isoformat()
        
        if date_str not in daily_stats:
            daily_stats[date_str] = {
                "date": date_str,
                "count": 0,
                "time": 0,
                "time_mature": 0,
                "time_young": 0,
                "time_learn": 0,
                "time_relearn": 0,
                "time_filtered": 0,
                "mature": 0,
                "young": 0,
                "again": 0,  # ease=1
                "hard": 0,   # ease=2
                "good": 0,   # ease=3
                "easy": 0,   # ease=4
                "learn": 0,  # type=0
                "review": 0, # type=1
                "relearn": 0,# type=2
                "filtered": 0# type=3
            }
        
        stats = daily_stats[date_str]
        stats["count"] += 1

        rev_time = review.get("time", 0)
        stats["time"] += rev_time
        
        # Count by maturity (ivl >= 21 = mature)
        if review.get("ivl", 0) >= 21:
            stats["mature"] += 1
            stats["time_mature"] += rev_time
        else:
            stats["young"] += 1
            stats["time_young"] += rev_time
        
        # Count by ease
        ease = review.get("ease", 0)
        if ease == 1:
            stats["again"] += 1
        elif ease == 2:
            stats["hard"] += 1
        elif ease == 3:
            stats["good"] += 1
        elif ease == 4:
            stats["easy"] += 1
        
        # Count by type
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
    
    # Convert to list and calculate retention
    result = []
    for date_str in sorted(daily_stats.keys()):
        stats = daily_stats[date_str]
        # Retention = (good + easy) / (again + hard + good + easy)
        total_answered = stats["again"] + stats["hard"] + stats["good"] + stats["easy"]
        retention = (stats["good"] + stats["easy"]) / total_answered if total_answered > 0 else 0
        stats["retention"] = round(retention, 4)
        stats["time"] = round(stats["time"] / 1000, 1)  # Convert to seconds
        stats["time_mature"] = round(stats["time_mature"] / 1000, 1)
        stats["time_young"] = round(stats["time_young"] / 1000, 1)
        stats["time_learn"] = round(stats["time_learn"] / 1000, 1)
        stats["time_relearn"] = round(stats["time_relearn"] / 1000, 1)
        stats["time_filtered"] = round(stats["time_filtered"] / 1000, 1)
        result.append(stats)
    
    return result


def _read_existing_review_total(path):
    """Read the total review count from an existing JSON file (fail-open helper)."""
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("reviews", [])
        return sum(d.get("count", 0) for d in entries)
    except Exception:
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
    
    reviews = aggregate_reviews()
    
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

    output = {"reviews": reviews}
    
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
