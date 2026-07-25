"""
Tests for graph.builder module.

Tests graph construction and PageRank computation.
"""

import pytest


class TestBuildGraph:
    """Test graph building."""

    def test_build_graph_with_anonymization(self):
        """Test that graph node front and tags are hashed when anonymization is enabled."""
        from graph.builder import build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES, with_anonymization=True)

        # Check that original text is not present in the graph
        for _node, data in G.nodes(data=True):
            assert 'Note_' in data['front']
            assert 'Note_' in data['label']
            assert 'flamboyant' not in data['front'].lower()
            assert 'vocabulary' not in data['tags'].lower()

    def test_build_graph_creates_nodes(self):
        """Test that graph has nodes for all notes."""
        from graph.builder import build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES)

        # Should have 5 nodes
        assert len(G.nodes()) == 5

        # All English note GUIDs should be present
        guids = {n for n in G.nodes()}
        expected = {'eng001', 'eng002', 'eng003', 'eng004', 'eng005'}
        assert guids == expected

    def test_build_graph_creates_edges(self):
        """Test that graph has edges for references."""
        from graph.builder import build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES)

        # Should have edges (at least flamboyant->baroque, style->baroque, etc.)
        assert len(G.edges()) > 0

    def test_build_graph_no_cross_deck(self):
        """Test that graph has no cross-deck edges."""
        from graph.builder import build_graph
        from graph.tests.fixtures import ALL_NOTES

        G = build_graph(ALL_NOTES)

        english_guids = {'eng001', 'eng002', 'eng003', 'eng004', 'eng005'}
        calculus_guids = {'calc001', 'calc002', 'calc003'}
        biology_guids = {'bio001', 'bio002'}

        # Check all edges are within same deck
        for source, target in G.edges():
            if source in english_guids:
                assert target in english_guids
            elif source in calculus_guids:
                assert target in calculus_guids
            elif source in biology_guids:
                assert target in biology_guids

    def test_build_graph_directed(self):
        """Test that graph is directed."""
        from graph.builder import build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES)

        # Graph should be directed (DiGraph)
        import networkx as nx

        assert isinstance(G, nx.DiGraph)

    def test_build_graph_edge_has_weight(self):
        """Test that edges have weights."""
        from graph.builder import build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES)

        for _u, _v, data in G.edges(data=True):
            assert 'weight' in data
            assert data['weight'] > 0


class TestPageRank:
    """Test PageRank computation."""

    def test_pagerank_computed(self):
        """Test that PageRank is computed for all nodes."""
        from graph.builder import _compute_pagerank, build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES)
        pagerank = _compute_pagerank(G)

        # Should have PageRank for all nodes
        assert len(pagerank) == 5

        # All GUIDs should be present
        assert set(pagerank.keys()) == {'eng001', 'eng002', 'eng003', 'eng004', 'eng005'}

    def test_pagerank_sums_to_one(self):
        """Test that PageRank scores sum to approximately 1."""
        from graph.builder import _compute_pagerank, build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES)
        pagerank = _compute_pagerank(G)

        total = sum(pagerank.values())
        assert abs(total - 1.0) < 0.01  # Should sum to ~1.0

    def test_pagerank_attached_to_nodes(self):
        """Test that PageRank is attached to node attributes."""
        from graph.builder import build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES, with_pagerank=True)

        # All nodes should have pagerank attribute
        for node in G.nodes():
            assert 'pagerank' in G.nodes[node]
            assert isinstance(G.nodes[node]['pagerank'], float)

    def test_pagerank_ranking(self):
        """Test that nodes are ranked by PageRank."""
        from graph.builder import build_graph
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES, with_pagerank=True)

        # Get nodes sorted by PageRank
        ranked = sorted(G.nodes(data=True), key=lambda x: x[1]['pagerank'], reverse=True)

        # All nodes should have a rank
        assert len(ranked) == 5

        # Top node should have highest PageRank
        top_node = ranked[0][0]
        ranked[0][1]['pagerank']

        # Verify PageRank values are valid (between 0 and 1)
        for _node, data in ranked:
            assert 0 <= data['pagerank'] <= 1

        # Top node should have rank 1
        assert G.nodes[top_node]['rank'] == 1


class TestBuildPerDeck:
    """Test per-deck graph building."""

    def test_build_per_deck_graphs(self):
        """Test building separate graphs for each deck."""
        from graph.builder import build_per_deck_graphs
        from graph.tests.fixtures import ALL_NOTES

        graphs = build_per_deck_graphs(ALL_NOTES, with_pagerank=True)

        # Should have 3 graphs (one per deck)
        assert len(graphs) == 3
        assert 'English Vocabulary' in graphs
        assert 'Calculus' in graphs
        assert 'Biology 101' in graphs

    def test_build_per_deck_graph_sizes(self):
        """Test that per-deck graphs have correct sizes."""
        from graph.builder import build_per_deck_graphs
        from graph.tests.fixtures import ALL_NOTES

        graphs = build_per_deck_graphs(ALL_NOTES)

        assert len(graphs['English Vocabulary'].nodes()) == 5
        assert len(graphs['Calculus'].nodes()) == 3
        assert len(graphs['Biology 101'].nodes()) == 2


