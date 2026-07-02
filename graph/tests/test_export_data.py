import concurrent.futures
from unittest.mock import MagicMock, mock_open, patch

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

    def test_strip_html_edge_cases(self):
        from graph.export_data import strip_html

        assert strip_html("") == ""
        assert strip_html("a &nbsp; b") == "a b"
        assert strip_html("a &amp; b") == "a & b"
        assert strip_html("a &lt; b &gt; c") == "a < b > c"
        assert strip_html("a &quot; b &#39; c &apos; d") == "a \" b ' c ' d"
        assert strip_html("a :: b\nc") == "a b c"
        long_str = "a" * 100
        assert len(strip_html(long_str)) == 60

    def test_note_fingerprint_length(self):
        from graph.export_data import note_fingerprint

        note = {'guid': '123', 'mod': 456, 'deck': 'Default'}
        fp = note_fingerprint(note)
        assert isinstance(fp, str)
        assert len(fp) == 12

    def test_deck_progress(self):
        from unittest.mock import MagicMock, patch

        from graph.export_data import deck_progress

        with patch('graph.export_data.progress_bar') as mock_progress_bar:
            deck_progress("Short", 0, 10, 100)
            mock_progress_bar.assert_called_with(1, 10, 'Refs: Short (100 notes)')

            long_name = "A" * 50
            deck_progress(long_name, 1, 10, 50)
            mock_progress_bar.assert_called_with(2, 10, f'Refs: {"A"*30}… (50 notes)')

    def test_compute_deck_layout_empty(self):
        import networkx as nx

        from graph.export_data import _compute_deck_layout

        g_empty = nx.DiGraph()
        assert _compute_deck_layout(g_empty, 10) == {}

        g_one = nx.DiGraph()
        g_one.add_node("A")
        assert _compute_deck_layout(g_one, 10) == {"A": (0.0, 0.0)}

    def test_compute_deck_layout_multiple(self):
        from unittest.mock import MagicMock, patch

        import networkx as nx

        from graph.export_data import _compute_deck_layout

        g_two = nx.DiGraph()
        g_two.add_node("A")
        g_two.add_node("B")
        with patch('graph.export_data.ForceAtlas2') as mock_fa2:
            mock_instance = MagicMock()
            mock_instance.forceatlas2_networkx_layout.return_value = {
                "A": (10.0, 10.0),
                "B": (20.0, 20.0),
            }
            mock_fa2.return_value = mock_instance

            layout = _compute_deck_layout(g_two, 10)

            assert "A" in layout
            assert layout["A"][0] < 0
            assert layout["B"][0] > 0


# Added tests to cover gaps in caching, layout, and HTML stripping
def test_find_changed_notes_different_output_file():
    from graph.export_data import find_changed_notes

    cache = {'version': 4, 'output_file': 'some_file.json', 'decks': {}}
    assert find_changed_notes([], cache, output_file='other_file.json') is None


def test_find_changed_notes_cache_version_mismatch():
    from graph.export_data import find_changed_notes

    cache = {'version': 3, 'decks': {}}
    assert find_changed_notes([], cache) is None


def test_compute_deck_layout_single_node():
    import networkx as nx

    from graph.export_data import _compute_deck_layout

    G = nx.Graph()
    G.add_node('1', deck='A')
    layout = _compute_deck_layout(G, 10)
    assert layout == {'1': (0.0, 0.0)}


@patch('graph.export_data.ForceAtlas2')
def test_compute_deck_layout_multiple_nodes_extra(mock_fa2):
    import networkx as nx

    from graph.export_data import _compute_deck_layout

    G = nx.Graph()
    G.add_node('1', deck='A')
    G.add_node('2', deck='A')

    mock_fa2_instance = MagicMock()
    mock_fa2.return_value = mock_fa2_instance
    mock_fa2_instance.forceatlas2_networkx_layout.return_value = {
        '1': (1.0, 1.0),
        '2': (-1.0, -1.0),
    }

    layout = _compute_deck_layout(G, 10)
    assert '1' in layout and '2' in layout


