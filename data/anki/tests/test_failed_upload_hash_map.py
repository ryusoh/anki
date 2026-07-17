#!/usr/bin/env python3
"""
Failed uploads must NOT be recorded in the hash map: a run that fails to
push a file has to retry it next time, not silently mark it as uploaded.
Regression test for the 2026-07-17 incident where a dead proxy failed all
504 uploads and a completed run would have marked them all as current.
"""

import gzip
import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPT_DIR = Path(__file__).parent
SCRIPT = SCRIPT_DIR.parent / 'upload-to-r2'

_loader = SourceFileLoader('upload_to_r2_hashmap_mod', str(SCRIPT))
_spec = importlib.util.spec_from_loader('upload_to_r2_hashmap_mod', _loader)
r2 = importlib.util.module_from_spec(_spec)
_loader.exec_module(r2)

CREDS = {'account_id': 'acct', 'access_key': 'ak', 'secret_key': 'sk', 'bucket': 'b'}
FAILING_KEY = 'collection/cards.json.gz'


@pytest.fixture
def staging(tmp_path):
    """Minimal staging dir: two collection files and one staged note."""
    (tmp_path / 'collection').mkdir()
    (tmp_path / 'collection' / 'notes.json.gz').write_bytes(gzip.compress(b'{"n": 1}'))
    (tmp_path / 'collection' / 'cards.json.gz').write_bytes(gzip.compress(b'{"c": 1}'))
    notes_dir = tmp_path / 'notes'
    notes_dir.mkdir()
    note = {'guid': 'g1', 'flds': 'front\x1fback', 'tags': ''}
    with gzip.open(notes_dir / 'g1.json.gz', 'wt', encoding='utf-8') as f:
        json.dump(note, f)
    (tmp_path / 'hash_map.json').write_text('{}')
    return tmp_path


def fake_upload(bucket, key, data, creds, verbose=False, quiet=False, **kwargs):
    return key != FAILING_KEY, 123


def test_upload_only_keeps_failed_files_out_of_hash_map(staging, monkeypatch):
    monkeypatch.setattr(r2, 'get_staging_dir', lambda: staging)
    monkeypatch.setattr(r2, 'load_credentials', lambda: dict(CREDS))
    monkeypatch.setattr(r2, 'upload_to_r2', fake_upload)
    monkeypatch.setattr(sys, 'argv', ['upload-to-r2', '--upload-only'])

    r2.main()

    hash_map = json.loads((staging / 'hash_map.json').read_text())
    assert 'collection/notes.json.gz' in hash_map  # succeeded -> recorded
    assert 'g1' in hash_map  # succeeded -> recorded
    assert FAILING_KEY not in hash_map  # failed -> must be retried next run


def test_rerun_retries_only_the_failed_file(staging, monkeypatch, capsys):
    monkeypatch.setattr(r2, 'get_staging_dir', lambda: staging)
    monkeypatch.setattr(r2, 'load_credentials', lambda: dict(CREDS))
    monkeypatch.setattr(r2, 'upload_to_r2', fake_upload)
    monkeypatch.setattr(sys, 'argv', ['upload-to-r2', '--upload-only'])
    r2.main()

    attempted = []

    def recording_upload(bucket, key, data, creds, verbose=False, quiet=False, **kwargs):
        attempted.append(key)
        return True, 123

    monkeypatch.setattr(r2, 'upload_to_r2', recording_upload)
    r2.main()

    assert attempted == [FAILING_KEY]


def test_upload_from_staging_returns_failed_keys(staging, monkeypatch):
    monkeypatch.setattr(r2, 'upload_to_r2', fake_upload)
    failed = r2.upload_from_staging(staging, dict(CREDS), verbose=False, notes_count=1)
    assert failed == {FAILING_KEY}