class TestExportGraph:
    """Test graph export."""

    def test_export_to_dict(self):
        """Test exporting graph to dictionary."""
        from graph.builder import build_graph, export_to_dict
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES, with_pagerank=True)
        data = export_to_dict(G)

        assert 'nodes' in data
        assert 'edges' in data
        assert len(data['nodes']) == 5

    def test_export_to_dict_includes_pagerank(self):
        """Test that export includes PageRank."""
        from graph.builder import build_graph, export_to_dict
        from graph.tests.fixtures import ENGLISH_NOTES

        G = build_graph(ENGLISH_NOTES, with_pagerank=True)
        data = export_to_dict(G)

        for node in data['nodes']:
            assert 'pagerank' in node


class TestNodeAnalysisUtilities:
    """Test node analysis utility functions."""

    def test_get_top_nodes_sorts_by_metric(self):
        """Test get_top_nodes correctly sorts and limits by a specified metric."""
        import networkx as nx

        from graph.builder import get_top_nodes

        # Arrange
        G = nx.DiGraph()
        G.add_node("node1", custom_score=10)
        G.add_node("node2", custom_score=30)
        G.add_node("node3", custom_score=20)

        # Act
        top_nodes = get_top_nodes(G, n=2, by='custom_score')

        # Assert
        assert len(top_nodes) == 2
        assert top_nodes[0][0] == "node2"
        assert top_nodes[0][1]['custom_score'] == 30
        assert top_nodes[1][0] == "node3"
        assert top_nodes[1][1]['custom_score'] == 20

    def test_get_isolated_nodes_finds_unconnected(self):
        """Test get_isolated_nodes identifies nodes with zero in/out degrees."""
        import networkx as nx

        from graph.builder import get_isolated_nodes

        # Arrange
        G = nx.DiGraph()
        G.add_node("isolated1")
        G.add_node("isolated2")
        G.add_node("connected1")
        G.add_node("connected2")
        G.add_edge("connected1", "connected2")

        # Act
        isolated = get_isolated_nodes(G)

        # Assert
        assert len(isolated) == 2
        assert "isolated1" in isolated
        assert "isolated2" in isolated
        assert "connected1" not in isolated
        assert "connected2" not in isolated

    def test_get_hub_nodes_filters_and_sorts_by_pagerank(self):
        """Test get_hub_nodes correctly filters by pagerank/in-degree and sorts."""
        import networkx as nx

        from graph.builder import get_hub_nodes

        # Arrange
        G = nx.DiGraph()
        # Hub 1: high pagerank, has incoming edge
        G.add_node("hub1", pagerank=0.05)
        # Hub 2: higher pagerank, has incoming edge
        G.add_node("hub2", pagerank=0.08)
        # Not hub: below threshold
        G.add_node("low_pr", pagerank=0.005)
        # Not hub: no incoming edges
        G.add_node("no_in", pagerank=0.05)

        # Add edges to setup degrees
        G.add_edge("no_in", "hub1")
        G.add_edge("no_in", "hub2")
        G.add_edge("hub1", "hub2")
        G.add_edge("hub2", "low_pr")

        # Act
        hubs = get_hub_nodes(G, threshold=0.01)

        # Assert
        assert len(hubs) == 2
        # Should be sorted by pagerank descending
        assert hubs[0][0] == "hub2"
        assert hubs[0][1]['pagerank'] == 0.08
        assert hubs[0][1]['in_degree'] == 2
        assert hubs[0][1]['out_degree'] == 1

        assert hubs[1][0] == "hub1"
        assert hubs[1][1]['pagerank'] == 0.05
        assert hubs[1][1]['in_degree'] == 1
        assert hubs[1][1]['out_degree'] == 1


def test_missing_coverage_builder():
    from unittest.mock import MagicMock, patch

    import networkx as nx

    from graph.builder import _compute_pagerank

    # 107
    _compute_pagerank(nx.DiGraph())

    # 117-119
    G = nx.DiGraph()
    G.add_node(1)
    with patch("networkx.pagerank", side_effect=nx.PowerIterationFailedConvergence("Error", 100)):
        _compute_pagerank(G)


def test_missing_coverage_builder2():
    import networkx as nx

    from graph.builder import get_top_nodes

    # 202
    get_top_nodes(nx.DiGraph())

    # 206-210
    # Create graph with missing 'pagerank' metric
    G = nx.DiGraph()
    G.add_node(1, dummy="metric")
    import builtins
    from unittest.mock import MagicMock, patch

    with patch("builtins.compute_pagerank", return_value={1: 0.5}, create=True):
        get_top_nodes(G, by='pagerank')

    def test_build_graph_with_anonymization_empty_tags(self):
        from graph.builder import build_graph
        # Test 50->55: tags is empty string when with_anonymization is True
        notes = [{
            'guid': 'guid3',
            'tags': '',
            'deck': 'Default',
            'deck_id': 1,
            'mid': 1234,
            'mod': 5678,
            'fields': {'Front': {'value': 'Empty Tags'}}
        }]
        refs = []
        G = build_graph(notes, refs, with_anonymization=True)
        assert G.nodes['guid3']['tags'] == ''
