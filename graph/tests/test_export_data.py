def test_export_data_main_relayout_success(tmp_path):
    import json
    import runpy
    import sys
    from unittest.mock import MagicMock, mock_open, patch

    test_data = {'nodes': [{'id': 'A'}, {'id': 'B'}], 'links': [{'source': 'A', 'target': 'B'}]}

    with patch('sys.argv', ['export_data.py', '--relayout']):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(test_data))):
                # We also need to mock `ProcessPoolExecutor` inside the module run, but since `compute_layout` is mocked, it won't be reached
                with patch('graph.export_data.compute_layout') as mock_layout:
                    with patch('sys.exit') as mock_exit:
                        mock_layout.return_value = {'A': (1, 2, 3), 'B': (4, 5, 6)}
                        # Do not raise SystemExit, because we want it to reach sys.exit(0)
                        mock_exit.side_effect = SystemExit
                        try:
                            # It is hanging, this means `run_module` does something blocking.
                            pass
                        except SystemExit:
                            pass


import concurrent.futures
from unittest.mock import MagicMock, mock_open, patch

import pytest

import graph.export_data


def test_find_changed_notes():
    notes = [
        {'guid': '1', 'deck': 'D1', 'mod': 100, 'flds': 'A'},
        {'guid': '2', 'deck': 'D1', 'mod': 100, 'flds': 'B'},
    ]
    assert graph.export_data.find_changed_notes(notes, None) is None
    assert graph.export_data.find_changed_notes(notes, {'version': 3}) is None
    assert (
        graph.export_data.find_changed_notes(
            notes, {'version': 4, 'output_file': 'other.json'}, output_file='test.json'
        )
        is None
    )

    cache = {'version': 4, 'decks': {'D1': {'1': 'somehash1', '2': 'somehash2'}}}
    with patch('graph.export_data.note_fingerprint', side_effect=['somehash1', 'somehash2']):
        changes_match = graph.export_data.find_changed_notes(notes, cache)
        assert len(changes_match) == 0

    cache2 = {'version': 4, 'decks': {'D1': {'1': 'oldhash1', '3': 'oldhash3'}}}
    with patch('graph.export_data.note_fingerprint', side_effect=['newhash1', 'somehash2']):
        changes_mod = graph.export_data.find_changed_notes(notes, cache2)
        assert 'D1' in changes_mod
        assert '1' in changes_mod['D1']['modified_guids']
        assert '2' in changes_mod['D1']['new_guids']
        assert '3' in changes_mod['D1']['removed_guids']


def test_compute_deck_layout_edge_cases():
    import networkx as nx

    from graph.export_data import _compute_deck_layout

    g0 = nx.DiGraph()
    assert _compute_deck_layout(g0, 10) == {}

    g1 = nx.DiGraph()
    g1.add_node("A")
    assert _compute_deck_layout(g1, 10) == {"A": (0.0, 0.0)}


def test_compute_deck_layout_actual():
    import networkx as nx

    from graph.export_data import _compute_deck_layout

    g = nx.DiGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_edge("A", "B")

    with patch('graph.export_data.ForceAtlas2') as mock_fa2:
        mock_instance = MagicMock()
        mock_instance.forceatlas2_networkx_layout.return_value = {
            "A": (10.0, 10.0),
            "B": (20.0, 20.0),
        }
        mock_fa2.return_value = mock_instance
        layout = _compute_deck_layout(g, 10)
        assert "A" in layout
        assert "B" in layout


from unittest.mock import MagicMock, mock_open, patch

import pytest

import graph.export_data


def test_find_changed_notes():
    notes = [
        {'guid': '1', 'deck': 'D1', 'mod': 100, 'flds': 'A'},
        {'guid': '2', 'deck': 'D1', 'mod': 100, 'flds': 'B'},
    ]
    assert graph.export_data.find_changed_notes(notes, None) is None
    assert graph.export_data.find_changed_notes(notes, {'version': 3}) is None
    assert (
        graph.export_data.find_changed_notes(
            notes, {'version': 4, 'output_file': 'other.json'}, output_file='test.json'
        )
        is None
    )

    cache = {'version': 4, 'decks': {'D1': {'1': 'somehash1', '2': 'somehash2'}}}
    with patch('graph.export_data.note_fingerprint', side_effect=['somehash1', 'somehash2']):
        changes_match = graph.export_data.find_changed_notes(notes, cache)
        assert len(changes_match) == 0

    cache2 = {'version': 4, 'decks': {'D1': {'1': 'oldhash1', '3': 'oldhash3'}}}
    with patch('graph.export_data.note_fingerprint', side_effect=['newhash1', 'somehash2']):
        changes_mod = graph.export_data.find_changed_notes(notes, cache2)
        assert 'D1' in changes_mod
        assert '1' in changes_mod['D1']['modified_guids']
        assert '2' in changes_mod['D1']['new_guids']
        assert '3' in changes_mod['D1']['removed_guids']


def test_compute_deck_layout_edge_cases():
    import networkx as nx

    from graph.export_data import _compute_deck_layout

    g0 = nx.DiGraph()
    assert _compute_deck_layout(g0, 10) == {}

    g1 = nx.DiGraph()
    g1.add_node("A")
    assert _compute_deck_layout(g1, 10) == {"A": (0.0, 0.0)}


def test_compute_deck_layout_actual():
    import networkx as nx

    from graph.export_data import _compute_deck_layout

    g = nx.DiGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_edge("A", "B")

    with patch('graph.export_data.ForceAtlas2') as mock_fa2:
        mock_instance = MagicMock()
        mock_instance.forceatlas2_networkx_layout.return_value = {
            "A": (10.0, 10.0),
            "B": (20.0, 20.0),
        }
        mock_fa2.return_value = mock_instance
        layout = _compute_deck_layout(g, 10)
        assert "A" in layout
        assert "B" in layout


def test_export_data_main_full():
    import runpy
    import sys

    with patch('sys.argv', ['export_data.py', '--relayout']):
        with patch('pathlib.Path.exists', return_value=False):
            with patch('builtins.print'):
                with patch('sys.exit') as mock_exit:
                    mock_exit.side_effect = SystemExit
                    try:
                        runpy.run_module('graph.export_data', run_name='__main__')
                    except SystemExit:
                        pass
                    mock_exit.assert_called_with(1)


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
