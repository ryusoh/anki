import json
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

from graph.export_data import main


def test_export_data_cache_no_changes():
    with patch('sys.argv', ['export_data.py']):
        with patch('pathlib.Path.exists', return_value=True):
            with patch(
                'graph.export_data.load_cache',
                return_value={'node_count': 1, 'link_count': 1, 'last_checksums': {}},
            ):
                with patch('graph.export_data.find_changed_notes', return_value={}):
                    with patch('gzip.open', mock_open(read_data='[]')):
                        with patch(
                            'builtins.open', mock_open(read_data='{"nodes": [], "links": []}')
                        ):
                            with patch('sys.exit') as mock_exit:
                                main()
                                mock_exit.assert_called_with(0)


def test_export_data_incremental():
    test_notes = [{'guid': 'N1', 'deck': 'Deck A', 'flds': 'front\x1fback', 'mod': 123}]
    changes = {'Deck A': {'new_guids': {'N1'}, 'modified_guids': set(), 'removed_guids': set()}}

    with patch('sys.argv', ['export_data.py']):
        with patch('pathlib.Path.exists', return_value=True):
            with patch(
                'graph.export_data.load_cache',
                return_value={'node_count': 1, 'link_count': 1, 'last_checksums': {}},
            ):
                with patch('graph.export_data.find_changed_notes', return_value=changes):
                    existing_data = json.dumps({'nodes': [], 'links': []})

                    def mock_open_file(*args, **kwargs):
                        if 'notes.json.gz' in str(args[0]):
                            return mock_open(read_data=json.dumps(test_notes))(*args, **kwargs)
                        return mock_open(read_data=existing_data)(*args, **kwargs)

                    with patch('builtins.open', mock_open(read_data=existing_data)):
                        with patch(
                            'graph.references.find_references_incremental',
                            return_value=[{'source': 'N1', 'target': 'N1', 'weight': 1.0}],
                        ):
                            with patch('graph.export_data.save_cache'):
                                with patch(
                                    'gzip.open', mock_open(read_data=json.dumps(test_notes))
                                ):
                                    main()


def test_export_data_incremental_public():
    test_notes = [{'guid': 'N1', 'deck': 'Deck A', 'flds': 'front\x1fback', 'mod': 123}]
    changes = {'Deck A': {'new_guids': {'N1'}, 'modified_guids': set(), 'removed_guids': set()}}

    with patch('sys.argv', ['export_data.py', '--public']):
        with patch('pathlib.Path.exists', return_value=True):
            with patch(
                'graph.export_data.load_cache',
                return_value={'node_count': 1, 'link_count': 1, 'last_checksums': {}},
            ):
                with patch('graph.export_data.find_changed_notes', return_value=changes):
                    existing_data = json.dumps(
                        {
                            'nodes': [
                                {
                                    'id': 'N2',
                                    'deck': 'Deck A',
                                    'x': 1,
                                    'y': 2,
                                    'z': 3,
                                    'pagerank': 0.5,
                                }
                            ],
                            'links': [],
                        }
                    )
                    with patch('builtins.open', mock_open(read_data=existing_data)):
                        with patch(
                            'graph.references.find_references_incremental',
                            return_value=[{'source': 'N1', 'target': 'N1', 'weight': 1.0}],
                        ):
                            with patch('graph.export_data.save_cache'):
                                with patch(
                                    'gzip.open', mock_open(read_data=json.dumps(test_notes))
                                ):
                                    main()


class MockList(list):
    def __call__(self, data=False):
        if not data:
            return self
        else:
            return getattr(self, '_data', [])


def test_export_data_full_rebuild():
    test_notes = [{'guid': 'N1', 'deck': 'Deck A', 'flds': 'front\x1fback', 'mod': 123}]

    with patch('sys.argv', ['export_data.py', '--full']):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open()):
                with patch('graph.export_data.build_graph') as mock_build_graph:
                    mock_graph = MagicMock()

                    nodes_list = MockList(['N1'])
                    nodes_list._data = [
                        ('N1', {'front': 'front', 'deck': 'Deck A', 'pagerank': 0.5})
                    ]
                    mock_graph.nodes = nodes_list

                    edges_list = MockList([('N1', 'N1')])
                    edges_list._data = [('N1', 'N1', {'weight': 1.0})]
                    mock_graph.edges = edges_list

                    mock_build_graph.return_value = mock_graph

                    with patch(
                        'graph.export_data.compute_layout', return_value={'N1': (1.0, 2.0, 3.0)}
                    ):
                        with patch('graph.export_data.save_cache'):
                            with patch('gzip.open', mock_open(read_data=json.dumps(test_notes))):
                                main()


def test_export_data_full_rebuild_public():
    test_notes = [{'guid': 'N1', 'deck': 'Deck A', 'flds': 'front\x1fback', 'mod': 123}]

    with patch('sys.argv', ['export_data.py', '--full', '--public']):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open()):
                with patch('graph.export_data.build_graph') as mock_build_graph:
                    mock_graph = MagicMock()

                    nodes_list = MockList(['N1'])
                    nodes_list._data = [
                        ('N1', {'front': 'front', 'deck': 'Deck A', 'pagerank': 0.5})
                    ]
                    mock_graph.nodes = nodes_list

                    edges_list = MockList([('N1', 'N1')])
                    edges_list._data = [('N1', 'N1', {'weight': 1.0})]
                    mock_graph.edges = edges_list

                    mock_build_graph.return_value = mock_graph

                    with patch(
                        'graph.export_data.compute_layout', return_value={'N1': (1.0, 2.0, 3.0)}
                    ):
                        with patch('graph.export_data.save_cache'):
                            with patch('gzip.open', mock_open(read_data=json.dumps(test_notes))):
                                main()
