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
OUTPUT_FILE = SCRIPT_DIR.parent / "review_stats_data.json"


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
        stats["time"] += review.get("time", 0)
        
        # Count by maturity (ivl >= 21 = mature)
        if review.get("ivl", 0) >= 21:
            stats["mature"] += 1
        else:
            stats["young"] += 1
        
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
        elif rtype == 1:
            stats["review"] += 1
        elif rtype == 2:
            stats["relearn"] += 1
        elif rtype == 3:
            stats["filtered"] += 1
    
    # Convert to list and calculate retention
    result = []
    for date_str in sorted(daily_stats.keys()):
        stats = daily_stats[date_str]
        # Retention = (good + easy) / (again + hard + good + easy)
        total_answered = stats["again"] + stats["hard"] + stats["good"] + stats["easy"]
        retention = (stats["good"] + stats["easy"]) / total_answered if total_answered > 0 else 0
        stats["retention"] = round(retention, 4)
        stats["time"] = round(stats["time"] / 1000, 1)  # Convert to seconds
        result.append(stats)
    
    return result


def main():
    print("📊 Generating review stats from Anki data...")
    
    reviews = aggregate_reviews()
    
    if not reviews:
        print("   ❌ No review data found")
        return False
    
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
