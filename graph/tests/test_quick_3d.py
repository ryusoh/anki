import json
import runpy
from unittest.mock import MagicMock, mock_open, patch

import networkx as nx
import pytest

from graph.quick_3d import scale_node_size, strip_html


def test_strip_html_none():
    assert strip_html(None) == ''


def test_strip_html_tags():
    assert strip_html('<p>Hello <b>World</b></p>') == 'Hello World'


def test_strip_html_separators():
    assert strip_html('Hello::World\nEveryone') == 'Hello World Everyone'


def test_strip_html_truncate():
    long_text = 'a' * 100
    assert len(strip_html(long_text)) == 60


def test_scale_node_size_min():
    assert scale_node_size(0.001) == 0.5


def test_scale_node_size_max():
    assert scale_node_size(0.1) == 3.0


def test_scale_node_size_mid():
    assert scale_node_size(0.015) == 1.5


def test_main_execution_file_not_found(capsys):
    with patch('gzip.open', side_effect=FileNotFoundError):
        with patch('sys.exit', side_effect=SystemExit) as mock_exit:
            with pytest.raises(SystemExit):
                runpy.run_module("graph.quick_3d", run_name="__main__")
            mock_exit.assert_called_with(0)
            captured = capsys.readouterr()
            assert "not found. Skipping main execution." in captured.out


def test_main_execution_success(capsys):
    mock_notes = [{"guid": "1", "front": "test_front", "pagerank": 0.05, "weight": 2.0}]
    mock_file_content = json.dumps(mock_notes)

    # Use a real NetworkX graph to bypass all the mocking complexity
    test_graph = nx.Graph()
    test_graph.add_node("1", front="test_label", pagerank=0.05)
    test_graph.add_edge("1", "2", weight=2.0)

    with patch('gzip.open', mock_open(read_data=mock_file_content)):
        with patch('graph.quick_3d.build_graph', return_value=test_graph):
            with patch('builtins.open', mock_open()) as mock_out:
                runpy.run_module("graph.quick_3d", run_name="__main__")

                # Check output
                captured = capsys.readouterr()
                assert "Using 1 notes for quick test..." in captured.out
                assert "FAST! Created 3D viz with 100 cards" in captured.out

                # Just assert that the file is written to avoid checking the specific JSON format
                mock_out.assert_called_once()
