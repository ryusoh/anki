#!/usr/bin/env python3
"""
Incremental Graph Data Export

Progressively increases sample size for testing:
100 → 200 → 300 → ... → 1000 → 1100 → ... → all

Usage:
    python3 incremental_export.py              # Next increment
    python3 incremental_export.py --size 500   # Specific size
    python3 incremental_export.py --reset      # Reset to 100
    python3 incremental_export.py --status     # Show current status
"""

import sys, json, gzip, re, argparse
from pathlib import Path

sys.path.insert(0, '/Users/lz/Library/Application Support/Anki2/addons21')
from graph.builder import build_graph

CONFIG_FILE = Path('/Users/lz/Library/Application Support/Anki2/addons21/graph/.incremental_config.json')
DATA_FILE = Path('/Users/lz/Library/Application Support/Anki2/addons21/graph/graph_data.json')
NOTES_FILE = Path('/Users/lz/Library/Application Support/Anki2/addons21/data/cloudflare/collection/notes.json.gz')

def load_config():
    """Load current sample size config."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'sample_size': 100, 'increment': 100}

def save_config(config):
    """Save config."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def strip_html(text):
    """Remove HTML tags from text."""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('::', ' ').replace('\n', ' ')
    return ' '.join(text.split())[:60]

def export_graph(sample_size):
    """Export graph with specified sample size."""
    print(f"📦 Loading notes (sample: {sample_size:,})...")
    
    with gzip.open(NOTES_FILE, 'rt') as f:
        all_notes = json.load(f)
    
    total_available = len(all_notes)
    
    if sample_size > total_available:
        print(f"⚠️  Requested {sample_size:,} but only {total_available:,} available")
        sample_size = total_available
    
    # Take sample
    sample_notes = all_notes[:sample_size]
    print(f"✓ Using {len(sample_notes):,} notes")
    
    # Build graph
    print("🔨 Building graph...")
    graph = build_graph(sample_notes, with_pagerank=True)
    print(f"✓ Graph: {len(graph.nodes()):,} nodes, {len(graph.edges()):,} edges")
    
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
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({'nodes': nodes, 'links': links}, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Exported to {DATA_FILE}")
    print(f"📊 Stats:")
    print(f"   Nodes: {len(nodes):,}")
    print(f"   Links: {len(links):,}")
    
    # Count by deck
    decks = {}
    for node in nodes:
        deck = node['deck']
        decks[deck] = decks.get(deck, 0) + 1
    
    print(f"   Decks: {len(decks)}")
    for deck, count in sorted(decks.items(), key=lambda x: -x[1])[:5]:
        print(f"      {deck}: {count:,}")
    
    return len(nodes)

def main():
    parser = argparse.ArgumentParser(description='Incremental graph export')
    parser.add_argument('--size', '-s', type=int, help='Specific sample size')
    parser.add_argument('--reset', '-r', action='store_true', help='Reset to 100')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--next', '-n', action='store_true', help='Next increment (default)')
    
    args = parser.parse_args()
    
    config = load_config()
    
    if args.status:
        print(f"📊 Current status:")
        print(f"   Sample size: {config['sample_size']:,}")
        print(f"   Increment: {config['increment']:,}")
        if DATA_FILE.exists():
            size_mb = DATA_FILE.stat().st_size / 1024 / 1024
            print(f"   Data file: {size_mb:.1f} MB")
        return
    
    if args.reset:
        config['sample_size'] = 100
        save_config(config)
        print(f"🔄 Reset to {config['sample_size']}")
        export_graph(config['sample_size'])
        return
    
    if args.size:
        config['sample_size'] = args.size
        save_config(config)
        print(f"📏 Set size to {config['sample_size']:,}")
        export_graph(config['sample_size'])
        return
    
    # Default: next increment
    old_size = config['sample_size']
    
    # Increase increment for larger sizes
    if config['sample_size'] >= 1000:
        config['increment'] = 100
    if config['sample_size'] >= 5000:
        config['increment'] = 500
    if config['sample_size'] >= 10000:
        config['increment'] = 1000
    if config['sample_size'] >= 50000:
        config['increment'] = 5000
    
    config['sample_size'] += config['increment']
    save_config(config)
    
    print(f"📈 Incrementing: {old_size:,} → {config['sample_size']:,}")
    export_graph(config['sample_size'])
    
    print(f"\n🌐 Refresh: open http://localhost:8000/graph/index.html")

if __name__ == "__main__":
    main()