# Run the layout pool in-process (threads) so the ForceAtlas2 patch below applies.
# A real ProcessPoolExecutor spawns workers that re-import graph.export_data and
# fail on `from fa2_modified import ForceAtlas2` (fa2_modified is not installed in CI).
@patch('concurrent.futures.ProcessPoolExecutor', concurrent.futures.ThreadPoolExecutor)
@patch('graph.export_data.ForceAtlas2')
def test_compute_layout(mock_fa2):
    import networkx as nx

    from graph.export_data import compute_layout

    G = nx.Graph()
    G.add_node('1', deck='A')
    G.add_node('2', deck='A')
    G.add_node('3', deck='B')

    mock_fa2_instance = MagicMock()
    mock_fa2.return_value = mock_fa2_instance
    mock_fa2_instance.forceatlas2_networkx_layout.return_value = {
        '1': (1.0, 1.0),
        '2': (-1.0, -1.0),
        '3': (0.0, 0.0),
    }

    layout = compute_layout(G, iterations=1)
    assert '1' in layout
    assert '2' in layout
    assert '3' in layout
    assert len(layout['1']) == 3


def test_progress_bar_complete(capsys):
    from graph.export_data import progress_bar

    progress_bar(10, 10)
    captured = capsys.readouterr()
    assert "\n" in captured.err


def test_deck_progress_truncates(capsys):
    from graph.export_data import deck_progress

    long_name = "A" * 40
    deck_progress(long_name, 1, 2, 100)
    captured = capsys.readouterr()
    assert "A" * 30 + "…" in captured.err


def test_strip_html_basic():
    from graph.export_data import strip_html

    assert strip_html("Hello <b>world</b>") == "Hello world"
    assert strip_html("") == ""


def test_note_fingerprint():
    from graph.export_data import note_fingerprint

    note = {'guid': 'abc', 'mod': '123', 'flds': 'val', 'deck': 'Default'}
    res = note_fingerprint(note)
    assert len(res) == 12


@patch('pathlib.Path.exists', return_value=False)
def test_load_cache_no_file(mock_exists):
    from graph.export_data import load_cache

    assert load_cache() is None


@patch('pathlib.Path.exists', return_value=True)
def test_load_cache_json_error(mock_exists):
    from graph.export_data import load_cache

    m = mock_open(read_data="invalid json")
    with patch('builtins.open', m):
        assert load_cache() is None


@patch('pathlib.Path.exists', return_value=True)
def test_load_cache_success(mock_exists):
    from graph.export_data import load_cache

    m = mock_open(read_data='{"version": 4}')
    with patch('builtins.open', m):
        assert load_cache() == {"version": 4}


def test_save_cache():
    from graph.export_data import save_cache

    notes = [{'guid': 'abc', 'deck': 'D1'}]
    m = mock_open()
    with patch('builtins.open', m):
        save_cache(notes, 1, 1, output_file='out.json')
        m.assert_called_once()
        calls = m().write.call_args_list
        written_data = "".join([c[0][0] for c in calls])
        assert 'out.json' in written_data


def test_find_changed_notes_all_changes():
    from graph.export_data import find_changed_notes

    cache = {'version': 4, 'decks': {'D1': {'1': 'a', '2': 'b'}, 'D2': {'3': 'c'}}}
    notes = [{'guid': '1', 'deck': 'D1'}, {'guid': '4', 'deck': 'D1'}]

    with patch('graph.export_data.note_fingerprint', return_value='z'):
        changes = find_changed_notes(notes, cache)
        assert 'D1' in changes
        assert '1' in changes['D1']['modified_guids']
        assert '4' in changes['D1']['new_guids']
        assert '2' in changes['D1']['removed_guids']

        assert 'D2' in changes
        assert '3' in changes['D2']['removed_guids']


def test_find_changed_notes_no_changes():
    from graph.export_data import find_changed_notes

    cache = {'version': 4, 'decks': {'D1': {'1': 'z'}}}
    notes = [{'guid': '1', 'deck': 'D1'}]
    with patch('graph.export_data.note_fingerprint', return_value='z'):
        changes = find_changed_notes(notes, cache)
        assert changes == {}
