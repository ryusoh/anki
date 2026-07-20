#!/usr/bin/env python3
"""Upload public anonymized graph data to Cloudflare R2."""

import hashlib
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

# Use the credentials loader from the main upload script.
# When this script runs inside Anki, the repo is symlinked to the add-ons folder,
# so resolving relative to __file__ works in both the repo checkout and Anki.
REPO_ROOT = Path(__file__).resolve().parents[1]
R2_SCRIPT = REPO_ROOT / 'data' / 'anki' / 'upload-to-r2'
sys.path.insert(0, str(R2_SCRIPT.parent))

r2_utils = SourceFileLoader('r2_utils', str(R2_SCRIPT)).load_module()

BASE = REPO_ROOT
PUBLIC_FILES = ['graph/graph_data_public.json', 'graph/history_data_public.json']
HASH_MAP_FILE = BASE / 'data' / 'cloudflare' / 'hash_map.json'

# graph/hash_map.py lives in the graph package; add it to the path.
sys.path.insert(0, str(BASE / 'graph'))
from hash_map import load_hash_map, save_hash_map  # noqa: E402


def upload_public_data():
    creds = r2_utils.load_credentials()
    if not creds['account_id'] or not creds['access_key']:
        print("❌ Error: R2 credentials not found.")
        sys.exit(1)

    print(f"🚀 Uploading public graph data to bucket: {creds['bucket']}")

    hash_map = load_hash_map(HASH_MAP_FILE)
    total_size = 0
    uploaded = 0
    skipped = 0
    updated = False

    for rel_path in PUBLIC_FILES:
        path = BASE / rel_path
        if not path.exists():
            print(f"⚠️  Skipping {rel_path} (not found)")
            continue

        with open(path, 'rb') as f:
            content = f.read()

        # Hash raw JSON bytes. Do NOT hash gzip-compressed bytes:
        # gzip.compress() embeds the current timestamp, so compressed bytes
        # differ every run even when the underlying JSON is identical.
        content_hash = hashlib.sha256(content).hexdigest()
        if hash_map.get(rel_path) == content_hash:
            print(f"   ⊘ {rel_path} unchanged — skipping upload")
            skipped += 1
            continue

        success, size = r2_utils.upload_to_r2(
            creds['bucket'],
            rel_path,  # Key matches path: graph/graph_data_public.json
            content,
            creds,
            verbose=True,
        )
        if success:
            print(f"  ✓ Uploaded {rel_path} ({size:,} bytes)")
            total_size += size
            uploaded += 1
            hash_map[rel_path] = content_hash
            updated = True
        else:
            print(f"❌ Failed to upload {rel_path}")

    if updated:
        save_hash_map(hash_map, HASH_MAP_FILE)

    print(
        f"✅ Success! Uploaded {uploaded}, skipped {skipped}, total {total_size/1024/1024:.1f} MB (compressed)"
    )
    print("🌐 Data is now available at your R2 public endpoint under /graph/...")


if __name__ == "__main__":
    upload_public_data()
