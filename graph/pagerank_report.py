#!/usr/bin/env python3
"""Generate PageRank report for recently reviewed cards.

Usage:
    python3 graph/pagerank_report.py          # latest reviewed day
    python3 graph/pagerank_report.py -a       # all days
    python3 graph/pagerank_report.py --all    # all days
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Allow running this script directly (python3 graph/pagerank_report.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graph._paths import ANKI_ADDONS_DIR

BASE = ANKI_ADDONS_DIR
GRAPH_FILE = BASE / 'graph/graph_data.json'
HISTORY_FILE = BASE / 'graph/history_data.json'
OUTPUT_DIR = BASE / 'data/pagerank'


def _normalize_concept(text):
    """Normalize text for concept deduplication (strip punctuation, lower, etc)."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove common punctuation and whitespace
    text = re.sub(r'[?？!！.。,，:;：；()（）[\]【】\s]+', '', text)
    return text.lower().strip()


def load_data():
    """Load graph and history data."""
    with open(GRAPH_FILE, 'r') as f:
        graph = json.load(f)
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)
    return graph, history


def build_link_counts(links):
    """Count incoming and outgoing links per node."""
    counts = defaultdict(lambda: {'in': 0, 'out': 0})
    for lk in links:
        s = lk.get('source', lk.get('s'))
        t = lk.get('target', lk.get('t'))
        if s and t:
            counts[s]['out'] += 1
            counts[t]['in'] += 1
    return counts


def generate_report(date, card_ids, nodes_by_id, link_counts, top_n=None):
    """Generate markdown report for a single day, or all time top N."""
    # Collect reviewed cards with their data
    cards = []
    for cid in card_ids:
        node = nodes_by_id.get(cid)
        if not node:
            continue
        c_links = link_counts.get(cid, {'in': 0, 'out': 0})
        cards.append(
            {
                'id': cid,
                'front': node.get('label', node.get('l', '')),
                'deck': node.get('deck', node.get('d', 'Unknown')),
                'pagerank': node.get('pagerank', node.get('p', 0)),
                'links_in': c_links['in'],
                'links_out': c_links['out'],
                'links_total': c_links['in'] + c_links['out'],
            }
        )

    # Group by deck
    by_deck = defaultdict(list)
    for c in cards:
        by_deck[c['deck']].append(c)

    # Build markdown
    if top_n:
        lines = [f'# PageRank Report — All Time Top {top_n} ({len(cards)} total cards in graph)\n']
    else:
        lines = [f'# PageRank Report — {date} ({len(cards)} cards reviewed)\n']

    for deck in sorted(by_deck.keys()):
        deck_cards = by_deck[deck]
        connected = [c for c in deck_cards if c['links_total'] > 0]
        isolated = [c for c in deck_cards if c['links_total'] == 0]

        lines.append(f'## {deck} ({len(deck_cards)} cards)\n')

        if connected:
            connected.sort(key=lambda c: c['pagerank'], reverse=True)

            # Deduplicate by concept
            unique_concepts = []
            seen_concepts = set()
            for c in connected:
                concept = _normalize_concept(c['front'])
                if not concept:
                    # If normalization results in empty string, keep original but don't dedup
                    unique_concepts.append(c)
                    continue
                if concept not in seen_concepts:
                    seen_concepts.add(concept)
                    unique_concepts.append(c)
            connected = unique_concepts

            if top_n:
                connected = connected[:top_n]
                lines.append(f'### Top {top_n} Connected (by PageRank)\n')
            else:
                lines.append('### Connected (by PageRank)\n')

            lines.append('| # | Front | PageRank | In-Links | Out-Links |')
            lines.append('|---|-------|----------|----------|-----------|')
            for i, c in enumerate(connected, 1):
                pr = f"{c['pagerank']:.6f}"
                front = c['front'].replace('|', '\\|')
                lines.append(f'| {i} | {front} | {pr} | {c["links_in"]} | {c["links_out"]} |')
            lines.append('')

        if isolated and not top_n:
            isolated.sort(key=lambda c: c['front'])
            lines.append('### Isolated (no connections)\n')
            for c in isolated:
                lines.append(f'- {c["front"]}')
            lines.append('')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate PageRank report")
    parser.add_argument(
        '-a', '--all', action='store_true', help='Generate reports for all historical dates'
    )
    parser.add_argument(
        '--top', type=int, help='Generate a single report for the top N cards of all time per deck'
    )
    args = parser.parse_args()

    graph, history = load_data()

    nodes_by_id = {}
    for n in graph['nodes']:
        nodes_by_id[n['id']] = n

    link_counts = build_link_counts(graph['links'])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.top:
        # All time top N report
        card_ids = list(nodes_by_id.keys())
        report = generate_report(None, card_ids, nodes_by_id, link_counts, top_n=args.top)
        out_file = OUTPUT_DIR / f'top_{args.top}.md'
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(report)
        print(f'\nSaved to {out_file}')
        return

    dates = history['dates']
    if not dates:
        print('No review history found.')
        sys.exit(1)

    if args.all:
        targets = dates
    else:
        targets = [dates[-1]]

    for date in targets:
        card_ids = history['history'].get(date, [])
        if not card_ids:
            continue

        report = generate_report(date, card_ids, nodes_by_id, link_counts)
        out_file = OUTPUT_DIR / f'{date}.md'
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(report)

        if not args.all or date == targets[-1]:
            print(report)

    if args.all:
        print(f'\nGenerated {len(targets)} reports in {OUTPUT_DIR}')
    else:
        print(f'\nSaved to {OUTPUT_DIR / f"{targets[0]}.md"}')


if __name__ == '__main__':
    main()
