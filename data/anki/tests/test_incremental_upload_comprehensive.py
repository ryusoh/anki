#!/usr/bin/env python3
"""
Comprehensive tests for incremental R2 upload logic.

Tests cover:
1. Hash computation for notes and collection files
2. Change detection (new, modified, unchanged)
3. Staging logic (only changed files)
4. Hash map persistence
5. Error handling (corrupted files, missing files)
6. Full workflow (fetch -> stage -> upload)
"""

import hashlib
import json
import gzip
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'graph'))

from hash_map import compute_note_hash, load_hash_map, save_hash_map, find_changed_notes, update_hash_map


# =============================================================================
# Test 1: Hash Computation
# =============================================================================

def test_note_hash_computation():
    """Test that note hashes are computed correctly and consistently."""
    print("\n📋 Test 1: Note Hash Computation")
    
    # Same note = same hash
    note1 = {'guid': 'abc123', 'flds': 'front\tback', 'tags': ['tag1'], 'mid': 123}
    note2 = {'guid': 'abc123', 'flds': 'front\tback', 'tags': ['tag1'], 'mid': 123}
    hash1 = compute_note_hash(note1)
    hash2 = compute_note_hash(note2)
    assert hash1 == hash2, "Same note should produce same hash"
    assert len(hash1) == 64, "Hash should be SHA256 (64 hex chars)"
    print("   ✓ Same note produces same hash")
    
    # Different field = different hash
    note_diff_flds = {'guid': 'abc123', 'flds': 'different\tback', 'tags': ['tag1'], 'mid': 123}
    hash_diff = compute_note_hash(note_diff_flds)
    assert hash1 != hash_diff, "Different fields should produce different hash"
    print("   ✓ Different fields produce different hash")
    
    # Different tags = different hash
    note_diff_tags = {'guid': 'abc123', 'flds': 'front\tback', 'tags': ['tag2'], 'mid': 123}
    hash_diff_tags = compute_note_hash(note_diff_tags)
    assert hash1 != hash_diff_tags, "Different tags should produce different hash"
    print("   ✓ Different tags produce different hash")
    
    # Different mid = different hash
    note_diff_mid = {'guid': 'abc123', 'flds': 'front\tback', 'tags': ['tag1'], 'mid': 456}
    hash_diff_mid = compute_note_hash(note_diff_mid)
    assert hash1 != hash_diff_mid, "Different mid should produce different hash"
    print("   ✓ Different mid produces different hash")
    
    # Same content, different guid = same hash (hash is based on content, not guid)
    note_diff_guid = {'guid': 'xyz789', 'flds': 'front\tback', 'tags': ['tag1'], 'mid': 123}
    hash_diff_guid = compute_note_hash(note_diff_guid)
    assert hash1 == hash_diff_guid, "Same content with different guid should produce same hash"
    print("   ✓ Same content with different guid produces same hash")
    
    # Empty fields handled
    note_empty = {'guid': 'empty', 'flds': '', 'tags': [], 'mid': 0}
    hash_empty = compute_note_hash(note_empty)
    assert len(hash_empty) == 64, "Empty note should still produce valid hash"
    print("   ✓ Empty note produces valid hash")
    
    print("   ✅ Note Hash Computation: PASSED")
    return True


def test_collection_file_hash():
    """Test collection file hash computation."""
    print("\n📋 Test 2: Collection File Hash Computation")
    
    def compute_file_hash(content):
        if isinstance(content, (dict, list)):
            content = json.dumps(content, sort_keys=True, ensure_ascii=False).encode('utf-8')
        elif isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    # Same content = same hash
    data1 = [{'id': 1, 'name': 'test'}]
    data2 = [{'id': 1, 'name': 'test'}]
    assert compute_file_hash(data1) == compute_file_hash(data2)
    print("   ✓ Same content produces same hash")
    
    # Different order = same hash (due to sort_keys)
    data3 = [{'name': 'test', 'id': 1}]
    assert compute_file_hash(data1) == compute_file_hash(data3)
    print("   ✓ Dict key order doesn't affect hash")
    
    # Different content = different hash
    data4 = [{'id': 2, 'name': 'test'}]
    assert compute_file_hash(data1) != compute_file_hash(data4)
    print("   ✓ Different content produces different hash")
    
    # Empty data
    empty_hash = compute_file_hash([])
    assert len(empty_hash) == 64
    print("   ✓ Empty list produces valid hash")
    
    print("   ✅ Collection File Hash Computation: PASSED")
    return True


