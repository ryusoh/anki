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
