#!/usr/bin/env python3
"""
Regression test: `upload-to-r2 --upload-only` must compare the same content
hash that `fetch` computes when staging collection files.

`fetch` stages `collection/reviews/YYYY-MM.json.gz` only when the month's JSON
content changed, but the uploader used to hash the raw gzip bytes both when
deciding what to upload and when updating hash_map.json. The stager's content
hash never matched the stored bytes hash, so every daily sync re-staged and
re-uploaded every historical month.
"""

import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

_loader = SourceFileLoader(
    'upload_to_r2_content_hash_mod', str(SCRIPT_DIR.parent / 'upload-to-r2')
)
_spec = importlib.util.spec_from_loader('upload_to_r2_content_hash_mod', _loader)
r2 = importlib.util.module_from_spec(_spec)
_loader.exec_module(r2)

_fetch_loader = SourceFileLoader('fetch', str(SCRIPT_DIR.parent / 'fetch'))
_fetch_spec = importlib.util.spec_from_loader('fetch', _fetch_loader)
fetch = importlib.util.module_from_spec(_fetch_spec)
_fetch_loader.exec_module(fetch)

CREDS = {'account_id': 'acct', 'access_key': 'ak', 'secret_key': 'sk', 'bucket': 'b'}

JAN_ID = 1609459200000  # 2021-01-01 00:00:00 UTC
FEB_ID = 1612137600000  # 2021-02-01 00:00:00 UTC


def _make_review(review_id, cid=1):
    """Return a minimal review dict; id is milliseconds since epoch."""
    return {'id': review_id, 'cid': cid, 'ease': 3, 'ivl': 1,
            'lastIvl': 0, 'factor': 0, 'time': 0, 'type': 0}


def _month_key(review_id):
    return sorted(fetch.partition_reviews_by_month([_make_review(review_id)]))[0]


def _stage(staging, reviews, old_hash_map):
    """Stage collection files the way `fetch --stage-r2` does."""
    data = {'reviews': reviews, 'cards': [], 'decks': {}, 'notetypes': []}
    _, hashes = fetch._stage_collection_files(
        data, [], staging / 'collection', old_hash_map, verbose=False
    )
    return hashes


def _run_upload_only(staging, monkeypatch, upload):
    monkeypatch.setattr(r2, 'get_staging_dir', lambda: staging)
    monkeypatch.setattr(r2, 'load_credentials', lambda: dict(CREDS))
    monkeypatch.setattr(r2, 'upload_to_r2', upload)
    monkeypatch.setattr(sys, 'argv', ['upload-to-r2', '--upload-only'])
    r2.main()


def test_unchanged_months_are_not_reuploaded(tmp_path, monkeypatch):
    """A hash map populated by `fetch` hashes means nothing needs upload."""
    staging = tmp_path
    (staging / 'collection').mkdir()

    reviews = [_make_review(JAN_ID, cid=1), _make_review(FEB_ID, cid=2)]
    hashes = _stage(staging, reviews, {})
    (staging / 'hash_map.json').write_text(json.dumps(hashes))

    attempted = []
    _run_upload_only(
        staging, monkeypatch,
        lambda *a, **k: (attempted.append(a[1]) or (True, 1)),
    )

    assert attempted == []


def test_only_new_month_is_uploaded(tmp_path, monkeypatch):
    """A new daily review re-uploads only its own month's file end to end."""
    staging = tmp_path
    (staging / 'collection').mkdir()

    reviews = [_make_review(JAN_ID, cid=1), _make_review(FEB_ID, cid=2)]
    old_hashes = _stage(staging, reviews, {})

    # Next day: one more review lands in February.
    new_reviews = reviews + [_make_review(FEB_ID + 86400000, cid=3)]
    _stage(staging, new_reviews, old_hashes)
    (staging / 'hash_map.json').write_text(json.dumps(old_hashes))

    attempted = []
    _run_upload_only(
        staging, monkeypatch,
        lambda *a, **k: (attempted.append(a[1]) or (True, 1)),
    )

    assert attempted == [f'collection/reviews/{_month_key(FEB_ID)}.json.gz']


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, '-v']))
