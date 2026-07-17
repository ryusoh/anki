#!/usr/bin/env python3
"""Audit the committed hash map against the live R2 bucket (read-only).

The hash map (data/cloudflare/hash_map.json) is the ledger of what has been
uploaded to R2; a poisoned entry claims an upload that never happened, and
incremental runs would silently skip the file forever. This tool lists the
bucket and reports every claim the bucket cannot back:

    make verify-r2        # or: python3 data/anki/verify-hash-map.py

Exit codes: 0 = consistent, 2 = poisoned entries found, 1 = cannot run.
Notes staged locally but absent from the map are fine (pending upload), and
map entries for locally-deleted notes are ignored (sync removes them on R2).
"""

import json
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STAGING_DIR = SCRIPT_DIR.parent / "cloudflare"
NOTE_SUFFIX = ".json.gz"


def _load_r2_utils():
    """Load the upload-to-r2 script as a module (it has no .py extension)."""
    loader = SourceFileLoader("r2_utils", str(SCRIPT_DIR / "upload-to-r2"))
    spec = spec_from_loader("r2_utils", loader)
    assert spec is not None
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


def audit(hash_map, staged_guids, r2_note_guids, r2_collection_keys):
    """Return (poisoned_note_guids, poisoned_collection_keys).

    Poisoned = the hash map claims it is uploaded, the source still exists
    locally, but the bucket has no such object.
    """
    map_collection = {k for k in hash_map if k.startswith("collection/")}
    map_guids = set(hash_map) - map_collection

    poisoned_notes = (map_guids & set(staged_guids)) - set(r2_note_guids)
    poisoned_collection = map_collection - set(r2_collection_keys)
    return poisoned_notes, poisoned_collection


def _list_bucket(client, bucket, prefix):
    keys = set()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.add(obj["Key"])
    return keys


def main():
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        print("❌ boto3 is required (pip install boto3)", file=sys.stderr)
        return 1

    hash_map_file = STAGING_DIR / "hash_map.json"
    if not hash_map_file.exists():
        print(f"❌ No hash map at {hash_map_file}", file=sys.stderr)
        return 1

    creds = _load_r2_utils().load_credentials()
    if not creds["account_id"] or not creds["access_key"]:
        print("❌ R2 credentials not found", file=sys.stderr)
        return 1

    client = boto3.client(
        "s3",
        endpoint_url=f"https://{creds['account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=creds["access_key"],
        aws_secret_access_key=creds["secret_key"],
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
    )

    hash_map = json.loads(hash_map_file.read_text())
    staged_guids = {
        p.name[: -len(NOTE_SUFFIX)] for p in (STAGING_DIR / "notes").glob(f"*{NOTE_SUFFIX}")
    }
    r2_note_guids = {
        k[len("notes/") : -len(NOTE_SUFFIX)] for k in _list_bucket(client, creds["bucket"], "notes/")
    }
    r2_collection = _list_bucket(client, creds["bucket"], "collection/")

    print(f"hash map: {len(hash_map):,} entries; staged notes: {len(staged_guids):,}")
    print(f"R2: {len(r2_note_guids):,} notes, {len(r2_collection)} collection files")

    poisoned_notes, poisoned_collection = audit(hash_map, staged_guids, r2_note_guids, r2_collection)

    if poisoned_notes or poisoned_collection:
        print("\n❌ POISONED entries (claimed uploaded, missing on R2):")
        for key in sorted(poisoned_collection):
            print(f"  - {key}")
        for guid in sorted(poisoned_notes)[:20]:
            print(f"  - notes/{guid}{NOTE_SUFFIX}")
        if len(poisoned_notes) > 20:
            print(f"  ... and {len(poisoned_notes) - 20:,} more notes")
        print("\nFix: delete these keys from data/cloudflare/hash_map.json and rerun")
        print("'make fetch-r2-skip-fetch', or restore the map from a known-good commit.")
        return 2

    print("\n✅ Hash map is consistent with R2 — every claimed upload exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