# =============================================================================
# Test 2: Change Detection
# =============================================================================

def test_find_changed_notes():
    """Test detection of new, modified, and unchanged notes."""
    print("\n📋 Test 3: Find Changed Notes")
    
    old_notes = [
        {'guid': 'note1', 'flds': 'a\tb', 'tags': [], 'mid': 1},
        {'guid': 'note2', 'flds': 'c\td', 'tags': ['tag1'], 'mid': 2},
        {'guid': 'note3', 'flds': 'e\tf', 'tags': [], 'mid': 1},
    ]
    
    # Build old hash map
    old_hash_map = {}
    for note in old_notes:
        old_hash_map[note['guid']] = compute_note_hash(note)
    
    # Test 1: No changes
    current_same = [
        {'guid': 'note1', 'flds': 'a\tb', 'tags': [], 'mid': 1},
        {'guid': 'note2', 'flds': 'c\td', 'tags': ['tag1'], 'mid': 2},
        {'guid': 'note3', 'flds': 'e\tf', 'tags': [], 'mid': 1},
    ]
    changed, unchanged = find_changed_notes(current_same, old_hash_map)
    assert len(changed) == 0, "No changes should be detected"
    assert len(unchanged) == 3, "All notes should be unchanged"
    print("   ✓ No changes detected when content is same")
    
    # Test 2: Modified note
    current_modified = [
        {'guid': 'note1', 'flds': 'CHANGED\tb', 'tags': [], 'mid': 1},  # Changed
        {'guid': 'note2', 'flds': 'c\td', 'tags': ['tag1'], 'mid': 2},  # Same
        {'guid': 'note3', 'flds': 'e\tf', 'tags': [], 'mid': 1},  # Same
    ]
    changed, unchanged = find_changed_notes(current_modified, old_hash_map)
    assert len(changed) == 1, "One modified note should be detected"
    assert changed[0]['guid'] == 'note1'
    assert len(unchanged) == 2
    print("   ✓ Modified note detected")
    
    # Test 3: New note
    current_new = [
        {'guid': 'note1', 'flds': 'a\tb', 'tags': [], 'mid': 1},
        {'guid': 'note2', 'flds': 'c\td', 'tags': ['tag1'], 'mid': 2},
        {'guid': 'note3', 'flds': 'e\tf', 'tags': [], 'mid': 1},
        {'guid': 'note4', 'flds': 'g\th', 'tags': [], 'mid': 1},  # New
    ]
    changed, unchanged = find_changed_notes(current_new, old_hash_map)
    assert len(changed) == 1, "One new note should be detected"
    assert changed[0]['guid'] == 'note4'
    print("   ✓ New note detected")
    
    # Test 4: Deleted note (not in current)
    current_deleted = [
        {'guid': 'note1', 'flds': 'a\tb', 'tags': [], 'mid': 1},
        {'guid': 'note2', 'flds': 'c\td', 'tags': ['tag1'], 'mid': 2},
        # note3 deleted
    ]
    changed, unchanged = find_changed_notes(current_deleted, old_hash_map)
    assert len(changed) == 0, "Deleted note should not appear as changed"
    assert len(unchanged) == 2
    print("   ✓ Deleted note handled correctly")
    
    # Test 5: Multiple changes
    current_multi = [
        {'guid': 'note1', 'flds': 'CHANGED', 'tags': [], 'mid': 1},  # Modified
        {'guid': 'note2', 'flds': 'c\td', 'tags': ['tag1'], 'mid': 2},  # Same
        # note3 deleted
        {'guid': 'note4', 'flds': 'new', 'tags': [], 'mid': 1},  # New
        {'guid': 'note5', 'flds': 'new2', 'tags': [], 'mid': 1},  # New
    ]
    changed, unchanged = find_changed_notes(current_multi, old_hash_map)
    assert len(changed) == 3, "Should detect 3 changes (1 modified + 2 new)"
    print("   ✓ Multiple changes detected")
    
    print("   ✅ Find Changed Notes: PASSED")
    return True


