"""
Tests for graph.hash_map module.

Tests content hashing and incremental staging.
"""

import pytest
import hashlib
import json
from pathlib import Path


class TestComputeNoteHash:
    """Test content hash computation for notes."""
    
    def test_hash_from_fields(self):
        """Test hashing note content."""
        from graph.hash_map import compute_note_hash
        
        note = {
            'guid': 'test123',
            'flds': 'front::back::extra',
            'tags': 'tag1 tag2',
            'mid': 123456,
        }
        
        hash1 = compute_note_hash(note)
        
        # Hash should be a SHA256 hex string (64 chars)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
    
    def test_same_content_same_hash(self):
        """Test that identical content produces same hash."""
        from graph.hash_map import compute_note_hash
        
        note1 = {
            'guid': 'test1',
            'flds': 'front::back',
            'tags': 'tag1',
            'mid': 123456,
        }
        
        note2 = {
            'guid': 'test2',  # Different GUID
            'flds': 'front::back',
            'tags': 'tag1',
            'mid': 123456,
        }
        
        # Same content should produce same hash (GUID not included)
        assert compute_note_hash(note1) == compute_note_hash(note2)
    
    def test_different_content_different_hash(self):
        """Test that different content produces different hash."""
        from graph.hash_map import compute_note_hash
        
        note1 = {
            'guid': 'test1',
            'flds': 'front::back',
            'tags': 'tag1',
            'mid': 123456,
        }
        
        note2 = {
            'guid': 'test1',
            'flds': 'front::different',  # Changed
            'tags': 'tag1',
            'mid': 123456,
        }
        
        assert compute_note_hash(note1) != compute_note_hash(note2)
    
    def test_hash_includes_all_fields(self):
        """Test that hash includes flds, tags, and mid."""
        from graph.hash_map import compute_note_hash
        
        base_note = {
            'guid': 'test1',
            'flds': 'front::back',
            'tags': 'tag1',
            'mid': 123456,
        }
        
        # Change flds
        note_flds = dict(base_note)
        note_flds['flds'] = 'different::back'
        assert compute_note_hash(base_note) != compute_note_hash(note_flds)
        
        # Change tags
        note_tags = dict(base_note)
        note_tags['tags'] = 'different'
        assert compute_note_hash(base_note) != compute_note_hash(note_tags)
        
        # Change mid
        note_mid = dict(base_note)
        note_mid['mid'] = 999999
        assert compute_note_hash(base_note) != compute_note_hash(note_mid)


