#!/usr/bin/env python3
"""Upload public anonymized graph data to Cloudflare R2."""

import sys
from pathlib import Path

# Use the credentials loader from the main upload script
sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21/data/anki')
from importlib.machinery import SourceFileLoader

r2_utils = SourceFileLoader(
    "r2_utils", "/Users/lz/Library/Application Support/Anki2/addons21/data/anki/upload-to-r2"
).load_module()

BASE = Path('/Users/lz/Library/Application Support/Anki2/addons21')
PUBLIC_FILES = ['graph/graph_data_public.json', 'graph/history_data_public.json']


def upload_public_data():
    creds = r2_utils.load_credentials()
    if not creds['account_id'] or not creds['access_key']:
        print("❌ Error: R2 credentials not found.")
        sys.exit(1)

    print(f"🚀 Uploading public graph data to bucket: {creds['bucket']}")

    total_size = 0
    for rel_path in PUBLIC_FILES:
        path = BASE / rel_path
        if not path.exists():
            print(f"⚠️  Skipping {rel_path} (not found)")
            continue

        with open(path, 'rb') as f:
            content = f.read()

        # Upload as gzipped, but R2 client might handle it.
        # The main script uses gzip.compress(content)
        success, size = r2_utils.upload_to_r2(
            creds['bucket'],
            rel_path,  # Key matches path: graph/graph_data_public.json
            content,
            creds,
            verbose=True,
        )
        if success:
            total_size += size
        else:
            print(f"❌ Failed to upload {rel_path}")

    print(f"✅ Success! Total uploaded: {total_size/1024/1024:.1f} MB (compressed)")
    print("🌐 Data is now available at your R2 public endpoint under /graph/...")


if __name__ == "__main__":
    upload_public_data()