def test_collection_file_change_detection():
    """Test detection of changed collection files."""
    print("\n📋 Test 4: Collection File Change Detection")
    
    def compute_file_hash(content):
        if isinstance(content, (dict, list)):
            content = json.dumps(content, sort_keys=True, ensure_ascii=False).encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    old_files = {
        "collection/notes.json.gz": compute_file_hash([{'guid': '1'}]),
        "collection/cards.json.gz": compute_file_hash([{'id': '1'}]),
        "collection/reviews.json.gz": compute_file_hash([{'cid': '1'}]),
    }
    
    # Test 1: No changes
    current_same = {
        "collection/notes.json.gz": compute_file_hash([{'guid': '1'}]),
        "collection/cards.json.gz": compute_file_hash([{'id': '1'}]),
        "collection/reviews.json.gz": compute_file_hash([{'cid': '1'}]),
    }
    changed = [k for k, h in current_same.items() if old_files.get(k) != h]
    assert len(changed) == 0
    print("   ✓ No changes detected")
    
    # Test 2: One file changed
    current_changed = {
        "collection/notes.json.gz": compute_file_hash([{'guid': '1'}, {'guid': '2'}]),  # Changed
        "collection/cards.json.gz": compute_file_hash([{'id': '1'}]),  # Same
        "collection/reviews.json.gz": compute_file_hash([{'cid': '1'}]),  # Same
    }
    changed = [k for k, h in current_changed.items() if old_files.get(k) != h]
    assert len(changed) == 1
    assert "collection/notes.json.gz" in changed
    print("   ✓ Changed file detected")
    
    # Test 3: New file
    current_new = dict(old_files)
    current_new["collection/decks.json"] = compute_file_hash([{'did': '1'}])
    changed = [k for k, h in current_new.items() if old_files.get(k) != h]
    assert "collection/decks.json" in changed
    print("   ✓ New file detected")
    
    print("   ✅ Collection File Change Detection: PASSED")
    return True


# =============================================================================
# Test 3: Hash Map Persistence
# =============================================================================

def test_hash_map_save_load():
    """Test hash map persistence."""
    print("\n📋 Test 5: Hash Map Save/Load")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        hash_file = Path(tmpdir) / "hash_map.json"
        
        # Save
        test_map = {
            'note1': 'hash1',
            'note2': 'hash2',
            'collection/notes.json.gz': 'collection_hash',
        }
        save_hash_map(test_map, hash_file)
        assert hash_file.exists()
        print("   ✓ Hash map saved")
        
        # Load
        loaded = load_hash_map(hash_file)
        assert loaded == test_map
        print("   ✓ Hash map loaded correctly")
        
        # Load non-existent file
        missing = load_hash_map(Path(tmpdir) / "missing.json")
        assert missing == {}
        print("   ✓ Missing file returns empty dict")
        
        # Load corrupted file
        corrupted = Path(tmpdir) / "corrupted.json"
        corrupted.write_text("not valid json{{{")
        corrupted_map = load_hash_map(corrupted)
        assert corrupted_map == {}
        print("   ✓ Corrupted file returns empty dict")
    
    print("   ✅ Hash Map Save/Load: PASSED")
    return True


