#!/usr/bin/env python3
"""Export graph data for JavaScript visualization"""

import sys, json, gzip, re
from pathlib import Path

sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21')
from graph.builder import build_graph

def strip_html(text):
    """Remove HTML tags and entities from text."""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    # Strip HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&apos;', "'")
    text = text.replace('::', ' ').replace('\n', ' ')
    return ' '.join(text.split())[:60]

# Load notes
notes_file = "/Users/lz/Library/Application Support/Anki2/addons21/data/cloudflare/collection/notes.json.gz"
with gzip.open(notes_file, 'rt') as f:
    all_notes = json.load(f)

# Take sample
sample_notes = all_notes[:100]
print(f"Using {len(sample_notes)} notes...")

# Build graph
graph = build_graph(sample_notes, with_pagerank=True)
print(f"Graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges")

# Prepare data for JS
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

# Save
output_file = Path("/Users/lz/Library/Application Support/Anki2/addons21/graph/graph_data.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({'nodes': nodes, 'links': links}, f, ensure_ascii=False, indent=2)

print(f"✅ Exported to {output_file}")
print(f"🌐 Open: open /Users/lz/Library/Application Support/Anki2/addons21/graph/index.html")
