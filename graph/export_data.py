#!/usr/bin/env python3
"""Export graph data for JavaScript visualization.

Usage:
    python3 graph/export_data.py           # default 2000 nodes
    python3 graph/export_data.py 500       # 500 nodes
    python3 graph/export_data.py all       # all nodes
    python3 graph/export_data.py --full    # force full rebuild (skip cache)
"""

import sys, json, gzip, re, time, hashlib
import numpy as np
from pathlib import Path

sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21')
from graph.builder import build_graph
from fa2_modified import ForceAtlas2

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
    key = f"{note['guid']}:{note.get('mod', '')}:{note.get('flds', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def load_cache():
    """Load the export cache (processed note fingerprints per deck)."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def save_cache(notes, node_count, link_count):
    """Save cache with note fingerprints as sets per deck."""
    deck_fingerprints = {}
    for note in notes:
        deck = note.get('deck', 'Unknown')
        if deck not in deck_fingerprints:
            deck_fingerprints[deck] = []
        deck_fingerprints[deck].append(note_fingerprint(note))

    cache = {
        'version': 3,
        'note_count': len(notes),
        'node_count': node_count,
        'link_count': link_count,
        'decks': deck_fingerprints,
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)


def find_changed_decks(notes, cache):
    """Compare current notes against cache to find which decks changed."""
    if not cache or cache.get('version') != 3:
        return None  # full rebuild

    # Build current fingerprints by deck
    current = {}
    for note in notes:
        deck = note.get('deck', 'Unknown')
        if deck not in current:
            current[deck] = set()
        current[deck].add(note_fingerprint(note))

    cached_decks = cache.get('decks', {})
    changed = set()

    for deck, fps in current.items():
        cached_fps = set(cached_decks.get(deck, []))
        if fps != cached_fps:
            new_count = len(fps - cached_fps)
            removed_count = len(cached_fps - fps)
            print(f'  Deck "{deck}": +{new_count} new, -{removed_count} removed')
            changed.add(deck)

    for deck in cached_decks:
        if deck not in current:
            changed.add(deck)

    return changed


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
        deck_centers[deck] = np.array([
            np.cos(theta) * r_at_y,
            y,
            np.sin(theta) * r_at_y,
        ])
        deck_radii[deck] = max(50, np.cbrt(len(decks[deck])) * 30)

    # Spacing: scale sphere so decks don't overlap
    max_radius = max(deck_radii.values())
    sphere_radius = max_radius * total * 0.4

    all_positions = {}

    for i, deck in enumerate(deck_names):
        deck_nodes = decks[deck]
        subgraph = graph.subgraph(deck_nodes)
        n = len(deck_nodes)
        iters = max(10, min(iterations, iterations * 5000 // max(n, 1)))

        short = deck[:30] + '…' if len(deck) > 30 else deck
        progress_bar(i + 1, total, f'Layout: {short} ({n} nodes, {iters} iters)')

        layout_2d = _compute_deck_layout(subgraph, iters)

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
            pos = center_3d + tangent_x * lx + tangent_y * ly
            all_positions[nid] = (float(pos[0]), float(pos[1]), float(pos[2]))

    sys.stderr.write('\n')
    return all_positions


# --- Main ---
force_full = '--full' in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith('--')]
arg = args[0] if args else '2000'

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
changed_decks = find_changed_decks(sample_notes, cache) if cache else None

if changed_decks is not None and len(changed_decks) == 0:
    print('No changes detected — graph_data.json is up to date.')
    print(f'  ({cache["node_count"]} nodes, {cache["link_count"]} links)')
    print('  Use --full to force rebuild.')
    sys.exit(0)

if changed_decks is not None:
    print(f'Incremental: {len(changed_decks)} deck(s) changed, rebuilding those')
    # Load existing output
    with open(OUTPUT_FILE, 'r') as f:
        existing = json.load(f)
    existing_nodes = {n['id']: n for n in existing['nodes']}
    existing_links = existing['links']

    # Remove old data for changed decks
    unchanged_node_ids = set()
    for nid, nd in existing_nodes.items():
        if nd.get('deck') not in changed_decks:
            unchanged_node_ids.add(nid)
    kept_nodes = [nd for nid, nd in existing_nodes.items() if nid in unchanged_node_ids]
    kept_links = [
        lk for lk in existing_links
        if lk['source'] in unchanged_node_ids and lk['target'] in unchanged_node_ids
    ]

    # Rebuild only changed decks
    changed_notes = [n for n in sample_notes if n.get('deck') in changed_decks]
    print(f'  Rebuilding {len(changed_notes)} notes across changed decks...')

    t1 = time.time()
    graph = build_graph(changed_notes, with_pagerank=True, progress_callback=deck_progress)
    print(f'  Graph built in {time.time() - t1:.1f}s')

    # Layout for changed decks
    n_changed = len(graph.nodes())
    iters = 30 if n_changed > 50000 else 50 if n_changed > 10000 else 100
    print(f'  Computing layout for changed decks ({iters} iterations)...')
    t_layout = time.time()
    layout = compute_layout(graph, iterations=iters)
    print(f'  Layout computed in {time.time() - t_layout:.1f}s')

    # Merge
    for node_id, ndata in graph.nodes(data=True):
        x, y = layout.get(node_id, (0, 0))
        kept_nodes.append({
            'id': node_id,
            'label': strip_html(ndata.get('front', 'Unknown')),
            'deck': ndata.get('deck', 'Unknown'),
            'pagerank': round(ndata.get('pagerank', 0), 6),
            'size': min(3, max(0.5, ndata.get('pagerank', 0) * 100)),
            'x': round(x, 2),
            'y': round(y, 2),
        })
    for s, t, d in graph.edges(data=True):
        kept_links.append({
            'source': s, 'target': t,
            'weight': round(d.get('weight', 1), 2),
        })

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
        x, y = layout.get(node_id, (0, 0))
        nodes.append({
            'id': node_id,
            'label': strip_html(ndata.get('front', 'Unknown')),
            'deck': ndata.get('deck', 'Unknown'),
            'pagerank': round(ndata.get('pagerank', 0), 6),
            'size': min(3, max(0.5, ndata.get('pagerank', 0) * 100)),
            'x': round(x, 2),
            'y': round(y, 2),
        })

    links = [
        {'source': s, 'target': t, 'weight': round(d.get('weight', 1), 2)}
        for s, t, d in graph.edges(data=True)
    ]

print(f'Writing {len(nodes)} nodes, {len(links)} links...')
t2 = time.time()
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump({'nodes': nodes, 'links': links}, f, ensure_ascii=False)
print(f'  Written in {time.time() - t2:.1f}s')

save_cache(sample_notes, len(nodes), len(links))

print(f'Done — {OUTPUT_FILE}')
print(f'  {len(nodes)} nodes, {len(links)} links')
