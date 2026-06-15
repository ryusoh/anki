#!/usr/bin/env python3
"""
analyze - Analyze Anki knowledge graphs with PageRank

Usage:
    analyze [options]

Options:
    -h, --help              Show this help message
    -d, --deck NAME         Analyze specific deck
    -a, --all-decks         Analyze all decks (separate graphs)
    -t, --top N             Show top N notes by PageRank (default: 10)
    -e, --export DIR        Export graph to directory
    -f, --format FORMAT     Export format: json, graphml (default: json)
    --isolated              Show isolated notes (no connections)
    --hubs                  Show hub notes (high PageRank)
    --compare               Compare decks side-by-side
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.builder import (
    build_graph,
    build_per_deck_graphs,
    export_to_dict,
    get_hub_nodes,
    get_isolated_nodes,
    get_top_nodes,
)
from graph.parser import group_by_deck

# Deck aliases for easy typing
DECK_ALIASES = {
    '1': '言語日語',
    'j': '言語日語',
    'J': '言語日語',
    '2': '言語粵語',
    'c': '言語粵語',
    'C': '言語粵語',
    '3': '言語英語',
    'e': '言語英語',
    'E': '言語英語',
    '4': '言語呉語',
    's': '言語呉語',  # Shanghai/Wu
    'S': '言語呉語',
    '5': '言語台語',
    't': '言語台語',
    'T': '言語台語',
    '6': '金融',
    'f': '金融',
    'F': '金融',
}


def load_notes_from_file(notes_file):
    """
    Load notes from JSON file (GitHub or R2 export).

    Args:
        notes_file: Path to notes.json.gz or notes.json

    Returns:
        List of note dicts with deck information
    """
    import gzip

    notes_file = Path(notes_file)

    if not notes_file.exists():
        print(f"❌ Notes file not found: {notes_file}", file=sys.stderr)
        return []

    try:
        if notes_file.suffix == '.gz':
            with gzip.open(notes_file, 'rt', encoding='utf-8') as f:
                notes = json.load(f)
        else:
            with open(notes_file, 'r', encoding='utf-8') as f:
                notes = json.load(f)

        # Add deck information if not present
        # For now, notes from GitHub don't have deck info
        # This will be enhanced when we merge with R2 data
        for note in notes:
            if 'deck' not in note:
                # Default deck if not specified
                note['deck'] = 'Unknown'
                note['deck_id'] = 0

        return notes

    except Exception as e:
        print(f"❌ Error loading notes: {e}", file=sys.stderr)
        return []


def load_notes_with_decks():
    """
    Load notes with deck information.

    Tries multiple sources:
    1. R2 staged data (data/cloudflare/collection/notes.json.gz)
    2. GitHub data (data/anki/notes.json.gz) - limited deck info

    Returns:
        List of note dicts with deck information
    """
    # Try R2 staged data first (has full deck info)
    r2_staged = (
        Path(__file__).parent.parent / "data" / "cloudflare" / "collection" / "notes.json.gz"
    )
    if r2_staged.exists():
        print(f"📦 Loading from R2 staging: {r2_staged}")
        notes = load_notes_from_file(r2_staged)
        if notes:
            return notes

    # Fallback to GitHub data
    github_data = Path(__file__).parent.parent / "data" / "anki" / "notes.json.gz"
    if github_data.exists():
        print(f"📦 Loading from GitHub: {github_data}")
        notes = load_notes_from_file(github_data)
        if notes:
            # Try to get deck info from cards.json.gz
            cards_file = Path(__file__).parent.parent / "data" / "anki" / "cards.json.gz"
            decks_file = Path(__file__).parent.parent / "data" / "anki" / "decks.json"
            if cards_file.exists():
                deck_map = build_deck_map_from_cards(notes, cards_file, decks_file)
                for note in notes:
                    if note['id'] in deck_map:
                        note['deck'] = deck_map[note['id']]['deck_name']
                        note['deck_id'] = deck_map[note['id']]['did']
            return notes

    print("❌ No notes found", file=sys.stderr)
    return []


def build_deck_map_from_cards(notes, cards_file, decks_file=None):
    """
    Build deck map from cards.json.gz.

    Maps note IDs to deck information. When decks_file is provided,
    resolves deck names via did -> decks.json (canonical, always current)
    instead of per-card deck_name which can be stale after merges/renames.
    """
    import gzip

    try:
        if cards_file.suffix == '.gz':
            with gzip.open(cards_file, 'rt', encoding='utf-8') as f:
                cards = json.load(f)
        else:
            with open(cards_file, 'r', encoding='utf-8') as f:
                cards = json.load(f)

        # Load did -> current name from decks.json
        did_to_name = {}
        if decks_file and decks_file.exists():
            try:
                with open(decks_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                did_to_name = {int(k): v for k, v in raw.items()}
            except Exception as e:
                print(f"Warning: Failed to load decks.json: {e}", file=sys.stderr)

        # Build map: note_id -> deck info
        deck_map = {}
        for card in cards:
            nid = card['nid']
            if nid not in deck_map:
                did = card['did']
                deck_name = did_to_name.get(did, card.get('deck_name', 'Unknown'))
                deck_map[nid] = {'did': did, 'deck_name': deck_name}

        return deck_map

    except Exception as e:
        print(f"⚠️  Could not load cards: {e}", file=sys.stderr)
        return {}


def get_available_decks(notes):
    """
    Get list of unique deck names from notes.

    Args:
        notes: List of note dicts

    Returns:
        List of deck names
    """
    grouped = group_by_deck(notes)
    return list(grouped.keys())


def resolve_deck_alias(alias):
    """Resolve deck alias to full deck name."""
    return DECK_ALIASES.get(alias)


def get_deck_notes(notes, deck_name):
    """
    Get notes for a deck name (supports aliases and exact matching).
    """
    resolved = resolve_deck_alias(deck_name)
    target = resolved if resolved else deck_name
    return [n for n in notes if n.get('deck') == target]


def print_deck_list(notes):
    """Print available decks."""
    decks = get_available_decks(notes)

    print(f"\n📚 Available Decks ({len(decks)}):")
    print("=" * 60)

    grouped = group_by_deck(notes)
    for deck_name in sorted(decks):
        count = len(grouped[deck_name])
        print(f"  • {deck_name}: {count} notes")

    print()


def print_top_notes(graph, deck_name, top_n=10):
    """Print top N notes by PageRank."""
    top = get_top_nodes(graph, n=top_n, by='pagerank')

    print(f"\n📊 Top {top_n} Notes by PageRank ({deck_name})")
    print("=" * 80)
    print(f"{'Rank':<6} {'Front Field':<30} {'PageRank':<12} {'Tags':<20}")
    print("=" * 80)

    for rank, (_node_id, data) in enumerate(top, 1):
        front = (
            data.get('front', 'Unknown')[:28] + '..'
            if len(data.get('front', '')) > 30
            else data.get('front', 'Unknown')
        )
        pagerank = data.get('pagerank', 0)
        tags = (
            data.get('tags', '')[:18] + '..'
            if len(data.get('tags', '')) > 20
            else data.get('tags', '')
        )

        print(f"{rank:<6} {front:<30} {pagerank:<12.6f} {tags:<20}")

    print()


def print_isolated_notes(graph, deck_name):
    """Print isolated notes (no connections)."""
    isolated = get_isolated_nodes(graph)

    if not isolated:
        print(f"\n✓ No isolated notes in {deck_name}")
        return

    print(f"\n🔍 Isolated Notes in {deck_name} ({len(isolated)}):")
    print("=" * 60)

    for node_id in isolated[:20]:  # Show first 20
        data = graph.nodes[node_id]
        front = data.get('front', 'Unknown')
        print(f"  • {front}")

    if len(isolated) > 20:
        print(f"  ... and {len(isolated) - 20} more")

    print()


def print_hub_notes(graph, deck_name, threshold=0.01):
    """Print hub notes (high PageRank, many connections)."""
    hubs = get_hub_nodes(graph, threshold=threshold)

    if not hubs:
        print(f"\n✓ No hub notes found in {deck_name}")
        return

    print(f"\n🎯 Hub Notes in {deck_name} ({len(hubs)}):")
    print("=" * 80)
    print(f"{'Rank':<6} {'Front Field':<30} {'PageRank':<12} {'In':<6} {'Out':<6}")
    print("=" * 80)

    for rank, (_node_id, data) in enumerate(hubs, 1):
        front = (
            data.get('front', 'Unknown')[:28] + '..'
            if len(data.get('front', '')) > 30
            else data.get('front', 'Unknown')
        )
        pagerank = data.get('pagerank', 0)
        in_deg = data.get('in_degree', 0)
        out_deg = data.get('out_degree', 0)

        print(f"{rank:<6} {front:<30} {pagerank:<12.6f} {in_deg:<6} {out_deg:<6}")

    print()


def export_graph(graph, output_dir, format='json', deck_name='graph'):
    """Export graph to file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

    if format == 'json':
        data = export_to_dict(graph)
        output_file = output_dir / f"{deck_name}-{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✓ Exported to {output_file}")

    elif format == 'graphml':
        import networkx as nx

        output_file = output_dir / f"{deck_name}-{timestamp}.graphml"

        nx.write_graphml(graph, output_file)
        print(f"✓ Exported to {output_file}")

    else:
        print(f"⚠️  Unknown format: {format}", file=sys.stderr)


