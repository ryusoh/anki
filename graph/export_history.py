#!/usr/bin/env python3
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

# Allow running this script directly (python3 graph/export_history.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graph._paths import ANKI_ADDONS_DIR

BASE = ANKI_ADDONS_DIR
NOTES_FILE = BASE / 'data/anki/notes.json.gz'
CARDS_FILE = BASE / 'data/anki/cards.json.gz'
REVIEWS_DIR = BASE / 'data/anki/reviews'
OUTPUT_FILE = BASE / 'graph/history_data.json'


def _load_guid_nid_mapping():
    guid_to_nid = {}
    with gzip.open(NOTES_FILE, 'rt') as f:
        notes = json.load(f)
        for n in notes:
            if 'guid' in n and 'id' in n:
                guid_to_nid[n['guid']] = n['id']
    return guid_to_nid


def _load_cid_nid_mapping():
    cid_to_nid = {}
    with gzip.open(CARDS_FILE, 'rt') as f:
        cards = json.load(f)
        for c in cards:
            if 'id' in c and 'nid' in c:
                cid_to_nid[c['id']] = c['nid']
    return cid_to_nid


def _process_reviews(review_files, cid_to_nid, nid_to_guid):
    history = {}
    for rf in review_files:
        with gzip.open(rf, 'rt') as f:
            reviews = json.load(f)
            for rev in reviews:
                cid = rev['cid']
                ts = rev['id'] / 1000
                dt = datetime.fromtimestamp(ts)
                date_str = dt.strftime('%Y-%m-%d')
                nid = cid_to_nid.get(cid)
                if nid:
                    guid = nid_to_guid.get(nid)
                    if guid:
                        if date_str not in history:
                            history[date_str] = set()
                        history[date_str].add(guid)
        print(f"\r     Completed {rf.name}", end="")
    print("\n   Processing complete.")
    return history


def export_history():
    print("🚀 Loading mapping data...")
    guid_to_nid = _load_guid_nid_mapping()
    nid_to_guid = {nid: guid for guid, nid in guid_to_nid.items()}
    cid_to_nid = _load_cid_nid_mapping()

    print(f"   Mapped {len(nid_to_guid)} notes and {len(cid_to_nid)} cards.")

    review_files = sorted(list(REVIEWS_DIR.glob("*.json.gz")))
    print(f"   Processing {len(review_files)} review partitions...")

    history = _process_reviews(review_files, cid_to_nid, nid_to_guid)

    sorted_dates = sorted(history.keys())
    export_data = {"dates": sorted_dates, "history": {d: list(history[d]) for d in sorted_dates}}

    import sys

    is_public = '--public' in sys.argv
    if is_public:
        OUTPUT_FILE = BASE / 'graph/history_data_public.json'
        print("💡 Public Mode: Saving to history_data_public.json")
    else:
        OUTPUT_FILE = BASE / 'graph/history_data.json'

    print(f"💾 Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(export_data, f, separators=(',', ':'))
    print("✅ Done!")


if __name__ == "__main__":
    export_history()
