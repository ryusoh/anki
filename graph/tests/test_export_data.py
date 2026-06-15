"""
Tests for graph.export_data module.

Tests fingerprint generation and incremental change detection,
particularly around deck merges where notes move between decks.
"""

import pytest

from graph.tests.fixtures import ALL_NOTES, BIOLOGY_NOTES, CALCULUS_NOTES, ENGLISH_NOTES


class TestNoteFingerprint:
    """Test note_fingerprint includes all relevant fields."""

    def test_fingerprint_changes_when_deck_changes(self):
        """Moving a note to a different deck must produce a different fingerprint."""
        from graph.export_data import note_fingerprint

        note_in_deck_a = {
            'guid': 'abc123',
            'mod': 1664855079,
            'flds': 'hello::world',
            'deck': 'Deck A',
        }
        note_in_deck_b = {
            **note_in_deck_a,
            'deck': 'Deck B',
        }

        fp_a = note_fingerprint(note_in_deck_a)
        fp_b = note_fingerprint(note_in_deck_b)
        assert fp_a != fp_b, (
            "Fingerprint must change when deck changes, "
            "otherwise deck-only moves are invisible to cache"
        )

    def test_fingerprint_stable_same_note(self):
        """Same note data should produce the same fingerprint."""
        from graph.export_data import note_fingerprint

        note = {
            'guid': 'abc123',
            'mod': 1664855079,
            'flds': 'hello::world',
            'deck': 'Deck A',
        }
        assert note_fingerprint(note) == note_fingerprint(note)


class TestFindChangedNotes:
    """Test find_changed_notes detects deck merges correctly."""

    def _make_cache(self, notes, output_file=None):
        """Build a cache dict from notes (mirrors save_cache structure)."""
        from graph.export_data import note_fingerprint

        deck_data = {}
        for note in notes:
            deck = note.get('deck', 'Unknown')
            if deck not in deck_data:
                deck_data[deck] = {}
            deck_data[deck][note['guid']] = note_fingerprint(note)

        cache = {
            'version': 4,
            'note_count': len(notes),
            'node_count': len(notes),
            'link_count': 0,
            'decks': deck_data,
        }
        if output_file:
            cache['output_file'] = output_file
        return cache

    def test_detects_deck_merge_via_grouping(self):
        """When notes move from deck A to deck B (content unchanged),
        find_changed_notes should detect changes."""
        from graph.export_data import find_changed_notes

        # Before merge: 3 decks
        old_notes = list(ALL_NOTES)
        cache = self._make_cache(old_notes)

        # After merge: move Biology notes into Calculus deck
        merged_notes = []
        for note in ALL_NOTES:
            if note['deck'] == 'Biology 101':
                merged_notes.append({**note, 'deck': 'Calculus'})
            else:
                merged_notes.append(note)

        changes = find_changed_notes(merged_notes, cache)

        # Should detect changes (not empty)
        assert changes is not None
        assert len(changes) > 0, "Deck merge must be detected as a change, " "not silently skipped"

    def test_deck_merge_identifies_moved_notes(self):
        """Merged notes should appear as new in target deck and removed from source."""
        from graph.export_data import find_changed_notes

        old_notes = list(ALL_NOTES)
        cache = self._make_cache(old_notes)

        # Move bio notes to Calculus
        merged_notes = []
        for note in ALL_NOTES:
            if note['deck'] == 'Biology 101':
                merged_notes.append({**note, 'deck': 'Calculus'})
            else:
                merged_notes.append(note)

        changes = find_changed_notes(merged_notes, cache)

        # Biology 101 should be detected as deleted
        assert 'Biology 101' in changes
        assert changes['Biology 101']['removed_guids'] == {'bio001', 'bio002'}

        # Calculus should show the moved notes as new
        assert 'Calculus' in changes
        assert {'bio001', 'bio002'}.issubset(changes['Calculus']['new_guids'])

    def test_cache_invalidated_for_different_output_file(self):
        """Cache built for private export should not be reused for public export."""
        from graph.export_data import find_changed_notes

        notes = list(ALL_NOTES)
        cache = self._make_cache(notes, output_file='graph_data.json')

        # Same notes, but different output target (public)
        changes = find_changed_notes(notes, cache, output_file='graph_data_public.json')

        # Should force rebuild (return None) since cache is for a different output
        assert changes is None, (
            "Cache for a different output file must be invalidated, "
            "otherwise public export reuses stale private cache"
        )

    def test_cache_valid_for_same_output_file(self):
        """Cache should be valid when output file matches."""
        from graph.export_data import find_changed_notes

        notes = list(ALL_NOTES)
        cache = self._make_cache(notes, output_file='graph_data.json')

        changes = find_changed_notes(notes, cache, output_file='graph_data.json')

        # No changes — same notes, same output
        assert changes is not None
        assert len(changes) == 0


class TestBuildGraphDeckMerge:
    """Test that build_graph correctly reflects merged deck structure."""

    def test_merged_deck_cluster_count(self):
        """After merging two decks, the graph should have fewer unique deck values."""
        from graph.builder import build_graph

        # Simulate deck merge: Biology notes moved to Calculus
        merged_notes = []
        for note in ALL_NOTES:
            if note['deck'] == 'Biology 101':
                merged_notes.append({**note, 'deck': 'Calculus'})
            else:
                merged_notes.append(note)

        G = build_graph(merged_notes)

        deck_values = {data['deck'] for _, data in G.nodes(data=True)}
        assert (
            len(deck_values) == 2
        ), f"Expected 2 decks after merge, got {len(deck_values)}: {deck_values}"
        assert 'Biology 101' not in deck_values
        assert 'English Vocabulary' in deck_values
        assert 'Calculus' in deck_values
