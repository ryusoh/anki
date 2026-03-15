#!/usr/bin/env python3
"""Export graph for visualization (Gephi, D3.js)"""

import sys, os
from pathlib import Path
sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21')
os.chdir('/Users/lz/Library/Application Support/Anki2/addons21')

import json, gzip, networkx as nx
from datetime import datetime
from graph.builder import build_per_deck_graphs

# Load staged notes
staging_file = "/Users/lz/Library/Application Support/Anki2/addons21/data/cloudflare/collection/notes.json.gz"
with gzip.open(staging_file, 'rt') as f:
    notes = json.load(f)

print(f"✓ Loaded {len(notes):,} notes")

# Create output dir
output_dir = Path("/Users/lz/Library/Application Support/Anki2/addons21/graph_output")
output_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

# Build and export per deck
graphs = build_per_deck_graphs(notes, with_pagerank=True)

for deck_name, graph in graphs.items():
    deck_safe = deck_name.replace(' ', '_').replace('/', '_')[:50]
    
    # GraphML for Gephi
    nx.write_graphml(graph, output_dir / f"{deck_safe}-{timestamp}.graphml")
    print(f"✓ {deck_name}: {len(graph.nodes()):,} nodes, {len(graph.edges()):,} edges")

print(f"\n✅ Export complete: {output_dir}")
print("Open .graphml files in Gephi (gephi.org)")