class TestHashMap:
    """Test hash map loading and saving."""
    
    def test_create_empty_hash_map(self):
        """Test creating empty hash map."""
        from graph.hash_map import create_hash_map
        
        hash_map = create_hash_map()
        
        assert hash_map == {}
        assert isinstance(hash_map, dict)
    
    def test_load_hash_map_from_file(self, tmp_path):
        """Test loading hash map from file."""
        from graph.hash_map import load_hash_map, save_hash_map
        
        # Create test hash map
        test_map = {
            'guid1': 'abc123',
            'guid2': 'def456',
        }
        
        hash_map_file = tmp_path / "hash_map.json"
        save_hash_map(test_map, hash_map_file)
        
        # Load it back
        loaded = load_hash_map(hash_map_file)
        
        assert loaded == test_map
    
    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file returns empty dict."""
        from graph.hash_map import load_hash_map
        
        hash_map_file = tmp_path / "nonexistent.json"
        loaded = load_hash_map(hash_map_file)
        
        assert loaded == {}
    
    def test_save_hash_map(self, tmp_path):
        """Test saving hash map to file."""
        from graph.hash_map import save_hash_map
        import json
        
        test_map = {
            'guid1': 'abc123',
            'guid2': 'def456',
        }
        
        hash_map_file = tmp_path / "hash_map.json"
        save_hash_map(test_map, hash_map_file)
        
        # Verify file exists and content
        assert hash_map_file.exists()
        
        with open(hash_map_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded == test_map


class TestFindChangedNotes:
    """Test finding notes that changed."""
    
    def test_all_new_notes(self):
        """Test when all notes are new."""
        from graph.hash_map import find_changed_notes
        
        old_map = {}
        new_notes = [
            {'guid': 'new1', 'flds': 'front', 'tags': 'tag', 'mid': 123},
            {'guid': 'new2', 'flds': 'front', 'tags': 'tag', 'mid': 123},
        ]
        
        changed, unchanged = find_changed_notes(new_notes, old_map)
        
        assert len(changed) == 2
        assert len(unchanged) == 0
        assert set(n['guid'] for n in changed) == {'new1', 'new2'}
    
    def test_all_unchanged_notes(self):
        """Test when no notes changed."""
        from graph.hash_map import find_changed_notes, compute_note_hash
        
        note1 = {'guid': 'n1', 'flds': 'front', 'tags': 'tag', 'mid': 123}
        note2 = {'guid': 'n2', 'flds': 'front', 'tags': 'tag', 'mid': 123}
        
        old_map = {
            'n1': compute_note_hash(note1),
            'n2': compute_note_hash(note2),
        }
        
        new_notes = [note1, note2]
        
        changed, unchanged = find_changed_notes(new_notes, old_map)
        
        assert len(changed) == 0
        assert len(unchanged) == 2
    
    def test_mixed_changed_unchanged(self):
        """Test mix of changed and unchanged notes."""
        from graph.hash_map import find_changed_notes, compute_note_hash
        
        note1 = {'guid': 'n1', 'flds': 'front', 'tags': 'tag', 'mid': 123}
        note2 = {'guid': 'n2', 'flds': 'changed', 'tags': 'tag', 'mid': 123}
        
        old_map = {
            'n1': compute_note_hash(note1),
            'n2': 'old_different_hash',  # Will be different
        }
        
        new_notes = [note1, note2]
        
        changed, unchanged = find_changed_notes(new_notes, old_map)
        
        assert len(changed) == 1
        assert len(unchanged) == 1
        assert changed[0]['guid'] == 'n2'
        assert unchanged[0]['guid'] == 'n1'
    
    def test_deleted_notes_not_in_unchanged(self):
        """Test that deleted notes are not in unchanged list."""
        from graph.hash_map import find_changed_notes, compute_note_hash
        
        note1 = {'guid': 'n1', 'flds': 'front', 'tags': 'tag', 'mid': 123}
        
        old_map = {
            'n1': compute_note_hash(note1),
            'deleted': 'some_hash',  # This note was deleted
        }
        
        new_notes = [note1]
        
        changed, unchanged = find_changed_notes(new_notes, old_map)
        
        # Deleted note should not appear in either list
        assert len(changed) == 0
        assert len(unchanged) == 1
        assert unchanged[0]['guid'] == 'n1'


class TestUpdateHashMap:
    """Test updating hash map with new notes."""
    
    def test_add_new_notes_to_map(self):
        """Test adding new notes to hash map."""
        from graph.hash_map import update_hash_map, compute_note_hash
        
        old_map = {
            'existing': 'existing_hash',
        }
        
        new_notes = [
            {'guid': 'new1', 'flds': 'front', 'tags': 'tag', 'mid': 123},
        ]
        
        updated = update_hash_map(old_map, new_notes)
        
        assert 'existing' in updated
        assert 'new1' in updated
        assert updated['new1'] == compute_note_hash(new_notes[0])
    
    def test_update_changed_notes(self):
        """Test updating hash for changed notes."""
        from graph.hash_map import update_hash_map, compute_note_hash
        
        old_map = {
            'changed': 'old_hash',
        }
        
        new_notes = [
            {'guid': 'changed', 'flds': 'new', 'tags': 'tag', 'mid': 123},
        ]
        
        updated = update_hash_map(old_map, new_notes)
        
        assert updated['changed'] != 'old_hash'
        assert updated['changed'] == compute_note_hash(new_notes[0])

def test_load_hash_map_invalid_json(tmp_path):
    from graph.hash_map import load_hash_map

    hash_map_file = tmp_path / "invalid.json"
    with open(hash_map_file, "w") as f:
        f.write("{invalid json")

    assert load_hash_map(hash_map_file) == {}

def test_find_changed_notes_no_guid():
    from graph.hash_map import find_changed_notes
    notes = [{"flds": "test", "tags": "test", "mid": 123}]
    changed, unchanged = find_changed_notes(notes, {})
    assert changed == []
    assert unchanged == []

def test_update_hash_map_no_guid():
    from graph.hash_map import update_hash_map
    notes = [{"flds": "test", "tags": "test", "mid": 123}]
    updated = update_hash_map({"existing": "hash"}, notes)
    assert updated == {"existing": "hash"}
