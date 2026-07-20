#!/usr/bin/env python3
"""Export graph for visualization (Gephi, D3.js)"""

import gzip
import json
import os
import sys
from datetime import datetime

import networkx as nx

from graph._paths import ANKI_ADDONS_DIR
from graph.builder import build_per_deck_graphs

BASE = ANKI_ADDONS_DIR
os.chdir(str(BASE))
sys.path.insert(0, str(BASE))

# Load staged notes
staging_file = BASE / 'data/cloudflare/collection/notes.json.gz'
with gzip.open(staging_file, 'rt') as f:
    notes = json.load(f)

print(f"✓ Loaded {len(notes):,} notes")

# Create output dir
output_dir = BASE / 'graph_output'
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