def compare_decks(graphs):
    """Compare multiple decks side-by-side."""
    print("\n📊 Deck Comparison")
    print("=" * 100)
    print(f"{'Deck':<30} {'Notes':<8} {'Edges':<8} {'Density':<10} {'Top Note':<40}")
    print("=" * 100)

    for deck_name, graph in sorted(graphs.items()):
        num_nodes = len(graph.nodes())
        num_edges = len(graph.edges())
        density = num_edges / max(num_nodes * (num_nodes - 1), 1)  # Avoid division by zero

        # Get top note
        top = get_top_nodes(graph, n=1, by='pagerank')
        top_front = top[0][1].get('front', 'Unknown')[:38] + '..' if top else 'N/A'

        print(
            f"{deck_name[:29]:<30} {num_nodes:<8} {num_edges:<8} {density:<10.4f} {top_front:<40}"
        )

    print()


def analyze_single_deck(args, decks, notes):
    # Resolve alias
    deck_to_analyze = args.deck

    # Check if it's an alias or full name
    resolved = resolve_deck_alias(args.deck)
    if resolved:
        deck_to_analyze = resolved
        print(f"📍 Alias '{args.deck}' → '{resolved}'")
    elif args.deck not in decks:
        print(f"❌ Deck not found: {args.deck}", file=sys.stderr)
        print("\nAvailable decks:", file=sys.stderr)
        for i, d in enumerate(sorted(decks), 1):
            print(f"  {i}. {d}", file=sys.stderr)
        print("\nOr use aliases: J, C, E, S, T, F", file=sys.stderr)
        sys.exit(1)

    deck_notes = get_deck_notes(notes, deck_to_analyze)
    actual_deck_name = deck_notes[0].get('deck', 'Unknown') if deck_notes else deck_to_analyze

    print(f"\n📊 Analyzing deck: {actual_deck_name} ({len(deck_notes):,} notes)")

    # Build graph
    graph = build_graph(deck_notes, with_pagerank=True, with_anonymization=args.anonymize)

    # Show top notes
    print_top_notes(graph, args.deck, args.top)

    # Show isolated notes
    if args.isolated:
        print_isolated_notes(graph, args.deck)

    # Show hub notes
    if args.hubs:
        print_hub_notes(graph, args.deck)

    # Export if requested
    if args.export:
        export_graph(graph, args.export, args.format, args.deck.replace(' ', '_'))


