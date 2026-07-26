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


def test_builder_missing_coverage():
    import networkx as nx

    from graph.builder import build_graph, get_top_nodes

    # Coverage for 50->55 (tags empty with anonymization)
    notes = [{'guid': 'n1', 'tags': '', 'front': 'text'}]
    with (
        patch('graph.builder.find_references', return_value=[]),
        patch('graph.builder.get_front_field', return_value='text'),
    ):
        G = build_graph(notes, with_anonymization=True)
    assert G.nodes['n1']['tags'] == ''

    # Coverage for 85->84, 91->90 (guid not in G.nodes from pagerank)
    with (
        patch('graph.builder.find_references', return_value=[]),
        patch('graph.builder.get_front_field', return_value='text'),
        patch('graph.builder._compute_pagerank', return_value={'n1': 0.5, 'fake_guid': 0.5}),
    ):
        G2 = build_graph(notes, with_pagerank=True)
        assert 'fake_guid' not in G2.nodes

    # Coverage for 197->203 (by != 'pagerank') and 200->199 (guid not in G.nodes)
    G3 = nx.DiGraph()
    G3.add_node('n1', rank=1)
    res1 = get_top_nodes(G3, n=1, by='other_metric')
    assert len(res1) == 1

    # this will hit `if guid in G.nodes` is false path
    G4 = nx.DiGraph()
    G4.add_node('n1')
    with patch('graph.builder._compute_pagerank', return_value={'fake_guid': 0.5}):
        res2 = get_top_nodes(G4, n=1, by='pagerank')
        assert len(res2) == 1
