#!/usr/bin/env python3
"""Tests for the hash-map-vs-R2 audit logic (data/anki/verify-hash-map.py)."""

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / 'verify-hash-map.py'

_loader = SourceFileLoader('verify_hash_map_mod', str(SCRIPT))
_spec = importlib.util.spec_from_loader('verify_hash_map_mod', _loader)
vh = importlib.util.module_from_spec(_spec)
_loader.exec_module(vh)


def test_consistent_map_reports_nothing():
    hash_map = {'g1': 'h', 'g2': 'h', 'collection/notes.json.gz': 'h'}
    notes, coll = vh.audit(
        hash_map,
        staged_guids={'g1', 'g2'},
        r2_note_guids={'g1', 'g2'},
        r2_collection_keys={'collection/notes.json.gz'},
    )
    assert notes == set() and coll == set()


def test_claimed_but_missing_upload_is_poisoned():
    hash_map = {'g1': 'h', 'g2': 'h', 'collection/notes.json.gz': 'h'}
    notes, coll = vh.audit(
        hash_map,
        staged_guids={'g1', 'g2'},
        r2_note_guids={'g1'},  # g2 claimed by the map but absent on R2
        r2_collection_keys=set(),  # collection file claimed but absent
    )
    assert notes == {'g2'}
    assert coll == {'collection/notes.json.gz'}


def test_locally_deleted_notes_are_not_flagged():
    # g9 is in the map but no longer staged locally: sync deletes it from
    # R2, so its absence from the bucket is expected, not poison.
    notes, _ = vh.audit(
        {'g9': 'h'}, staged_guids=set(), r2_note_guids=set(), r2_collection_keys=set()
    )
    assert notes == set()


def test_pending_uploads_are_not_flagged():
    # Staged + on R2 from an old upload, but newer hash not yet in the map —
    # that's a pending upload, not an inconsistency.
    notes, _ = vh.audit(
        {}, staged_guids={'g1'}, r2_note_guids=set(), r2_collection_keys=set()
    )
    assert notes == set()