def test_update_hash_map():
    """Test hash map update logic."""
    print("\n📋 Test 6: Update Hash Map")
    
    # Create notes and compute their actual hashes
    note1 = {'guid': 'note1', 'flds': 'a', 'tags': [], 'mid': 1}
    note2 = {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1}
    
    old_map = {
        'note1': compute_note_hash(note1),
        'note2': compute_note_hash(note2),
    }
    
    # Update with same notes (content unchanged)
    notes_same = [
        {'guid': 'note1', 'flds': 'a', 'tags': [], 'mid': 1},
        {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1},
    ]
    updated = update_hash_map(old_map, notes_same)
    assert updated['note1'] == old_map['note1'], "Unchanged note should have same hash"
    assert updated['note2'] == old_map['note2'], "Unchanged note should have same hash"
    print("   ✓ Unchanged notes preserve hashes")
    
    # Update with modified note
    notes_modified = [
        {'guid': 'note1', 'flds': 'CHANGED', 'tags': [], 'mid': 1},
        {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1},
    ]
    updated = update_hash_map(old_map, notes_modified)
    assert updated['note1'] != old_map['note1'], "Modified note should have new hash"
    assert updated['note2'] == old_map['note2'], "Unchanged note should preserve hash"
    print("   ✓ Modified note gets new hash")
    
    # Update with new note
    notes_new = [
        {'guid': 'note1', 'flds': 'a', 'tags': [], 'mid': 1},
        {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1},
        {'guid': 'note3', 'flds': 'c', 'tags': [], 'mid': 1},
    ]
    updated = update_hash_map(old_map, notes_new)
    assert 'note3' in updated, "New note should be added"
    assert len(updated) == 3, "Should have 3 notes"
    print("   ✓ New note added to hash map")
    
    print("   ✅ Update Hash Map: PASSED")
    return True


# =============================================================================
# Test 4: Error Handling
# =============================================================================

def test_corrupted_note_file_handling():
    """Test handling of corrupted note files."""
    print("\n📋 Test 7: Corrupted Note File Handling")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        notes_dir = Path(tmpdir) / "notes"
        notes_dir.mkdir()
        
        # Create a corrupted (empty) note file
        corrupted_file = notes_dir / "corrupted.json.gz"
        corrupted_file.write_bytes(b'')  # Empty file
        
        # Create a valid note file
        valid_file = notes_dir / "valid.json.gz"
        valid_note = {'guid': 'valid123', 'flds': 'test', 'tags': [], 'mid': 1}
        with gzip.open(valid_file, 'wt', encoding='utf-8') as f:
            json.dump(valid_note, f)
        
        # Try to read corrupted file
        errors = []
        success = []
        
        for note_file in notes_dir.glob("*.json.gz"):
            try:
                with gzip.open(note_file, 'rt', encoding='utf-8') as f:
                    content = f.read()
                    if not content:
                        raise ValueError("Empty file")
                    note = json.loads(content)
                    success.append(note_file.name)
            except Exception as e:
                errors.append((note_file.name, str(e)))
        
        assert len(errors) == 1, "Should detect 1 corrupted file"
        assert len(success) == 1, "Should read 1 valid file"
        print("   ✓ Corrupted file detected and reported")
        print("   ✓ Valid file read successfully")
        
        # Error should NOT be silently ignored
        assert errors[0][0] == "corrupted.json.gz"
        print(f"   ✓ Error reported: {errors[0][1]}")
    
    print("   ✅ Corrupted Note File Handling: PASSED")
    return True


def test_missing_collection_file_handling():
    """Test handling of missing collection files."""
    print("\n📋 Test 8: Missing Collection File Handling")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_dir = Path(tmpdir) / "collection"
        collection_dir.mkdir()
        
        # Create only some files
        (collection_dir / "notes.json.gz").write_bytes(gzip.compress(b'[]'))
        # cards.json.gz is missing
        
        # Check for missing files
        expected_files = [
            "collection/notes.json.gz",
            "collection/cards.json.gz",
        ]
        
        missing = []
        existing = []
        
        for key in expected_files:
            file_path = Path(tmpdir) / key
            if file_path.exists():
                existing.append(key)
            else:
                missing.append(key)
        
        assert "collection/cards.json.gz" in missing
        assert "collection/notes.json.gz" in existing
        print("   ✓ Missing file detected")
        print("   ✓ Existing file detected")
    
    print("   ✅ Missing Collection File Handling: PASSED")
    return True


