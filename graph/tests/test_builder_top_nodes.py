from unittest.mock import patch

import networkx as nx

from graph.builder import get_top_nodes


def test_missing_pagerank():
    G = nx.DiGraph()
    G.add_node("n1")
    G.add_node("n2")

    with patch('graph.builder._compute_pagerank') as mock_compute:
        mock_compute.return_value = {"n1": 0.8, "n2": 0.2}
        res = get_top_nodes(G, n=5, by='pagerank')
        assert len(res) == 2
        assert res[0][0] == "n1"
        assert res[0][1]['pagerank'] == 0.8


def test_empty_graph():
    G = nx.DiGraph()
    res = get_top_nodes(G, n=5, by='pagerank')
    assert res == []


def test_compute_pagerank_empty():
    from graph.builder import _compute_pagerank

    G = nx.DiGraph()
    res = _compute_pagerank(G)
    assert res == {}


def test_compute_pagerank_no_convergence():
    from graph.builder import _compute_pagerank

    G = nx.DiGraph()
    G.add_node("n1")
    G.add_node("n2")

    with patch('networkx.pagerank', side_effect=nx.PowerIterationFailedConvergence(100)):
        res = _compute_pagerank(G)
        assert res == {"n1": 0.5, "n2": 0.5}
