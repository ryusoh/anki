#!/usr/bin/env python3
"""Export graph data for JavaScript visualization.

Usage:
    python3 graph/export_data.py           # default 2000 nodes
    python3 graph/export_data.py 500       # 500 nodes
    python3 graph/export_data.py all       # all nodes
    python3 graph/export_data.py --public    # strip sensitive content
    python3 graph/export_data.py --full    # force full rebuild (skip cache)
"""

import gzip
import hashlib
import json
import logging
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21')
from fa2_modified import ForceAtlas2

from graph.builder import build_graph

BASE = Path('/Users/lz/Library/Application Support/Anki2/addons21')
NOTES_FILE = BASE / 'data/cloudflare/collection/notes.json.gz'
OUTPUT_FILE = BASE / 'graph/graph_data.json'
CACHE_FILE = BASE / 'graph/.export_cache.json'


def strip_html(text):
    """Remove HTML tags and entities from text."""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&apos;', "'")
    text = text.replace('::', ' ').replace('\n', ' ')
    return ' '.join(text.split())[:60]


def progress_bar(current, total, prefix='', width=40):
    """Print a progress bar to stderr."""
    pct = current / total if total > 0 else 1
    filled = int(width * pct)
    bar = '█' * filled + '░' * (width - filled)
    sys.stderr.write(f'\r  {prefix} [{bar}] {current}/{total} ({pct:.0%})')
    sys.stderr.flush()
    if current == total:
        sys.stderr.write('\n')


def note_fingerprint(note):
    """Hash a note's content for change detection."""
    key = f"{note['guid']}:{note.get('mod', '')}:{note.get('flds', '')}:{note.get('deck', '')}"
    return hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()[:12]


