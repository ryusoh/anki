#!/usr/bin/env python3
"""Quick export of uploaded notes for Gephi visualization"""

import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

import networkx as nx

# Allow running this script directly (python3 graph/quick_export.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graph._paths import ANKI_ADDONS_DIR
from graph.builder import build_graph

BASE = ANKI_ADDONS_DIR
sys.path.insert(0, str(BASE))

# Load staged notes
notes_file = BASE / 'data/cloudflare/collection/notes.json.gz'
print("Loading notes...")
with gzip.open(notes_file, 'rt') as f:
    notes = json.load(f)

# Take first 5000 for quick viz
sample_notes = notes[:5000]
print(f"✓ Loaded {len(sample_notes):,} notes (sample)")

# Create output dir
output_dir = BASE / 'graph_output'
output_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

# Build graph
print("Building graph...")
graph = build_graph(sample_notes, with_pagerank=True)
print(f"✓ Graph: {len(graph.nodes()):,} nodes, {len(graph.edges()):,} edges")

# Export to GraphML
output_file = output_dir / f"anki-graph-{timestamp}.graphml"
print(f"Exporting to {output_file}...")
nx.write_graphml(graph, output_file)
print(f"✅ Done! Open in Gephi: {output_file}")
