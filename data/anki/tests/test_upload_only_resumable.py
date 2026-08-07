#!/usr/bin/env python3
"""
A killed `--upload-only` run (e.g. the precommit-fix network deadline) must
keep its progress: the hash map is saved periodically during the note loop,
so the next run only uploads the notes that never completed. Regression test
for the 2026-08-08 incident where 46k changed notes could never finish within
the deadline because the map was only saved after the final note.
"""

import gzip
import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent
SCRIPT = SCRIPT_DIR.parent / 'upload-to-r2'

_loader = SourceFileLoader('upload_to_r2_resumable_mod', str(SCRIPT))
_spec = importlib.util.spec_from_loader('upload_to_r2_resumable_mod', _loader)
r2 = importlib.util.module_from_spec(_spec)
_loader.exec_module(r2)

CREDS = {'account_id': 'acct', 'access_key': 'ak', 'secret_key': 'sk', 'bucket': 'b'}
NOTE_GUIDS = [f'g{i}' for i in range(5)]


@pytest.fixture
def staging(tmp_path):
    """Staging dir with five staged notes and an empty hash map."""
    (tmp_path / 'collection').mkdir()
    (tmp_path / 'collection' / 'notes.json.gz').write_bytes(gzip.compress(b'{"n": 1}'))
    notes_dir = tmp_path / 'notes'
    notes_dir.mkdir()
    for guid in NOTE_GUIDS:
        note = {'guid': guid, 'flds': 'front\x1fback', 'tags': ''}
        with gzip.open(notes_dir / f'{guid}.json.gz', 'wt', encoding='utf-8') as f:
            json.dump(note, f)
    (tmp_path / 'hash_map.json').write_text('{}')
    return tmp_path


def _run_upload_only(staging, monkeypatch, upload):
    monkeypatch.setattr(r2, 'get_staging_dir', lambda: staging)
    monkeypatch.setattr(r2, 'load_credentials', lambda: dict(CREDS))
    monkeypatch.setattr(r2, 'upload_to_r2', upload)
    # Serial workers + tiny save interval make the mid-run state deterministic.
    monkeypatch.setattr(r2, 'MAX_UPLOAD_WORKERS', 1)
    monkeypatch.setattr(r2, 'HASH_MAP_SAVE_INTERVAL', 2)
    monkeypatch.setattr(sys, 'argv', ['upload-to-r2', '--upload-only'])
    r2.main()


def test_killed_run_keeps_progress_and_rerun_resumes(staging, monkeypatch):
    calls = []

    def upload_then_die(bucket, key, data, creds, verbose=False, quiet=False, **kwargs):
        calls.append(key)
        if len(calls) >= 4:  # 1 collection file + 2 notes succeed, then the kill
            raise KeyboardInterrupt('deadline')
        return True, 123

    with pytest.raises(KeyboardInterrupt):
        _run_upload_only(staging, monkeypatch, upload_then_die)

    saved = json.loads((staging / 'hash_map.json').read_text())
    saved_notes = {k for k in saved if k in NOTE_GUIDS}
    assert len(saved_notes) == 2  # periodic save ran before the kill

    attempted = []

    def recording_upload(bucket, key, data, creds, verbose=False, quiet=False, **kwargs):
        attempted.append(key)
        return True, 123

    _run_upload_only(staging, monkeypatch, recording_upload)

    retried_notes = {k[len('notes/'):-len('.json.gz')] for k in attempted if k.startswith('notes/')}
    # Note filenames match their guids in this fixture, so stems are guids.
    assert retried_notes == set(NOTE_GUIDS) - saved_notes