def test_empty_hash_map_first_run():
    """Test behavior on first run (empty hash map)."""
    print("\n📋 Test 9: First Run (Empty Hash Map)")
    
    old_hash_map = {}
    
    notes = [
        {'guid': 'note1', 'flds': 'a', 'tags': [], 'mid': 1},
        {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1},
    ]
    
    changed, unchanged = find_changed_notes(notes, old_hash_map)
    
    assert len(changed) == 2, "All notes should be new on first run"
    assert len(unchanged) == 0
    print("   ✓ All notes detected as new on first run")
    
    # Collection files
    collection_files = {
        "collection/notes.json.gz": "hash1",
        "collection/cards.json.gz": "hash2",
    }
    
    changed_files = [k for k, h in collection_files.items() if old_hash_map.get(k) != h]
    assert len(changed_files) == 2, "All collection files should be new on first run"
    print("   ✓ All collection files detected as new on first run")
    
    print("   ✅ First Run: PASSED")
    return True


# =============================================================================
# Test 5: Full Workflow
# =============================================================================

def test_full_incremental_workflow():
    """Test complete incremental upload workflow."""
    print("\n📋 Test 10: Full Incremental Workflow")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        staging_dir = Path(tmpdir) / "staging"
        staging_dir.mkdir()
        hash_file = staging_dir / "hash_map.json"
        collection_dir = staging_dir / "collection"
        collection_dir.mkdir()
        notes_dir = staging_dir / "notes"
        notes_dir.mkdir()
        
        # First run - everything is new
        notes_run1 = [
            {'guid': 'note1', 'flds': 'a', 'tags': [], 'mid': 1},
            {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1},
        ]
        
        old_hash_map = load_hash_map(hash_file)
        changed, _ = find_changed_notes(notes_run1, old_hash_map)
        assert len(changed) == 2, "First run: all notes new"
        
        # Simulate staging
        for note in changed:
            guid_hash = hashlib.md5(note['guid'].encode()).hexdigest()[:16]
            note_file = notes_dir / f"{guid_hash}.json.gz"
            with gzip.open(note_file, 'wt', encoding='utf-8') as f:
                json.dump(note, f)
        
        # Save hash map
        new_hash_map = update_hash_map(old_hash_map, notes_run1)
        save_hash_map(new_hash_map, hash_file)
        print("   ✓ First run: staged 2 notes")
        
        # Second run - no changes
        notes_run2 = [
            {'guid': 'note1', 'flds': 'a', 'tags': [], 'mid': 1},
            {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1},
        ]
        
        old_hash_map = load_hash_map(hash_file)
        changed, unchanged = find_changed_notes(notes_run2, old_hash_map)
        assert len(changed) == 0, "Second run: no changes"
        assert len(unchanged) == 2
        print("   ✓ Second run: no changes detected")
        
        # Third run - one note modified
        notes_run3 = [
            {'guid': 'note1', 'flds': 'CHANGED', 'tags': [], 'mid': 1},
            {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1},
        ]
        
        old_hash_map = load_hash_map(hash_file)
        changed, unchanged = find_changed_notes(notes_run3, old_hash_map)
        assert len(changed) == 1, "Third run: one change"
        assert changed[0]['guid'] == 'note1'
        print("   ✓ Third run: modified note detected")
        
        # Fourth run - new note added
        notes_run4 = [
            {'guid': 'note1', 'flds': 'CHANGED', 'tags': [], 'mid': 1},
            {'guid': 'note2', 'flds': 'b', 'tags': [], 'mid': 1},
            {'guid': 'note3', 'flds': 'c', 'tags': [], 'mid': 1},
        ]
        
        old_hash_map = load_hash_map(hash_file)
        changed, unchanged = find_changed_notes(notes_run4, old_hash_map)
        assert len(changed) == 2, "Fourth run: modified + new"
        print("   ✓ Fourth run: modified + new notes detected")
    
    print("   ✅ Full Incremental Workflow: PASSED")
    return True


# =============================================================================
# Main Test Runner
# =============================================================================

