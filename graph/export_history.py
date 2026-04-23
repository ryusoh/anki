#!/usr/bin/env python3
import json
import gzip
import os
from pathlib import Path
from datetime import datetime

BASE = Path('/Users/lz/Library/Application Support/Anki2/addons21')
NOTES_FILE = BASE / 'data/anki/notes.json.gz'
CARDS_FILE = BASE / 'data/anki/cards.json.gz'
REVIEWS_DIR = BASE / 'data/anki/reviews'
OUTPUT_FILE = BASE / 'graph/history_data.json'

def export_history():
    print("🚀 Loading mapping data...")
    
    # 1. Map guid -> nid
    guid_to_nid = {}
    with gzip.open(NOTES_FILE, 'rt') as f:
        notes = json.load(f)
        for n in notes:
            if 'guid' in n and 'id' in n:
                guid_to_nid[n['guid']] = n['id']
    
    # 2. Map nid -> guid (reverse)
    nid_to_guid = {nid: guid for guid, nid in guid_to_nid.items()}
    
    # 3. Map cid -> nid
    cid_to_nid = {}
    with gzip.open(CARDS_FILE, 'rt') as f:
        cards = json.load(f)
        for c in cards:
            if 'id' in c and 'nid' in c:
                cid_to_nid[c['id']] = c['nid']
                
    print(f"   Mapped {len(nid_to_guid)} notes and {len(cid_to_nid)} cards.")

    # 4. Process reviews
    history = {} # date_str -> set of guids
    
    review_files = sorted(list(REVIEWS_DIR.glob("*.json.gz")))
    print(f"   Processing {len(review_files)} review partitions...")
    
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

    # 5. Format for export
    sorted_dates = sorted(history.keys())
    # Convert sets to lists for JSON
    export_data = {
        "dates": sorted_dates,
        "history": {d: list(history[d]) for d in sorted_dates}
    }
    
    import sys
    is_public = '--public' in sys.argv
    if is_public:
        OUTPUT_FILE = BASE / 'graph/history_data_public.json'
        print("💡 Public Mode: Saving to history_data_public.json")

    print(f"💾 Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(export_data, f, separators=(',', ':'))
    print("✅ Done!")

if __name__ == "__main__":
    export_history()
