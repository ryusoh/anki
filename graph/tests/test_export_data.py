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


def test_strip_html_none():
    from graph.export_data import strip_html

    assert strip_html(None) == ''


def test_strip_html_tags():
    from graph.export_data import strip_html

    assert strip_html('<p>Hello <b>World</b></p>') == 'Hello World'


def test_strip_html_entities():
    from graph.export_data import strip_html

    assert strip_html('Hello&nbsp;World&amp;Everyone') == 'Hello World&Everyone'
    assert strip_html('&lt;&gt;&quot;&#39;&apos;') == '<>"\'\''


def test_strip_html_separators():
    from graph.export_data import strip_html

    assert strip_html('Hello::World\nEveryone') == 'Hello World Everyone'


def test_strip_html_truncate():
    from graph.export_data import strip_html

    long_text = 'a' * 100
    assert len(strip_html(long_text)) == 60


def test_progress_bar_complete(capsys):
    import sys
    from unittest.mock import patch

    from graph.export_data import progress_bar

    with patch('sys.stderr') as mock_stderr:
        progress_bar(100, 100, prefix='Testing')
        mock_stderr.write.assert_any_call(
            '\r  Testing [████████████████████████████████████████] 100/100 (100%)'
        )
        mock_stderr.write.assert_any_call('\n')


def test_progress_bar_zero_total():
    from unittest.mock import patch

    from graph.export_data import progress_bar

    with patch('sys.stderr') as mock_stderr:
        progress_bar(0, 0, prefix='Testing')
        mock_stderr.write.assert_any_call(
            '\r  Testing [████████████████████████████████████████] 0/0 (100%)'
        )


def test_load_cache_not_exists():
    from unittest.mock import patch

    from graph.export_data import load_cache

    with patch('pathlib.Path.exists', return_value=False):
        assert load_cache() is None


def test_load_cache_success():
    import json
    from unittest.mock import MagicMock, patch

    from graph.export_data import load_cache

    mock_cache = {"version": 4}
    with (
        patch('pathlib.Path.exists', return_value=True),
        patch(
            'builtins.open',
            MagicMock(
                return_value=MagicMock(
                    __enter__=MagicMock(
                        return_value=MagicMock(read=MagicMock(return_value=json.dumps(mock_cache)))
                    )
                )
            ),
        ),
    ):
        with patch('json.load', return_value=mock_cache):
            assert load_cache() == mock_cache


def test_load_cache_json_error():
    import json
    from unittest.mock import MagicMock, patch

    from graph.export_data import load_cache

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch(
            'builtins.open',
            MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock()))),
        ),
    ):
        with patch('json.load', side_effect=json.JSONDecodeError("msg", "doc", 0)):
            assert load_cache() is None


def test_load_cache_key_error():
    from unittest.mock import MagicMock, patch

    from graph.export_data import load_cache

    with (
        patch('pathlib.Path.exists', return_value=True),
        patch(
            'builtins.open',
            MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock()))),
        ),
    ):
        with patch('json.load', side_effect=KeyError()):
            assert load_cache() is None


def test_save_cache():
    import json
    from unittest.mock import MagicMock, patch

    from graph.export_data import save_cache

    notes = [
        {'guid': '1', 'mod': 123, 'flds': 'A::B', 'deck': 'Deck1'},
        {'guid': '2', 'mod': 124, 'flds': 'C::D', 'deck': 'Deck1'},
    ]
    with patch('builtins.open') as mock_open, patch('json.dump') as mock_dump:
        with patch('graph.export_data.CACHE_FILE', 'mock_cache_file.json'):
            save_cache(notes, 2, 1, output_file='test.json')
            mock_open.assert_called_with('mock_cache_file.json', 'w')
            mock_dump.assert_called()

            args = mock_dump.call_args[0][0]
            assert args['version'] == 4
            assert args['note_count'] == 2
            assert args['node_count'] == 2
            assert args['link_count'] == 1
            assert args['output_file'] == 'test.json'
            assert 'Deck1' in args['decks']
            assert '1' in args['decks']['Deck1']
            assert '2' in args['decks']['Deck1']


def test_save_cache_no_deck():
    from unittest.mock import MagicMock, patch

    from graph.export_data import save_cache

    notes = [{'guid': '1'}]
    with patch('builtins.open'), patch('json.dump') as mock_dump:
        save_cache(notes, 1, 0)
        args = mock_dump.call_args[0][0]
        assert 'Unknown' in args['decks']
        assert '1' in args['decks']['Unknown']


def test_deck_progress(capsys):
    import sys
    from unittest.mock import patch

    from graph.export_data import deck_progress

    written = []

    class MockStderr:
        def write(self, s):
            written.append(s)

        def flush(self):
            pass

    with patch('sys.stderr', MockStderr()):
        deck_progress("MyDeck", 1, 5, 100)
        assert any('MyDeck' in w for w in written)


def test_deck_progress_truncates(capsys):
    import sys
    from unittest.mock import patch

    from graph.export_data import deck_progress

    written = []

    class MockStderr:
        def write(self, s):
            written.append(s)

        def flush(self):
            pass

    with patch('sys.stderr', MockStderr()):
        long_name = "A" * 60
        deck_progress(long_name, 1, 5, 100)
        assert any('A' * 30 in w and '…' in w for w in written)