def test_upload_only_checks_hash_map():
    """Test that --upload-only checks hash map and skips already uploaded files."""
    print("\n📋 Test 11: Upload-Only Checks Hash Map")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        staging_dir = Path(tmpdir) / "staging"
        staging_dir.mkdir()
        hash_file = staging_dir / "hash_map.json"
        collection_dir = staging_dir / "collection"
        collection_dir.mkdir()
        notes_dir = staging_dir / "notes"
        notes_dir.mkdir()
        
        # Create collection file
        notes_data = [{'guid': 'note1', 'flds': 'a', 'tags': [], 'mid': 1}]
        notes_file = collection_dir / "notes.json.gz"
        with gzip.open(notes_file, 'wt', encoding='utf-8') as f:
            json.dump(notes_data, f)
        
        # Create individual note
        note1_file = notes_dir / "abc123.json.gz"
        with gzip.open(note1_file, 'wt', encoding='utf-8') as f:
            json.dump(notes_data[0], f)
        
        # Hash map says everything is already uploaded
        old_hash_map = {
            'collection/notes.json.gz': hashlib.sha256(open(notes_file, 'rb').read()).hexdigest(),
            'note1': compute_note_hash(notes_data[0]),
        }
        save_hash_map(old_hash_map, hash_file)
        
        # Simulate --upload-only check
        def file_needs_upload(key, file_path):
            if not file_path.exists():
                return False, None
            with open(file_path, 'rb') as f:
                content = f.read()
            current_hash = hashlib.sha256(content).hexdigest()
            old_hash = old_hash_map.get(key)
            return old_hash is None or old_hash != current_hash, current_hash
        
        # Check collection file
        needs_upload, _ = file_needs_upload('collection/notes.json.gz', notes_file)
        assert not needs_upload, "Collection file should not need upload"
        print("   ✓ Collection file skipped (already uploaded)")
        
        # Check individual note
        needs_upload = old_hash_map.get('note1') != compute_note_hash(notes_data[0])
        assert not needs_upload, "Note should not need upload"
        print("   ✓ Individual note skipped (already uploaded)")
        
        # Now modify the note
        modified_data = [{'guid': 'note1', 'flds': 'CHANGED', 'tags': [], 'mid': 1}]
        with gzip.open(note1_file, 'wt', encoding='utf-8') as f:
            json.dump(modified_data[0], f)
        
        # Check again - should need upload now
        needs_upload = old_hash_map.get('note1') != compute_note_hash(modified_data[0])
        assert needs_upload, "Modified note should need upload"
        print("   ✓ Modified note detected for upload")
    
    print("   ✅ Upload-Only Checks Hash Map: PASSED")
    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("🧪 Comprehensive Incremental Upload Tests")
    print("=" * 70)
    
    tests = [
        ("Hash Computation", test_note_hash_computation),
        ("Collection File Hash", test_collection_file_hash),
        ("Find Changed Notes", test_find_changed_notes),
        ("Collection File Changes", test_collection_file_change_detection),
        ("Hash Map Save/Load", test_hash_map_save_load),
        ("Update Hash Map", test_update_hash_map),
        ("Corrupted File Handling", test_corrupted_note_file_handling),
        ("Missing File Handling", test_missing_collection_file_handling),
        ("First Run (Empty)", test_empty_hash_map_first_run),
        ("Full Workflow", test_full_incremental_workflow),
        ("Upload-Only Hash Check", test_upload_only_checks_hash_map),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"   ✗ FAILED: {e}")
            failed += 1
            errors.append((name, str(e)))
        except Exception as e:
            print(f"   ✗ ERROR: {type(e).__name__}: {e}")
            failed += 1
            errors.append((name, f"{type(e).__name__}: {e}"))
    
    print("\n" + "=" * 70)
    print(f"📊 Results: {passed}/{len(tests)} passed")
    print("=" * 70)
    
    if failed > 0:
        print(f"\n❌ {failed} test(s) failed:")
        for name, error in errors:
            print(f"   - {name}: {error}")
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED")
        return True


if __name__ == "__main__":
    run_all_tests()