def analyze_all_decks(args, decks, notes):
    print(f"\n📊 Analyzing all {len(decks)} decks...")

    graphs = build_per_deck_graphs(notes, with_pagerank=True, with_anonymization=args.anonymize)

    # Compare decks
    if args.compare:
        compare_decks(graphs)

    # Show top notes for each deck
    for deck_name, graph in graphs.items():
        print_top_notes(graph, deck_name, min(args.top, 5))

        if args.isolated:
            print_isolated_notes(graph, deck_name)

        if args.hubs:
            print_hub_notes(graph, deck_name)

    # Export all decks
    if args.export:
        for deck_name, graph in graphs.items():
            export_graph(graph, args.export, args.format, deck_name.replace(' ', '_'))


def main():
    parser = argparse.ArgumentParser(
        prog='analyze',
        description='Analyze Anki knowledge graphs with PageRank',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '-d', '--deck', type=str, help='Analyze specific deck (aliases: J, C, E, S, T, F)'
    )
    parser.add_argument('-a', '--all-decks', action='store_true', help='Analyze all decks')
    parser.add_argument('-t', '--top', type=int, default=10, help='Show top N notes (default: 10)')
    parser.add_argument('-e', '--export', type=str, help='Export graph to directory')
    parser.add_argument(
        '-f',
        '--format',
        type=str,
        default='json',
        choices=['json', 'graphml'],
        help='Export format',
    )
    parser.add_argument('--isolated', action='store_true', help='Show isolated notes')
    parser.add_argument('--hubs', action='store_true', help='Show hub notes')
    parser.add_argument('--compare', action='store_true', help='Compare decks')
    parser.add_argument('--list-decks', action='store_true', help='List available decks')
    parser.add_argument('--anonymize', action='store_true', help='Anonymize sensitive card content')

    args = parser.parse_args()

    # Load notes
    print("📦 Loading notes...")
    notes = load_notes_with_decks()

    if not notes:
        print("❌ No notes loaded", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Loaded {len(notes):,} notes")

    if args.anonymize:
        print("🔒 Anonymization enabled: card content will be hashed")

    # List decks if requested
    if args.list_decks:
        print_deck_list(notes)
        return

    # Get available decks
    decks = get_available_decks(notes)

    if not decks:
        print("❌ No decks found", file=sys.stderr)
        sys.exit(1)

    # Specific deck analysis
    if args.deck:
        analyze_single_deck(args, decks, notes)
        return

    # All decks analysis
    if args.all_decks or args.compare:
        analyze_all_decks(args, decks, notes)
        return

    # Default: show deck list
    print_deck_list(notes)
    print("Use --deck NAME to analyze a specific deck")
    print("Use --all-decks to analyze all decks")


if __name__ == "__main__":
    main()
