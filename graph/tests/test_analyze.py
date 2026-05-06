"""
Tests for graph CLI (analyze.py).

Tests command-line interface, deck aliases, and output formatting.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestDeckAliases:
    """Test deck alias resolution."""
    
    def test_alias_j_resolves(self):
        """Test that 'J' alias resolves to Japanese."""
        from graph.analyze import DECK_ALIASES
        
        assert DECK_ALIASES['J'] == '言語日語'
        assert DECK_ALIASES['j'] == '言語日語'
        assert DECK_ALIASES['1'] == '言語日語'
    
    def test_alias_c_resolves(self):
        """Test that 'C' alias resolves to Cantonese."""
        from graph.analyze import DECK_ALIASES
        
        assert DECK_ALIASES['C'] == '言語粵語'
        assert DECK_ALIASES['c'] == '言語粵語'
        assert DECK_ALIASES['2'] == '言語粵語'
    
    def test_alias_e_resolves(self):
        """Test that 'E' alias resolves to English."""
        from graph.analyze import DECK_ALIASES
        
        assert DECK_ALIASES['E'] == '言語英語'
        assert DECK_ALIASES['e'] == '言語英語'
        assert DECK_ALIASES['3'] == '言語英語'
    
    def test_alias_s_resolves(self):
        """Test that 'S' alias resolves to Wu/Shanghai."""
        from graph.analyze import DECK_ALIASES
        
        assert DECK_ALIASES['S'] == '言語呉語'
        assert DECK_ALIASES['s'] == '言語呉語'
        assert DECK_ALIASES['4'] == '言語呉語'
    
    def test_alias_t_resolves(self):
        """Test that 'T' alias resolves to Taiwanese."""
        from graph.analyze import DECK_ALIASES
        
        assert DECK_ALIASES['T'] == '言語台語'
        assert DECK_ALIASES['t'] == '言語台語'
        assert DECK_ALIASES['5'] == '言語台語'
    
    def test_alias_f_resolves(self):
        """Test that 'F' alias resolves to Finance (merged deck)."""
        from graph.analyze import DECK_ALIASES

        assert DECK_ALIASES['F'] == '金融'
        assert DECK_ALIASES['f'] == '金融'
        assert DECK_ALIASES['6'] == '金融'


class TestResolveDeckAlias:
    """Test resolve_deck_alias function."""
    
    def test_resolve_single_alias(self):
        """Test resolving a single deck alias."""
        from graph.analyze import resolve_deck_alias
        
        assert resolve_deck_alias('J') == '言語日語'
        assert resolve_deck_alias('1') == '言語日語'
    
    def test_resolve_finance_alias(self):
        """Test that 'F' returns None (matches both finance decks)."""
        from graph.analyze import resolve_deck_alias
        
        # F is special - matches both finance decks
        assert resolve_deck_alias('F') == '金融'
    
    def test_resolve_unknown_alias(self):
        """Test resolving unknown alias returns None."""
        from graph.analyze import resolve_deck_alias
        
        assert resolve_deck_alias('XYZ') is None
        assert resolve_deck_alias('99') is None


class TestGetDeckNotes:
    """Test get_deck_notes function."""
    
    def test_get_notes_by_exact_name(self):
        """Test getting notes by exact deck name."""
        from graph.analyze import get_deck_notes
        
        notes = [
            {'deck': 'Test Deck', 'guid': 'n1'},
            {'deck': 'Other Deck', 'guid': 'n2'},
        ]
        
        result = get_deck_notes(notes, 'Test Deck')
        
        assert len(result) == 1
        assert result[0]['guid'] == 'n1'
    
    def test_get_notes_by_alias(self):
        """Test getting notes by alias."""
        from graph.analyze import get_deck_notes
        
        notes = [
            {'deck': '言語日語', 'guid': 'n1'},
            {'deck': '言語粵語', 'guid': 'n2'},
        ]
        
        result = get_deck_notes(notes, 'J')
        
        assert len(result) == 1
        assert result[0]['deck'] == '言語日語'
    
    def test_get_finance_notes(self):
        """Test getting notes from merged finance deck with 'F' alias."""
        from graph.analyze import get_deck_notes

        notes = [
            {'deck': '金融', 'guid': 'n1'},
            {'deck': '金融', 'guid': 'n2'},
            {'deck': '言語日語', 'guid': 'n3'},
        ]

        result = get_deck_notes(notes, 'F')

        assert len(result) == 2
        assert set(n['guid'] for n in result) == {'n1', 'n2'}
    
    def test_get_notes_empty_deck(self):
        """Test getting notes from empty deck."""
        from graph.analyze import get_deck_notes
        
        notes = [
            {'deck': 'Other', 'guid': 'n1'},
        ]
        
        result = get_deck_notes(notes, 'Nonexistent')
        
        assert len(result) == 0


class TestBuildDeckMapFromCards:
    """Test build_deck_map_from_cards resolves via decks.json."""

    def test_uses_decks_json_over_stale_deck_name(self, tmp_path):
        """Cards with stale deck_name should resolve via did + decks.json."""
        from graph.analyze import build_deck_map_from_cards
        import gzip, json

        cards = [
            {"nid": 1, "did": 100, "deck_name": "金融\x1f産研"},
            {"nid": 2, "did": 100, "deck_name": "金融\x1f理論"},
            {"nid": 3, "did": 200, "deck_name": "言語\x1f英語"},
        ]
        cards_file = tmp_path / "cards.json.gz"
        with gzip.open(cards_file, 'wt', encoding='utf-8') as f:
            json.dump(cards, f)

        decks_file = tmp_path / "decks.json"
        with open(decks_file, 'w') as f:
            json.dump({"100": "金融", "200": "言語\x1f英語"}, f)

        result = build_deck_map_from_cards([], cards_file, decks_file)
        assert result[1]['deck_name'] == '金融'
        assert result[2]['deck_name'] == '金融'
        assert result[3]['deck_name'] == '言語\x1f英語'

    def test_falls_back_to_deck_name_without_decks_file(self, tmp_path):
        """Without decks.json, use per-card deck_name."""
        from graph.analyze import build_deck_map_from_cards
        import gzip, json

        cards = [
            {"nid": 1, "did": 100, "deck_name": "TestDeck"},
        ]
        cards_file = tmp_path / "cards.json.gz"
        with gzip.open(cards_file, 'wt', encoding='utf-8') as f:
            json.dump(cards, f)

        result = build_deck_map_from_cards([], cards_file)
        assert result[1]['deck_name'] == 'TestDeck'


class TestLoadNotesFromFile:
    """Test load_notes_from_file function."""
    
    def test_load_from_gzip_file(self, tmp_path):
        """Test loading notes from .json.gz file."""
        from graph.analyze import load_notes_from_file
        import gzip
        import json
        
        # Create test file
        test_notes = [
            {'guid': 'n1', 'deck': 'Test', 'flds': 'front'},
            {'guid': 'n2', 'deck': 'Test', 'flds': 'back'},
        ]
        
        notes_file = tmp_path / "notes.json.gz"
        with gzip.open(notes_file, 'wt', encoding='utf-8') as f:
            json.dump(test_notes, f)
        
        # Load it back
        loaded = load_notes_from_file(notes_file)
        
        assert len(loaded) == 2
        assert loaded[0]['guid'] == 'n1'
    
    def test_load_from_json_file(self, tmp_path):
        """Test loading notes from .json file."""
        from graph.analyze import load_notes_from_file
        import json
        
        test_notes = [
            {'guid': 'n1', 'deck': 'Test'},
        ]
        
        notes_file = tmp_path / "notes.json"
        with open(notes_file, 'w') as f:
            json.dump(test_notes, f)
        
        loaded = load_notes_from_file(notes_file)
        
        assert len(loaded) == 1
    
    def test_load_nonexistent_file(self, tmp_path, capsys):
        """Test loading from nonexistent file shows error."""
        from graph.analyze import load_notes_from_file
        
        notes_file = tmp_path / "nonexistent.json.gz"
        result = load_notes_from_file(notes_file)
        
        assert result == []
        captured = capsys.readouterr()
        assert "not found" in captured.err


class TestGetAvailableDecks:
    """Test get_available_decks function."""
    
    def test_get_unique_decks(self):
        """Test getting unique deck names."""
        from graph.analyze import get_available_decks
        
        notes = [
            {'deck': 'Deck A', 'guid': 'n1'},
            {'deck': 'Deck B', 'guid': 'n2'},
            {'deck': 'Deck A', 'guid': 'n3'},  # Duplicate
        ]
        
        decks = get_available_decks(notes)
        
        assert len(decks) == 2
        assert set(decks) == {'Deck A', 'Deck B'}
    
    def test_get_decks_empty_list(self):
        """Test getting decks from empty list."""
        from graph.analyze import get_available_decks
        
        decks = get_available_decks([])
        
        assert decks == []


class TestPrintDeckList:
    """Test print_deck_list function."""
    
    def test_print_deck_list_format(self, capsys):
        """Test deck list output format."""
        from graph.analyze import print_deck_list
        
        notes = [
            {'deck': 'Deck A', 'guid': 'n1'},
            {'deck': 'Deck A', 'guid': 'n2'},
            {'deck': 'Deck B', 'guid': 'n3'},
        ]
        
        print_deck_list(notes)
        captured = capsys.readouterr()
        
        assert 'Available Decks' in captured.out
        assert 'Deck A' in captured.out
        assert 'Deck B' in captured.out
        assert '2 notes' in captured.out  # Deck A has 2 notes
        assert '1 note' in captured.out or '1 notes' in captured.out  # Deck B has 1 note


class TestPrintTopNotes:
    """Test print_top_notes function."""
    
    def test_print_top_notes_format(self, capsys):
        """Test top notes output format."""
        from graph.analyze import print_top_notes
        import networkx as nx
        
        # Create test graph
        G = nx.DiGraph()
        G.add_node('n1', front='Question 1', pagerank=0.5, tags='tag1', deck='Test')
        G.add_node('n2', front='Question 2', pagerank=0.3, tags='tag2', deck='Test')
        
        print_top_notes(G, 'Test', top_n=2)
        captured = capsys.readouterr()
        
        assert 'Top 2 Notes' in captured.out
        assert 'PageRank' in captured.out
        assert 'Question 1' in captured.out
        assert 'Question 2' in captured.out


class TestPrintIsolatedNotes:
    """Test print_isolated_notes function."""
    
    def test_print_isolated_notes_format(self, capsys):
        """Test isolated notes output format."""
        from graph.analyze import print_isolated_notes
        import networkx as nx
        
        # Create graph with truly isolated node (no edges at all)
        G = nx.DiGraph()
        G.add_node('n1', front='Isolated', deck='Test')
        G.add_node('n2', front='Connected', deck='Test')
        # n1 has NO edges at all (truly isolated)
        # n2 also has no edges in this test
        
        print_isolated_notes(G, 'Test')
        captured = capsys.readouterr()
        
        # Should show isolated nodes
        assert 'Isolated' in captured.out or 'isolated' in captured.out


class TestExportGraph:
    """Test export_graph function."""
    
    def test_export_to_json(self, tmp_path):
        """Test exporting graph to JSON."""
        from graph.analyze import export_graph
        import networkx as nx
        
        G = nx.DiGraph()
        G.add_node('n1', front='Test', pagerank=0.5)
        G.add_edge('n1', 'n2')
        
        export_graph(G, tmp_path, format='json', deck_name='Test')
        
        # Check file was created
        files = list(tmp_path.glob('*.json'))
        assert len(files) > 0
    
    def test_export_creates_directory(self, tmp_path):
        """Test that export creates output directory."""
        from graph.analyze import export_graph
        import networkx as nx
        
        G = nx.DiGraph()
        output_dir = tmp_path / "subdir"
        
        export_graph(G, output_dir, format='json', deck_name='Test')
        
        assert output_dir.exists()


class TestMainCLI:
    """Test main CLI function."""
    
    @patch('graph.analyze.load_notes_with_decks')
    @patch('graph.analyze.build_graph')
    def test_main_with_deck_alias(self, mock_build, mock_load, capsys):
        """Test CLI with deck alias."""
        from graph.analyze import main
        import sys
        from io import StringIO
        
        # Mock data
        mock_load.return_value = [
            {'deck': '言語日語', 'guid': 'n1', 'flds': 'test', 'tags': '', 'mid': 123}
        ]
        
        mock_graph = MagicMock()
        mock_graph.nodes.return_value = []
        mock_graph.edges.return_value = []
        mock_build.return_value = mock_graph
        
        # Test with alias
        with patch.object(sys, 'argv', ['analyze', '--deck', 'J', '--top', '5']):
            try:
                main()
            except SystemExit:
                pass  # Expected after completion
        
        # Verify alias was resolved
        captured = capsys.readouterr()
        # Should mention the alias resolution or deck name
        assert '言語日語' in captured.out or 'Alias' in captured.out
    
    @patch('graph.analyze.load_notes_with_decks')
    def test_main_list_decks(self, mock_load, capsys):
        """Test CLI --list-decks option."""
        from graph.analyze import main
        import sys
        
        mock_load.return_value = [
            {'deck': 'Deck A', 'guid': 'n1'},
            {'deck': 'Deck B', 'guid': 'n2'},
        ]
        
        with patch.object(sys, 'argv', ['analyze', '--list-decks']):
            try:
                main()
            except SystemExit:
                pass
        
        captured = capsys.readouterr()
        assert 'Available Decks' in captured.out