def load_cache():
    """Load the export cache (processed note fingerprints per deck)."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            logging.getLogger(__name__).warning(
                "Failed to load export cache: JSON decode error or missing key."
            )
    return None


def save_cache(notes, node_count, link_count, output_file=None):
    """Save cache with guid→fingerprint mapping per deck."""
    deck_data = {}
    for note in notes:
        deck = note.get('deck', 'Unknown')
        if deck not in deck_data:
            deck_data[deck] = {}
        deck_data[deck][note['guid']] = note_fingerprint(note)

    cache = {
        'version': 4,
        'note_count': len(notes),
        'node_count': node_count,
        'link_count': link_count,
        'decks': deck_data,
    }
    if output_file:
        cache['output_file'] = str(output_file)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)


def find_changed_notes(notes, cache, output_file=None):
    """
    Compare current notes against cache to find exactly which notes changed per deck.

    Returns:
        None if full rebuild needed,
        dict {deck: {'new_guids': set, 'removed_guids': set, 'modified_guids': set}} otherwise.
        Decks with no changes are omitted.
    """
    if not cache or cache.get('version') != 4:
        return None  # full rebuild

    # Invalidate cache if it was built for a different output file
    if output_file:
        cached_output = cache.get('output_file')
        if cached_output and str(output_file) != cached_output:
            return None  # full rebuild

    # Build current guid→fingerprint per deck
    current = {}
    guid_to_note = {}
    for note in notes:
        deck = note.get('deck', 'Unknown')
        if deck not in current:
            current[deck] = {}
        current[deck][note['guid']] = note_fingerprint(note)
        guid_to_note[note['guid']] = note

    cached_decks = cache.get('decks', {})
    changes = {}

    for deck, cur_guids in current.items():
        cached_guids = cached_decks.get(deck, {})
        new_guids = set(cur_guids.keys()) - set(cached_guids.keys())
        removed_guids = set(cached_guids.keys()) - set(cur_guids.keys())
        modified_guids = {
            g
            for g in set(cur_guids.keys()) & set(cached_guids.keys())
            if cur_guids[g] != cached_guids[g]
        }

        if new_guids or removed_guids or modified_guids:
            print(
                f'  Deck "{deck}": +{len(new_guids)} new, ~{len(modified_guids)} modified, -{len(removed_guids)} removed'
            )
            changes[deck] = {
                'new_guids': new_guids,
                'removed_guids': removed_guids,
                'modified_guids': modified_guids,
            }

    # Check for deleted decks
    for deck in cached_decks:
        if deck not in current:
            changes[deck] = {
                'new_guids': set(),
                'removed_guids': set(cached_decks[deck].keys()),
                'modified_guids': set(),
            }

    return changes


def deck_progress(deck_name, deck_idx, total_decks, deck_size):
    """Progress callback for reference finding."""
    short_name = deck_name[:30] + '…' if len(deck_name) > 30 else deck_name
    progress_bar(deck_idx + 1, total_decks, f'Refs: {short_name} ({deck_size} notes)')


def _compute_deck_layout(subgraph, iterations):
    """Compute FA2 layout for a single deck subgraph, centered at origin."""
    node_list = list(subgraph.nodes())
    if len(node_list) == 0:
        return {}
    if len(node_list) == 1:
        return {node_list[0]: (0.0, 0.0)}

    fa2 = ForceAtlas2(
        outboundAttractionDistribution=True,
        edgeWeightInfluence=1.0,
        jitterTolerance=1.0,
        barnesHutOptimize=True,
        barnesHutTheta=1.2,
        scalingRatio=2.0,
        strongGravityMode=False,
        gravity=1.0,
        verbose=False,
    )

    positions = fa2.forceatlas2_networkx_layout(subgraph, pos=None, iterations=iterations)

    coords = np.array([positions[nid] for nid in node_list])
    coords -= coords.mean(axis=0)
    # Scale so 95th percentile radius matches cube-root of node count
    # This gives each deck a size proportional to its volume
    dists = np.linalg.norm(coords, axis=1)
    p95 = np.percentile(dists, 95) if len(dists) > 1 else 1.0
    target_radius = max(50, np.cbrt(len(node_list)) * 30)
    if p95 > 0:
        coords *= target_radius / p95

    return {nid: (float(coords[i][0]), float(coords[i][1])) for i, nid in enumerate(node_list)}


def compute_layout(graph, iterations=50):
    """
    Compute per-deck ForceAtlas2 layouts, then arrange decks
    on a Fibonacci sphere in 3D so they don't overlap.

    Returns dict: {node_id: (x, y, z)}
    """
    # Group nodes by deck
    decks = {}
    for nid, ndata in graph.nodes(data=True):
        deck = ndata.get('deck', 'Unknown')
        if deck not in decks:
            decks[deck] = []
        decks[deck].append(nid)

    deck_names = sorted(decks.keys(), key=lambda d: len(decks[d]), reverse=True)
    total = len(deck_names)

    # Fibonacci sphere centers for deck placement
    golden_angle = np.pi * (3 - np.sqrt(5))
    deck_centers = {}
    deck_radii = {}
    for i, deck in enumerate(deck_names):
        y = 1 - (2 * i + 1) / total
        r_at_y = np.sqrt(1 - y * y)
        theta = golden_angle * i
        deck_centers[deck] = np.array(
            [
                np.cos(theta) * r_at_y,
                y,
                np.sin(theta) * r_at_y,
            ]
        )
        deck_radii[deck] = max(50, np.cbrt(len(decks[deck])) * 30)

    # Spacing: scale sphere so decks don't overlap
    max_radius = max(deck_radii.values())
    sphere_radius = max_radius * total * 0.4

    all_positions = {}

    import concurrent.futures

    with concurrent.futures.ProcessPoolExecutor() as executor:
        future_to_deck = {}
        for _i, deck in enumerate(deck_names):
            deck_nodes = decks[deck]
            # Copy subgraph so pickling to workers doesn't send the entire graph
            subgraph = graph.subgraph(deck_nodes).copy()
            n = len(deck_nodes)
            iters = max(10, min(iterations, iterations * 5000 // max(n, 1)))
            future_to_deck[executor.submit(_compute_deck_layout, subgraph, iters)] = deck

        completed = 0
        for future in concurrent.futures.as_completed(future_to_deck):
            deck = future_to_deck[future]
            layout_2d = future.result()

            completed += 1
            short = deck[:30] + '…' if len(deck) > 30 else deck
            progress_bar(completed, total, f'Layout: {short}')

            # Place deck's 2D layout on a tangent plane at the sphere surface
            center_3d = deck_centers[deck] * sphere_radius

            # Create a local coordinate frame on the sphere surface
            normal = deck_centers[deck]  # unit normal pointing outward
            # Pick an arbitrary vector not parallel to normal
            up = np.array([0, 1, 0]) if abs(normal[1]) < 0.9 else np.array([1, 0, 0])
            tangent_x = np.cross(normal, up)
            tangent_x /= np.linalg.norm(tangent_x)
            tangent_y = np.cross(normal, tangent_x)
            tangent_y /= np.linalg.norm(tangent_y)

            for nid, (lx, ly) in layout_2d.items():
                r2d_sq = lx**2 + ly**2
                R_sq = deck_radii[deck] ** 2
                # Calculate max possible Z to form a spherical cluster
                max_z = np.sqrt(max(0, R_sq - r2d_sq))
                # Distribute Z randomly within that spherical bounds to inflate the 2D layout into a 3D ball
                lz = (np.random.random() * 2 - 1) * max_z

                pos = center_3d + tangent_x * lx + tangent_y * ly + normal * lz
                all_positions[nid] = (float(pos[0]), float(pos[1]), float(pos[2]))

    sys.stderr.write('\n')
    return all_positions


if __name__ == '__main__':
    # Parse arguments
    force_full = '--full' in sys.argv
    is_public = '--public' in sys.argv
    relayout_only = '--relayout' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    arg = args[0] if args else '2000'

    if is_public:
        OUTPUT_FILE = BASE / 'graph/graph_data_public.json'
        print("💡 Public Mode: Stripping sensitive card content (labels)")

    if relayout_only:
        print(f"Loading existing {OUTPUT_FILE} for layout recalculation...")
        if not OUTPUT_FILE.exists():
            print(f"Error: {OUTPUT_FILE} not found. Cannot re-layout without existing data.")
            sys.exit(1)

        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        nodes = data.get('nodes', [])
        links = data.get('links', [])

        print(f"Rebuilding networkx graph from {len(nodes)} nodes and {len(links)} links...")
        import networkx as nx

        G = nx.DiGraph()
        for n in nodes:
            G.add_node(n['id'], deck=n.get('deck', 'Unknown'))
        for link in links:
            G.add_edge(link['source'], link['target'], weight=link.get('weight', 1))

        n_nodes = len(G.nodes())
        iters = 30 if n_nodes > 50000 else 50 if n_nodes > 10000 else 100
        print(f"Computing 3D sphere layout ({iters} iterations)...")

        t_layout = time.time()
        layout = compute_layout(G, iterations=iters)
        print(f"  Layout computed in {time.time() - t_layout:.1f}s")

        print("Updating node coordinates...")
        for n in nodes:
            node_id = n['id']
            x, y, z = layout.get(node_id, (0, 0, 0))
            n['x'] = round(x, 2)
            n['y'] = round(y, 2)
            n['z'] = round(z, 2)

        print(f"Saving to {OUTPUT_FILE}...")
        t2 = time.time()
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(
                {'nodes': nodes, 'links': links}, f, ensure_ascii=False, separators=(',', ':')
            )
        print(f"  Written in {time.time() - t2:.1f}s")
        print("Done!")
        sys.exit(0)

    print('Loading notes...')
    t0 = time.time()
    with gzip.open(NOTES_FILE, 'rt') as f:
        all_notes = json.load(f)
    print(f'  Loaded {len(all_notes)} notes in {time.time() - t0:.1f}s')

    if arg == 'all':
        sample_notes = all_notes
    else:
        n = int(arg)
        sample_notes = all_notes[:n]

    print(f'Using {len(sample_notes)} / {len(all_notes)} notes')

    # --- Incremental check ---
    cache = load_cache() if not force_full else None
    changes = (
        find_changed_notes(sample_notes, cache, output_file=str(OUTPUT_FILE)) if cache else None
    )

    if changes is not None and len(changes) == 0 and OUTPUT_FILE.exists():
        print(f"No changes detected — {OUTPUT_FILE.name} is up to date.")
        if cache:
            print(f'  ({cache["node_count"]} nodes, {cache["link_count"]} links)')
        print("  Use --full to force rebuild.")
        sys.exit(0)

    if changes is not None and OUTPUT_FILE.exists():
        from graph.parser import get_front_field
        from graph.references import find_references_incremental

        # Collect all changed guids (new + modified + removed) across all decks
        all_changed_guids = set()
        all_removed_guids = set()
        changed_decks = set(changes.keys())
        for _deck, ch in changes.items():
            all_changed_guids |= ch['new_guids'] | ch['modified_guids']
            all_removed_guids |= ch['removed_guids']

        total_changed = len(all_changed_guids)
        total_removed = len(all_removed_guids)
        print(
            f'Incremental: {total_changed} changed + {total_removed} removed notes across {len(changed_decks)} deck(s)'
        )

        # Load existing output
        with open(OUTPUT_FILE, 'r') as f:
            existing = json.load(f)
        existing_nodes = {n['id']: n for n in existing['nodes']}
        existing_links = existing['links']

        # Remove nodes that were deleted or modified (will be re-added)
        remove_ids = all_removed_guids | all_changed_guids
        kept_nodes = [nd for nd in existing['nodes'] if nd['id'] not in remove_ids]
        # Remove edges involving removed/changed nodes
        kept_links = [
            lk
            for lk in existing_links
            if lk.get('source', lk.get('s')) not in remove_ids
            and lk.get('target', lk.get('t')) not in remove_ids
        ]

        # Build notes lookup
        notes_by_guid = {n['guid']: n for n in sample_notes}

        # Process each changed deck
        t1 = time.time()
        for deck, ch in changes.items():
            changed_guids = ch['new_guids'] | ch['modified_guids']
            if not changed_guids:
                continue

            # Get ALL notes in this deck for reference scanning
            all_deck_notes = [n for n in sample_notes if n.get('deck') == deck]

            # Find references involving changed notes only
            print(
                f'  Scanning refs for {len(changed_guids)} changed notes in "{deck}" ({len(all_deck_notes)} total)...'
            )
            new_edges = find_references_incremental(all_deck_notes, changed_guids, deck)

            # Add new nodes with existing positions as hint (place near deck centroid)
            # Find centroid of existing nodes in this deck
            deck_existing = [nd for nd in kept_nodes if nd.get('deck', nd.get('d')) == deck]
            if deck_existing:
                cx = float(np.mean([nd.get('x', 0) for nd in deck_existing]))
                cy = float(np.mean([nd.get('y', 0) for nd in deck_existing]))
                cz = float(np.mean([nd.get('z', 0) for nd in deck_existing]))
            else:
                cx, cy, cz = 0.0, 0.0, 0.0

            # Compute average pagerank for the deck as default
            deck_pageranks = [nd.get('pagerank', nd.get('p', 0)) for nd in deck_existing]
            avg_pr = float(np.mean(deck_pageranks)) if deck_pageranks else 1e-5

            for guid in changed_guids:
                note = notes_by_guid.get(guid)
                if not note:
                    continue
                front = get_front_field(note)
                label = "" if is_public else strip_html(front)
                # Place near centroid with small random offset
                offset = 20
                x = cx + (np.random.random() - 0.5) * offset
                y = cy + (np.random.random() - 0.5) * offset
                z = cz + (np.random.random() - 0.5) * offset

                if is_public:
                    kept_nodes.append(
                        {
                            'id': guid,
                            'l': label,
                            'd': deck,
                            'p': round(avg_pr, 6),
                            's': round(min(3, max(0.5, avg_pr * 100)), 2),
                            'x': int(x),
                            'y': int(y),
                            'z': int(z),
                        }
                    )
                else:
                    kept_nodes.append(
                        {
                            'id': guid,
                            'label': label,
                            'deck': deck,
                            'pagerank': round(avg_pr, 6),
                            'size': min(3, max(0.5, avg_pr * 100)),
                            'x': round(x, 2),
                            'y': round(y, 2),
                            'z': round(z, 2),
                        }
                    )

            # Add new edges
            for e in new_edges:
                if is_public:
                    kept_links.append(
                        {'s': e['source'], 't': e['target'], 'w': round(e['weight'], 1)}
                    )
                else:
                    kept_links.append(
                        {
                            'source': e['source'],
                            'target': e['target'],
                            'weight': round(e['weight'], 2),
                        }
                    )

        print(f'  Incremental build in {time.time() - t1:.1f}s')
        nodes = kept_nodes
        links = kept_links
    else:
        # Full rebuild
        print('Building graph (full)...')
        t1 = time.time()
        graph = build_graph(sample_notes, with_pagerank=True, progress_callback=deck_progress)
        t_graph = time.time() - t1
        print(f'  Graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges ({t_graph:.1f}s)')

        # Compute ForceAtlas2 layout
        n_nodes = len(graph.nodes())
        iters = 30 if n_nodes > 50000 else 50 if n_nodes > 10000 else 100
        print(f'Computing layout (ForceAtlas2, {iters} iterations)...')
        t_layout = time.time()
        layout = compute_layout(graph, iterations=iters)
        print(f'  Layout computed in {time.time() - t_layout:.1f}s')

        print('Exporting nodes...')
        nodes = []
        for i, (node_id, ndata) in enumerate(graph.nodes(data=True)):
            if (i + 1) % 5000 == 0 or i + 1 == len(graph.nodes()):
                progress_bar(i + 1, len(graph.nodes()), 'Nodes')
            x, y, z = layout.get(node_id, (0, 0, 0))
            label = "" if is_public else strip_html(ndata.get('front', 'Unknown'))
            if is_public:
                nodes.append(
                    {
                        'id': node_id,
                        'l': label,
                        'd': ndata.get('deck', 'Unknown'),
                        'p': round(ndata.get('pagerank', 0), 6),
                        's': round(min(3, max(0.5, ndata.get('pagerank', 0) * 100)), 2),
                        'x': int(x),
                        'y': int(y),
                        'z': int(z),
                    }
                )
            else:
                nodes.append(
                    {
                        'id': node_id,
                        'label': label,
                        'deck': ndata.get('deck', 'Unknown'),
                        'pagerank': round(ndata.get('pagerank', 0), 6),
                        'size': min(3, max(0.5, ndata.get('pagerank', 0) * 100)),
                        'x': round(x, 2),
                        'y': round(y, 2),
                        'z': round(z, 2),
                    }
                )

        if is_public:
            links = [
                {'s': s, 't': t, 'w': round(d.get('weight', 1), 1)}
                for s, t, d in graph.edges(data=True)
            ]
        else:
            links = [
                {'source': s, 'target': t, 'weight': round(d.get('weight', 1), 2)}
                for s, t, d in graph.edges(data=True)
            ]

    print(f'Writing {len(nodes)} nodes, {len(links)} links...')
    t2 = time.time()
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'nodes': nodes, 'links': links}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'  Written in {time.time() - t2:.1f}s')

    if not is_public:
        save_cache(sample_notes, len(nodes), len(links), output_file=str(OUTPUT_FILE))

    print(f'Done — {OUTPUT_FILE}')
    print(f'  {len(nodes)} nodes, {len(links)} links')
