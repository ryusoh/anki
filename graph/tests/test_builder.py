"""
Tests for graph.builder module.

Tests graph construction and PageRank computation.
"""

import pytest


class TestBuildGraph:
    """Test graph building."""
    
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
        
        for u, v, data in G.edges(data=True):
            assert 'weight' in data
            assert data['weight'] > 0


class TestPageRank:
    """Test PageRank computation."""
    
    def test_pagerank_computed(self):
        """Test that PageRank is computed for all nodes."""
        from graph.builder import build_graph, _compute_pagerank
        from graph.tests.fixtures import ENGLISH_NOTES
        
        G = build_graph(ENGLISH_NOTES)
        pagerank = _compute_pagerank(G)
        
        # Should have PageRank for all nodes
        assert len(pagerank) == 5
        
        # All GUIDs should be present
        assert set(pagerank.keys()) == {'eng001', 'eng002', 'eng003', 'eng004', 'eng005'}
    
    def test_pagerank_sums_to_one(self):
        """Test that PageRank scores sum to approximately 1."""
        from graph.builder import build_graph, _compute_pagerank
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
        ranked = sorted(
            G.nodes(data=True),
            key=lambda x: x[1]['pagerank'],
            reverse=True
        )
        
        # All nodes should have a rank
        assert len(ranked) == 5
        
        # Top node should have highest PageRank
        top_node = ranked[0][0]
        top_pagerank = ranked[0][1]['pagerank']
        
        # Verify PageRank values are valid (between 0 and 1)
        for node, data in ranked:
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
