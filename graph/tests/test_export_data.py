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


from unittest.mock import patch


class TestExportDataUtils:
    def test_strip_html(self):
        from graph.export_data import strip_html

        # Base case None/empty
        assert strip_html(None) == ''
        assert strip_html('') == ''

        # HTML tag stripping
        assert strip_html('<b>bold</b>') == 'bold'
        assert strip_html('<div class="x">text</div>') == 'text'

        # Entities
        assert strip_html('a&nbsp;b') == 'a b'
        assert strip_html('a&amp;b') == 'a&b'
        assert strip_html('a&lt;b') == 'a<b'
        assert strip_html('a&gt;b') == 'a>b'
        assert strip_html('a&quot;b') == 'a"b'
        assert strip_html('a&#39;b') == "a'b"
        assert strip_html('a&apos;b') == "a'b"

        # Replacements
        assert strip_html('a::b') == 'a b'
        assert strip_html('a\nb') == 'a b'

        # Truncation and extra spaces
        long_str = 'a   b   c ' * 10
        res = strip_html(long_str)
        assert res == ('a b c ' * 10).strip()[:60]
        assert len(res) <= 60

    def test_progress_bar(self, capsys):
        import sys

        from graph.export_data import progress_bar

        with patch.object(sys.stderr, 'write') as mock_write:
            progress_bar(50, 100, prefix="Test")
            mock_write.assert_called()

            # Check 100% newline
            progress_bar(100, 100, prefix="Test")
            mock_write.assert_any_call('\n')

        with patch.object(sys.stderr, 'write') as mock_write:
            progress_bar(10, 0, prefix="DivZero")
            # total=0 => pct=1 => bar filled
            mock_write.assert_called()

    def test_load_cache_no_file(self):
        from graph.export_data import load_cache

        with patch('pathlib.Path.exists', return_value=False):
            assert load_cache() is None

    def test_load_cache_success(self):
        from unittest.mock import mock_open

        from graph.export_data import load_cache

        mock_data = '{"version": 4}'
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_data)):
                assert load_cache() == {"version": 4}

    def test_load_cache_error(self):
        from unittest.mock import mock_open

        from graph.export_data import load_cache

        mock_data = '{invalid json}'
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_data)):
                with patch('logging.Logger.warning') as mock_warn:
                    assert load_cache() is None
                    mock_warn.assert_called_once()

    def test_save_cache(self):
        import json
        from unittest.mock import mock_open

        from graph.export_data import save_cache

        notes = [
            {'guid': '123', 'mod': 1, 'flds': 'a', 'deck': 'D1'},
            {'guid': '456', 'mod': 2, 'flds': 'b', 'deck': 'D2'},
            {'guid': '789'},
        ]

        m = mock_open()
        with patch('builtins.open', m):
            save_cache(notes, 10, 5, output_file="out.json")

        m.assert_called_once_with(m.call_args_list[0].args[0], 'w')

        # Verify JSON data written
        written = ''.join(c[0][0] for c in m().write.call_args_list)
        data = json.loads(written)
        assert data['version'] == 4
        assert data['note_count'] == 3
        assert data['node_count'] == 10
        assert data['link_count'] == 5
        assert data['output_file'] == "out.json"
        assert 'D1' in data['decks']
        assert 'D2' in data['decks']
        assert 'Unknown' in data['decks']

    def test_deck_progress(self):
        from graph.export_data import deck_progress

        with patch('graph.export_data.progress_bar') as mock_pb:
            deck_progress("Short Name", 0, 10, 100)
            mock_pb.assert_called_once_with(1, 10, 'Refs: Short Name (100 notes)')

            mock_pb.reset_mock()
            deck_progress("A Very Long Deck Name That Exceeds Thirty Characters Max", 1, 10, 100)
            mock_pb.assert_called_once()
            args = mock_pb.call_args[0]
            assert "A Very Long Deck Name That Exc…" in args[2]

    def test_save_cache_no_output_file(self):
        import json
        from unittest.mock import mock_open

        from graph.export_data import save_cache

        notes = [{'guid': '123', 'mod': 1, 'flds': 'a', 'deck': 'D1'}]

        m = mock_open()
        with patch('builtins.open', m):
            save_cache(notes, 10, 5)

        written = ''.join(c[0][0] for c in m().write.call_args_list)
        data = json.loads(written)
        assert 'output_file' not in data

    def test_deck_progress_short(self):
        from graph.export_data import deck_progress

        with patch('graph.export_data.progress_bar') as mock_pb:
            deck_progress("A" * 30, 0, 10, 100)
            mock_pb.assert_called_once()
            args = mock_pb.call_args[0]
            assert ("A" * 30) in args[2]
            assert "…" not in args[2]

    def test_save_cache_multiple_notes_same_deck(self):
        import json
        from unittest.mock import mock_open

        from graph.export_data import save_cache

        notes = [
            {'guid': '123', 'mod': 1, 'flds': 'a', 'deck': 'D1'},
            {'guid': '456', 'mod': 2, 'flds': 'b', 'deck': 'D1'},
        ]

        m = mock_open()
        with patch('builtins.open', m):
            save_cache(notes, 10, 5, output_file="out.json")

        written = ''.join(c[0][0] for c in m().write.call_args_list)
        data = json.loads(written)
        assert len(data['decks']['D1']) == 2
