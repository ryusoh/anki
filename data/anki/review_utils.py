#!/usr/bin/env python3
"""Shared utilities for review partitioning."""

from datetime import datetime


def partition_reviews_by_month(reviews):
    """Return a dict mapping 'YYYY-MM' to the list of reviews for that month.

    Anki revlog ids are milliseconds since epoch.
    """
    reviews_by_month = {}

    # Bolt: Cache datetime formatting per day to avoid O(N) datetime allocations
    # and string formatting overhead for every single review.
    month_cache = {}

    for review in reviews:
        # Get day index for O(1) cache lookup
        day_idx = review['id'] // 86400000

        if day_idx not in month_cache:
            month_cache[day_idx] = datetime.fromtimestamp(review['id'] / 1000).strftime('%Y-%m')

        month_key = month_cache[day_idx]

        # Avoid .setdefault() overhead
        if month_key not in reviews_by_month:
            reviews_by_month[month_key] = []
        reviews_by_month[month_key].append(review)

    return reviews_by_month
