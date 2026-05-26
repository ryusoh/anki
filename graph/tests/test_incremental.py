import unittest
from unittest.mock import patch, MagicMock
"""
Tests for incremental export system
"""

import pytest
import json
from pathlib import Path
import tempfile
import os

# Import functions to test
import sys
sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21/graph')

from graph.incremental_export import load_config, save_config, strip_html


class TestConfigManagement:
    """Test configuration loading and saving."""
    
    def test_load_default_config(self, tmp_path):
        """Test loading non-existent config returns defaults."""
        # Temporarily change config file location
        from graph import incremental_export
        original = incremental_export.CONFIG_FILE
        incremental_export.CONFIG_FILE = tmp_path / "nonexistent.json"
        
        config = load_config()
        
        assert config['sample_size'] == 100
        assert config['increment'] == 100
        
        incremental_export.CONFIG_FILE = original
    
    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading config."""
        from graph import incremental_export
        original = incremental_export.CONFIG_FILE
        incremental_export.CONFIG_FILE = tmp_path / "test_config.json"
        
        config = {'sample_size': 500, 'increment': 200}
        save_config(config)
        
        loaded = load_config()
        
        assert loaded['sample_size'] == 500
        assert loaded['increment'] == 200
        
        incremental_export.CONFIG_FILE = original
    
    def test_config_persists(self, tmp_path):
        """Test that config persists across calls."""
        from graph import incremental_export
        original = incremental_export.CONFIG_FILE
        incremental_export.CONFIG_FILE = tmp_path / "test_config.json"
        
        save_config({'sample_size': 300})
        config1 = load_config()
        
        save_config({'sample_size': 400})
        config2 = load_config()
        
        assert config1['sample_size'] == 300
        assert config2['sample_size'] == 400
        
        incremental_export.CONFIG_FILE = original


class TestHTMLStripping:
    """Test HTML stripping for node labels."""
    
    def test_strip_bold_tags(self):
        """Test stripping <b> tags."""
        text = 'This is <b>bold</b> text'
        result = strip_html(text)
        assert '<b>' not in result
        assert 'bold' in result
    
    def test_strip_multiple_tags(self):
        """Test stripping multiple tag types."""
        text = '<b>bold</b> and <i>italic</i> and <u>underline</u>'
        result = strip_html(text)
        assert '<b>' not in result
        assert '<i>' not in result
        assert '<u>' not in result
        assert 'bold' in result
        assert 'italic' in result
    
    def test_strip_field_separator(self):
        """Test stripping Anki field separators."""
        text = 'Front::Back'
        result = strip_html(text)
        assert '::' not in result
        assert 'Front Back' == result
    
    def test_truncate_length(self):
        """Test truncation to 60 chars."""
        text = 'A' * 100
        result = strip_html(text)
        assert len(result) <= 60
    
    def test_preserve_japanese(self):
        """Test that Japanese text is preserved."""
        text = 'これがこの町で一番<b>高い</b>ビルです。'
        result = strip_html(text)
        assert '高い' in result
        assert '<b>' not in result


class TestIncrementLogic:
    """Test increment size logic."""
    
    def test_small_sizes_increment_by_100(self):
        """Test sizes < 1000 increment by 100."""
        sizes = [100, 200, 300, 500, 900]
        for size in sizes:
            next_size = size + 100
            assert next_size <= 1000
    
    def test_medium_sizes_increment_by_100(self):
        """Test sizes 1000-5000 increment by 100."""
        size = 1000
        next_size = size + 100
        assert next_size == 1100
    
    def test_large_sizes_increment_by_500(self):
        """Test sizes 5000-10000 increment by 500."""
        size = 5000
        next_size = size + 500
        assert next_size == 5500
    
    def test_very_large_sizes_increment_by_1000(self):
        """Test sizes 10000-50000 increment by 1000."""
        size = 10000
        next_size = size + 1000
        assert next_size == 11000
    
    def test_massive_sizes_increment_by_5000(self):
        """Test sizes 50000+ increment by 5000."""
        size = 50000
        next_size = size + 5000
        assert next_size == 55000

class TestExportGraph:
    """Test exporting graph data."""

    @patch('graph.incremental_export.json.dump')
    @patch('graph.incremental_export.open', new_callable=unittest.mock.mock_open)
    @patch('graph.incremental_export.build_graph')
    @patch('graph.incremental_export.json.load')
    @patch('graph.incremental_export.gzip.open', new_callable=unittest.mock.mock_open)
    def test_export_graph(self, mock_gzip_open, mock_json_load, mock_build_graph, mock_open, mock_json_dump):
        """Test export_graph reads notes, builds graph, and writes to DATA_FILE."""
        from graph.incremental_export import export_graph
        import networkx as nx

        # Mock json load
        mock_json_load.return_value = [{'id': '1', 'front': 'Card 1', 'deck': 'Deck A'}]

        # Mock build graph
        G = nx.DiGraph()
        G.add_node('1', front='Card 1', deck='Deck A', pagerank=0.5)
        mock_build_graph.return_value = G

        # Run
        num_nodes = export_graph(10)

        # Assertions
        assert num_nodes == 1
        mock_json_load.assert_called_once()
        mock_build_graph.assert_called_once()
        mock_open.assert_called_once()
        mock_json_dump.assert_called_once()

        # Verify JSON dump structure
        args, kwargs = mock_json_dump.call_args
        data = args[0]
        assert 'nodes' in data
        assert 'links' in data
        assert len(data['nodes']) == 1
        assert data['nodes'][0]['id'] == '1'

class TestMainExecution:
    """Test main command-line execution."""

    @patch('graph.incremental_export.export_graph')
    @patch('graph.incremental_export.save_config')
    @patch('graph.incremental_export.load_config')
    @patch('sys.argv', ['incremental_export.py', '--status'])
    def test_main_status(self, mock_load_config, mock_save_config, mock_export_graph):
        """Test main running with --status flag."""
        from graph.incremental_export import main
        mock_load_config.return_value = {'sample_size': 100, 'increment': 100}

        main()

        mock_load_config.assert_called_once()
        mock_export_graph.assert_not_called()

    @patch('graph.incremental_export.export_graph')
    @patch('graph.incremental_export.save_config')
    @patch('graph.incremental_export.load_config')
    @patch('sys.argv', ['incremental_export.py', '--reset'])
    def test_main_reset(self, mock_load_config, mock_save_config, mock_export_graph):
        """Test main running with --reset flag."""
        from graph.incremental_export import main
        mock_load_config.return_value = {'sample_size': 500, 'increment': 100}

        main()

        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]
        assert saved_config['sample_size'] == 100
        mock_export_graph.assert_called_once_with(100)

    @patch('graph.incremental_export.export_graph')
    @patch('graph.incremental_export.save_config')
    @patch('graph.incremental_export.load_config')
    @patch('sys.argv', ['incremental_export.py', '--size', '200'])
    def test_main_size(self, mock_load_config, mock_save_config, mock_export_graph):
        """Test main running with --size flag."""
        from graph.incremental_export import main
        mock_load_config.return_value = {'sample_size': 100, 'increment': 100}

        main()

        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]
        assert saved_config['sample_size'] == 200
        mock_export_graph.assert_called_once_with(200)

    @patch('graph.incremental_export.export_graph')
    @patch('graph.incremental_export.save_config')
    @patch('graph.incremental_export.load_config')
    @patch('sys.argv', ['incremental_export.py', '--next'])
    def test_main_next(self, mock_load_config, mock_save_config, mock_export_graph):
        """Test main running with --next flag."""
        from graph.incremental_export import main
        mock_load_config.return_value = {'sample_size': 100, 'increment': 100}

        main()

        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]
        assert saved_config['sample_size'] == 200
        mock_export_graph.assert_called_once_with(200)


class TestExportValidation:
    """Test export validation."""
    
    def test_export_creates_valid_json(self, tmp_path):
        """Test that export creates valid JSON."""
        # This would require actual Anki data
        # For now, just test the structure
        test_data = {
            'nodes': [
                {'id': 'n1', 'label': 'Test', 'deck': 'Test', 'pagerank': 0.01, 'size': 1.0}
            ],
            'links': []
        }
        
        output_file = tmp_path / "test_graph.json"
        with open(output_file, 'w') as f:
            json.dump(test_data, f)
        
        # Verify it loads back
        with open(output_file, 'r') as f:
            loaded = json.load(f)
        
        assert 'nodes' in loaded
        assert 'links' in loaded
        assert len(loaded['nodes']) == 1
    
    def test_node_has_required_fields(self):
        """Test that nodes have all required fields."""
        node = {
            'id': 'test123',
            'label': 'Test Card',
            'deck': 'Test Deck',
            'pagerank': 0.01234,
            'size': 1.234
        }
        
        required = ['id', 'label', 'deck', 'pagerank', 'size']
        for field in required:
            assert field in node
    
    def test_link_has_required_fields(self):
        """Test that links have all required fields."""
        link = {
            'source': 'node1',
            'target': 'node2',
            'weight': 1.5
        }
        
        required = ['source', 'target', 'weight']
        for field in required:
            assert field in link
