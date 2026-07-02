"""
Tests for graph CLI (analyze.py).
Tests command-line interface, deck aliases, and output formatting.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import networkx as nx
import pytest


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
        import gzip
        import json

        from graph.analyze import build_deck_map_from_cards

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
        import gzip
        import json

        from graph.analyze import build_deck_map_from_cards

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
        import gzip
        import json

        from graph.analyze import load_notes_from_file

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
        import json

        from graph.analyze import load_notes_from_file

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

    def test_print_isolated_notes_empty(self, capsys):
        from graph.analyze import print_isolated_notes

        G = nx.DiGraph()
        print_isolated_notes(G, "Test Deck")
        assert "No isolated notes" in capsys.readouterr().out

    def test_print_isolated_notes_truncation(self, capsys):
        from graph.analyze import print_isolated_notes

        G = nx.DiGraph()
        for i in range(25):
            G.add_node(f"node_{i}", front=f"Node {i}")
        print_isolated_notes(G, "Test Deck")
        out = capsys.readouterr().out
        assert "Isolated Notes in Test Deck" in out
        assert "and 5 more" in out


class TestPrintHubNotes:
    """Test print_hub_notes function."""

    def test_print_hub_notes_empty(self, capsys):
        from graph.analyze import print_hub_notes

        G = nx.DiGraph()
        print_hub_notes(G, "Test Deck")
        assert "No hub notes found" in capsys.readouterr().out

    def test_print_hub_notes_truncation(self, capsys):
        from graph.analyze import print_hub_notes

        G = nx.DiGraph()
        G.add_node("n1", front="A" * 40, pagerank=0.5)
        G.add_node("n2", front="B" * 40, pagerank=0.1)
        G.add_edge("n1", "n2")
        G.add_edge("n2", "n1")
        print_hub_notes(G, "Test Deck")
        out = capsys.readouterr().out
        assert "Hub Notes in Test Deck" in out
        assert "AAAAAAAAAAAAAAAAAAAAAAAAAAAA.." in out
        assert "BBBBBBBBBBBBBBBBBBBBBBBBBBBB.." in out


class TestExportGraph:
    """Test export_graph function."""

    def test_export_to_json(self, tmp_path):
        """Test exporting graph to JSON."""
        from graph.analyze import export_graph

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
        import sys
        from io import StringIO

        from graph.analyze import main

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
        import sys

        from graph.analyze import main

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


def test_export_to_graphml(tmp_path, capsys):
    from graph.analyze import export_graph

    G = nx.DiGraph()
    G.add_node('n1', front='Test', pagerank=0.5)
    G.add_edge('n1', 'n2')

    export_graph(G, tmp_path, format='graphml', deck_name='TestDeck')

    files = list(tmp_path.glob('*.graphml'))
    assert len(files) == 1
    assert "TestDeck" in files[0].name

    captured = capsys.readouterr()
    assert "Exported to" in captured.out


def test_export_unknown_format(tmp_path, capsys):
    from graph.analyze import export_graph

    G = nx.DiGraph()
    export_graph(G, tmp_path, format='unknown_format', deck_name='Test')

    captured = capsys.readouterr()
    assert "Unknown format: unknown_format" in captured.err


def test_compare_decks(capsys):
    from graph.analyze import compare_decks

    G1 = nx.DiGraph()
    G1.add_node('n1', front='Test Node 1', pagerank=0.5)
    G1.add_node('n2', front='Test Node 2', pagerank=0.3)
    G1.add_edge('n1', 'n2')

    G2 = nx.DiGraph()

    G3 = nx.DiGraph()
    G3.add_node(
        'n3', front='Very long name that should be truncated for display purposes', pagerank=0.9
    )

    graphs = {'Deck 1': G1, 'Empty Deck': G2, 'Deck 3': G3}

    compare_decks(graphs)

    captured = capsys.readouterr()
    assert "Deck Comparison" in captured.out
    assert "Deck 1" in captured.out
    assert "Empty Deck" in captured.out
    assert "Deck 3" in captured.out
    assert "Test Node 1" in captured.out
    assert "N/A" in captured.out
    assert "Very long name that should be truncat" in captured.out


def test_print_hub_notes(capsys):
    from graph.analyze import print_hub_notes

    G = nx.DiGraph()
    G.add_node('n0')
    G.add_node('n1', front='Test Node 1', pagerank=0.05)
    G.add_edge('n0', 'n1')
    G.add_node('n2', front='Test Node 2', pagerank=0.001)
    G.add_edge('n1', 'n2')
    G.add_node('n3', front='Very long name that should be truncated', pagerank=0.02)
    G.add_edge('n0', 'n3')

    print_hub_notes(G, deck_name='Test Deck', threshold=0.01)

    captured = capsys.readouterr()
    assert "Hub Notes in Test Deck" in captured.out
    assert "Test Node 1" in captured.out
    assert "Test Node 2" not in captured.out
    assert "Very long name that should b.." in captured.out


def test_print_hub_notes_empty(capsys):
    from graph.analyze import print_hub_notes

    G = nx.DiGraph()

    print_hub_notes(G, deck_name='Empty Deck', threshold=0.01)

    captured = capsys.readouterr()
    assert "No hub notes found in Empty Deck" in captured.out


def test_analyze_single_deck(capsys):
    from graph.analyze import analyze_single_deck

    args = MagicMock()
    args.deck = 'Deck A'
    args.anonymize = False
    args.top = 10
    args.isolated = True
    args.hubs = True
    args.export = '/tmp/export'
    args.format = 'json'

    decks = ['Deck A', 'Deck B']
    notes = [{'deck': 'Deck A', 'guid': 'n1', 'flds': 'front\x1fback', 'tags': '', 'mid': 1}]

    with (
        patch('graph.analyze.build_graph') as mock_build,
        patch('graph.analyze.print_top_notes') as mock_print_top,
        patch('graph.analyze.print_isolated_notes') as mock_print_isolated,
        patch('graph.analyze.print_hub_notes') as mock_print_hub,
        patch('graph.analyze.export_graph') as mock_export,
    ):

        graph_mock = MagicMock()
        mock_build.return_value = graph_mock

        analyze_single_deck(args, decks, notes)

        mock_build.assert_called_once()
        mock_print_top.assert_called_once_with(graph_mock, 'Deck A', 10)
        mock_print_isolated.assert_called_once_with(graph_mock, 'Deck A')
        mock_print_hub.assert_called_once_with(graph_mock, 'Deck A')
        mock_export.assert_called_once_with(graph_mock, '/tmp/export', 'json', 'Deck_A')


def test_analyze_single_deck_deck_not_found(capsys):
    from graph.analyze import analyze_single_deck

    args = MagicMock()
    args.deck = 'Deck C'
    decks = ['Deck A', 'Deck B']
    notes = []

    try:
        analyze_single_deck(args, decks, notes)
    except SystemExit:
        pass

    captured = capsys.readouterr()
    assert "Deck not found: Deck C" in captured.err


def test_analyze_all_decks(capsys):
    from graph.analyze import analyze_all_decks

    args = MagicMock()
    args.anonymize = False
    args.compare = True
    args.top = 10
    args.isolated = True
    args.hubs = True
    args.export = '/tmp/export'
    args.format = 'json'

    decks = ['Deck A', 'Deck B']
    notes = [
        {'deck': 'Deck A', 'guid': 'n1', 'flds': 'front\x1fback', 'tags': '', 'mid': 1},
        {'deck': 'Deck B', 'guid': 'n2', 'flds': 'front2\x1fback2', 'tags': '', 'mid': 2},
    ]

    with (
        patch('graph.analyze.build_per_deck_graphs') as mock_build_per_deck,
        patch('graph.analyze.compare_decks') as mock_compare,
        patch('graph.analyze.print_top_notes') as mock_print_top,
        patch('graph.analyze.print_isolated_notes') as mock_print_isolated,
        patch('graph.analyze.print_hub_notes') as mock_print_hub,
        patch('graph.analyze.export_graph') as mock_export,
    ):

        graph_a = MagicMock()
        graph_b = MagicMock()
        mock_graphs = {'Deck A': graph_a, 'Deck B': graph_b}
        mock_build_per_deck.return_value = mock_graphs

        analyze_all_decks(args, decks, notes)

        mock_build_per_deck.assert_called_once_with(
            notes, with_pagerank=True, with_anonymization=False
        )
        mock_compare.assert_called_once_with(mock_graphs)
        assert mock_print_top.call_count == 2
        assert mock_print_isolated.call_count == 2
        assert mock_print_hub.call_count == 2
        assert mock_export.call_count == 2


@patch('graph.analyze.Path')
@patch('graph.analyze.load_notes_from_file')
@patch('graph.analyze.build_deck_map_from_cards')
def test_load_notes_with_decks_r2(mock_build, mock_load, mock_path):
    mock_r2_staged = (
        mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value
    )
    mock_r2_staged.exists.return_value = True
    mock_load.return_value = [{'id': 1}]

    from graph.analyze import load_notes_with_decks

    notes = load_notes_with_decks()
    assert notes == [{'id': 1}]


@patch('graph.analyze.Path')
@patch('graph.analyze.load_notes_from_file')
@patch('graph.analyze.build_deck_map_from_cards')
def test_load_notes_with_decks_github(mock_build, mock_load, mock_path):
    # Mock R2 staging path does not exist
    mock_r2_staged = (
        mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value
    )
    mock_r2_staged.exists.return_value = False

    # Mock GitHub fallback path exists
    mock_github_data = (
        mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value
    )
    mock_github_data.exists.return_value = True

    mock_load.return_value = [{'id': 1}]
    mock_build.return_value = {1: {'deck_name': 'Test Deck', 'did': 123}}

    from graph.analyze import load_notes_with_decks

    notes = load_notes_with_decks()
    assert len(notes) == 1
    assert notes[0]['id'] == 1
    assert notes[0]['deck'] == 'Test Deck'
    assert notes[0]['deck_id'] == 123


@patch('graph.analyze.Path')
def test_load_notes_with_decks_none(mock_path, capsys):
    mock_r2_staged = (
        mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value
    )
    mock_r2_staged.exists.return_value = False
    mock_github_data = (
        mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value
    )
    mock_github_data.exists.return_value = False

    from graph.analyze import load_notes_with_decks

    notes = load_notes_with_decks()
    assert notes == []

    captured = capsys.readouterr()
    assert "No notes found" in captured.err


import networkx as nx
import pytest


def test_export_to_json(tmp_path, capsys):
    from graph.analyze import export_graph

    G = nx.DiGraph()
    G.add_node('n1', front='Test', pagerank=0.5)
    G.add_edge('n1', 'n2')

    export_graph(G, tmp_path, format='json', deck_name='TestDeck')

    files = list(tmp_path.glob('*.json'))
    assert len(files) == 1
    assert "TestDeck" in files[0].name

    captured = capsys.readouterr()
    assert "Exported to" in captured.out
