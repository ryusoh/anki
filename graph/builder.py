"""
Builder module for Anki knowledge graph.

Builds directed graphs from notes and computes PageRank.
"""

import networkx as nx

from graph.parser import get_front_field, group_by_deck
from graph.references import find_references


def build_graph(
    notes, with_pagerank=False, with_anonymization=False, alpha=0.85, progress_callback=None
):
    """
    Build a directed graph from notes.

    Args:
        notes: List of note dicts
        with_pagerank: Whether to compute PageRank (default: False)
        with_anonymization: Whether to hash sensitive fields (default: False)
        alpha: Damping factor for PageRank (default: 0.85)
        progress_callback: Optional callable for reference-finding progress

    Returns:
        networkx.DiGraph with nodes and weighted edges
    """
    import hashlib

    G = nx.DiGraph()
    hash_cache = {}

    def get_hash(text):
        if text not in hash_cache:
            hash_cache[text] = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return hash_cache[text]

    # Add all notes as nodes
    for note in notes:
        guid = note['guid']
        front = get_front_field(note)
        tags = note.get('tags', '')

        if with_anonymization:
            # Hash front and tags to prevent clear-text exposure
            front_hash = get_hash(front)[:12]
            front = f"Note_{front_hash}"

            if tags:
                tag_list = tags.split()
                hashed_tags = [get_hash(t)[:8] for t in tag_list]
                tags = ' '.join(hashed_tags)

        G.add_node(
            guid,
            guid=guid,
            label=front,  # Use label for display in UI
            front=front,
            deck=note.get('deck'),
            deck_id=note.get('deck_id'),
            tags=tags,
            mid=note.get('mid'),
            mod=note.get('mod'),
        )

    # Find and add edges (references)
    edges = find_references(notes, progress_callback=progress_callback)

    for edge in edges:
        G.add_edge(
            edge['source'],
            edge['target'],
            weight=edge['weight'],
            type=edge['type'],
            deck=edge.get('deck'),
        )

    # Compute PageRank if requested
    if with_pagerank:
        pagerank = _compute_pagerank(G, alpha=alpha)

        # Attach PageRank to nodes
        for guid, score in pagerank.items():
            if guid in G.nodes:
                G.nodes[guid]['pagerank'] = score

        # Add rank (1-based, sorted by PageRank descending)
        ranked = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
        for rank, (guid, _) in enumerate(ranked, 1):
            if guid in G.nodes:
                G.nodes[guid]['rank'] = rank

    return G


def _compute_pagerank(G, alpha=0.85, max_iter=100, tol=1e-06):
    """
    Compute PageRank for a graph.

    Args:
        G: networkx.DiGraph
        alpha: Damping factor (default: 0.85)
        max_iter: Maximum iterations (default: 100)
        tol: Tolerance (default: 1e-06)

    Returns:
        dict: {node_id: pagerank_score}
    """
    if len(G.nodes()) == 0:
        return {}

    try:
        pagerank = nx.pagerank(G, weight='weight', alpha=alpha, max_iter=max_iter, tol=tol)
    except nx.PowerIterationFailedConvergence:
        # If PageRank doesn't converge, use uniform distribution
        pagerank = {node: 1.0 / len(G.nodes()) for node in G.nodes()}

    return pagerank


def build_per_deck_graphs(notes, with_pagerank=False, with_anonymization=False, alpha=0.85):
    """
    Build separate graphs for each deck.

    Args:
        notes: List of note dicts
        with_pagerank: Whether to compute PageRank for each graph
        with_anonymization: Whether to hash sensitive fields
        alpha: Damping factor for PageRank

    Returns:
        dict: {deck_name: networkx.DiGraph}
    """
    grouped = group_by_deck(notes)
    graphs = {}

    for deck_name, deck_notes in grouped.items():
        G = build_graph(
            deck_notes,
            with_pagerank=with_pagerank,
            with_anonymization=with_anonymization,
            alpha=alpha,
        )
        graphs[deck_name] = G

    return graphs


def export_to_dict(G):
    """
    Export graph to dictionary format.

    Args:
        G: networkx.DiGraph

    Returns:
        dict with 'nodes' and 'edges' lists
    """
    # Optimize dict construction with list comprehensions instead of append loops
    nodes = [{'id': node_id, **data} for node_id, data in G.nodes(data=True)]
    edges = [{'source': source, 'target': target, **data} for source, target, data in G.edges(data=True)]

    return {
        'nodes': nodes,
        'edges': edges,
        'metadata': {
            'num_nodes': len(nodes),
            'num_edges': len(edges),
        },
    }


def get_top_nodes(G, n=10, by='pagerank'):
    """
    Get top N nodes by a given metric.

    Args:
        G: networkx.DiGraph
        n: Number of nodes to return
        by: Metric to sort by ('pagerank', 'rank', etc.)

    Returns:
        List of (node_id, data) tuples
    """
    if len(G.nodes()) == 0:
        return []

    if by not in G.nodes[list(G.nodes())[0]]:
        # Metric not available, compute it
        if by == 'pagerank':
            pagerank = _compute_pagerank(G)
            for guid, score in pagerank.items():
                if guid in G.nodes:
                    G.nodes[guid]['pagerank'] = score

    ranked = sorted(G.nodes(data=True), key=lambda x: x[1].get(by, 0), reverse=True)

    return ranked[:n]


def get_isolated_nodes(G):
    """
    Find isolated nodes (no incoming or outgoing edges).

    Args:
        G: networkx.DiGraph

    Returns:
        List of node IDs with no connections
    """
    isolated = []

    for node in G.nodes():
        in_degree = G.in_degree(node)
        out_degree = G.out_degree(node)

        if in_degree == 0 and out_degree == 0:
            isolated.append(node)

    return isolated


def get_hub_nodes(G, threshold=0.01):
    """
    Find hub nodes (high PageRank, many connections).

    Args:
        G: networkx.DiGraph
        threshold: Minimum PageRank to consider (default: 0.01)

    Returns:
        List of (node_id, data) tuples for hub nodes
    """
    hubs = []

    for node, data in G.nodes(data=True):
        pagerank = data.get('pagerank', 0)
        in_degree = G.in_degree(node)

        if pagerank >= threshold and in_degree > 0:
            hubs.append(
                (
                    node,
                    {
                        **data,
                        'in_degree': in_degree,
                        'out_degree': G.out_degree(node),
                    },
                )
            )

    # Sort by PageRank descending
    hubs.sort(key=lambda x: x[1]['pagerank'], reverse=True)

    return hubs
