#!/usr/bin/env python3
"""Shared utilities for review partitioning."""

from datetime import datetime


def partition_reviews_by_month(reviews):
    """Return a dict mapping 'YYYY-MM' to the list of reviews for that month.

    Anki revlog ids are milliseconds since epoch.
    """
    reviews_by_month = {}
    for review in reviews:
        ts = review['id'] / 1000
        month_key = datetime.fromtimestamp(ts).strftime('%Y-%m')
        reviews_by_month.setdefault(month_key, []).append(review)
    return reviews_by_month
