#!/usr/bin/env python3
"""Export graph data for JavaScript visualization.

Usage:
    python3 graph/export_data.py           # default 2000 nodes
    python3 graph/export_data.py 500       # 500 nodes
    python3 graph/export_data.py all       # all nodes
"""

import sys, json, gzip, re
from pathlib import Path

sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21')
from graph.builder import build_graph

BASE = Path('/Users/lz/Library/Application Support/Anki2/addons21')
NOTES_FILE = BASE / 'data/cloudflare/collection/notes.json.gz'
OUTPUT_FILE = BASE / 'graph/graph_data.json'


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


# Parse node count from CLI
arg = sys.argv[1] if len(sys.argv) > 1 else '2000'

with gzip.open(NOTES_FILE, 'rt') as f:
    all_notes = json.load(f)

if arg == 'all':
    sample_notes = all_notes
else:
    n = int(arg)
    sample_notes = all_notes[:n]

print(f"Using {len(sample_notes)} / {len(all_notes)} notes...")

graph = build_graph(sample_notes, with_pagerank=True)
print(f"Graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges")

nodes = []
for node_id, data in graph.nodes(data=True):
    nodes.append({
        'id': node_id,
        'label': strip_html(data.get('front', 'Unknown')),
        'deck': data.get('deck', 'Unknown'),
        'pagerank': round(data.get('pagerank', 0), 6),
        'size': min(3, max(0.5, data.get('pagerank', 0) * 100))
    })

links = [
    {'source': s, 'target': t, 'weight': round(d.get('weight', 1), 2)}
    for s, t, d in graph.edges(data=True)
]

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump({'nodes': nodes, 'links': links}, f, ensure_ascii=False)

print(f"Exported to {OUTPUT_FILE}")
print(f"  {len(nodes)} nodes, {len(links)} links")
