# Graph Analysis CLI Guide

## Overview

The `graph/analyze.py` CLI tool analyzes your Anki collection as a knowledge graph using PageRank to find the most important "hub" cards.

## Quick Start

```bash
# Analyze all decks
make graph-analyze

# Analyze specific deck
make graph-deck DECK='English Vocabulary'

# Export graphs to JSON
make graph-export
```

## Commands

### List Available Decks

```bash
python3 graph/analyze.py --list-decks
```

Output:

```
📚 Available Decks (5):
============================================================
  • English Vocabulary: 2,345 notes
  • Calculus: 567 notes
  • Biology 101: 890 notes
  • Physics: 432 notes
  • History: 1,234 notes
```

### Analyze Specific Deck

```bash
python3 graph/analyze.py --deck "English Vocabulary" --top 10
```

Output:

```
📊 Top 10 Notes by PageRank (English Vocabulary)
================================================================================
Rank   Front Field                    PageRank     Tags
================================================================================
1      baroque                        0.284000     vocab, english, art
2      style                          0.234000     vocab, english
3      flamboyant                     0.184000     vocab, english
...
```

### Analyze All Decks

```bash
python3 graph/analyze.py --all-decks --top 5 --compare
```

Output:

```
📊 Deck Comparison
====================================================================================================
Deck                           Notes    Edges    Density    Top Note
====================================================================================================
Biology 101                    890      234      0.0003     mitochondria
Calculus                       567      189      0.0006     derivative
English Vocabulary             2345     892      0.0002     baroque
...

📊 Top 5 Notes by PageRank (English Vocabulary)
...

📊 Top 5 Notes by PageRank (Calculus)
...
```

### Find Hub Notes

Hub notes have high PageRank and many incoming references:

```bash
python3 graph/analyze.py --deck "English Vocabulary" --hubs
```

Output:

```
🎯 Hub Notes in English Vocabulary (15):
================================================================================
Rank   Front Field                    PageRank     In     Out
================================================================================
1      baroque                        0.284000     5      2
2      style                          0.234000     4      3
...
```

### Find Isolated Notes

Isolated notes have no connections (might need better tagging):

```bash
python3 graph/analyze.py --deck "English Vocabulary" --isolated
```

Output:

```
🔍 Isolated Notes in English Vocabulary (23):
============================================================
  • ephemeral
  • serendipity
  • quintessential
  ... and 20 more
```

### Export Graph

```bash
# Export to JSON
python3 graph/analyze.py --deck "English Vocabulary" --export graph_output --format json

# Export to GraphML (for Gephi)
python3 graph/analyze.py --deck "English Vocabulary" --export graph_output --format graphml
```

## Makefile Targets

| Target                        | Description                                  |
| ----------------------------- | -------------------------------------------- |
| `make graph-analyze`          | Analyze all decks with PageRank + comparison |
| `make graph-deck DECK='name'` | Analyze specific deck with hubs + isolated   |
| `make graph-export`           | Export all decks to `graph_output/` as JSON  |

## Options

| Option             | Description                      |
| ------------------ | -------------------------------- |
| `-d, --deck NAME`  | Analyze specific deck            |
| `-a, --all-decks`  | Analyze all decks                |
| `-t, --top N`      | Show top N notes (default: 10)   |
| `-e, --export DIR` | Export to directory              |
| `-f, --format`     | Export format: `json`, `graphml` |
| `--isolated`       | Show isolated notes              |
| `--hubs`           | Show hub notes                   |
| `--compare`        | Compare decks side-by-side       |
| `--list-decks`     | List available decks             |

## Data Sources

The CLI automatically loads from:

1. **R2 Staged Data** (`data/cloudflare/collection/notes.json.gz`) - Full data with deck info
2. **GitHub Data** (`data/anki/notes.json.gz` + `cards.json.gz`) - Anonymized with deck mapping

## Example Workflow

```bash
# 1. Fetch data from Anki (includes R2 staging)
make fetch-and-stage-r2

# 2. Upload to R2 (optional, for sync)
make fetch-r2

# 3. Analyze all decks
make graph-analyze

# 4. Deep dive into specific deck
make graph-deck DECK='English Vocabulary'

# 5. Export for visualization in Gephi
make graph-export

# 6. Open in Gephi
gephi graph_output/English_Vocabulary-20260314-153042.graphml
```

## Understanding Output

### PageRank Score

- **High (>0.01)**: Hub card, referenced by many other cards
- **Medium (0.001-0.01)**: Connected card
- **Low (<0.001)**: Peripheral or isolated card

### Density

Graph density = edges / possible_edges

- **High (>0.1)**: Tightly connected deck
- **Low (<0.01)**: Sparse connections

### In-Degree vs Out-Degree

- **In-Degree**: How many cards reference this card's Front field
- **Out-Degree**: How many other cards this card references

**Hub cards** = High In-Degree + High PageRank

## Use Cases

### 1. Find Foundational Concepts

```bash
# High PageRank = foundational concepts
python3 graph/analyze.py --deck "Calculus" --top 10 --hubs
```

**Insight:** Study these cards first - they help with many others!

### 2. Identify Weak Connections

```bash
# Isolated cards might need better tagging
python3 graph/analyze.py --deck "English Vocabulary" --isolated
```

**Action:** Add related tags or create connection cards.

### 3. Compare Deck Complexity

```bash
# Higher density = more interconnected
python3 graph/analyze.py --all-decks --compare
```

**Insight:** Dense decks need more study time.

### 4. Export for Visualization

```bash
# Export to GraphML, open in Gephi
make graph-export
```

**Use:** Visual exploration of knowledge structure.

## Troubleshooting

### "No notes found"

Make sure data is staged:

```bash
make fetch-and-stage-r2
```

### "Deck not found"

List available decks:

```bash
python3 graph/analyze.py --list-decks
```

### "Module not found: networkx"

Install dependencies:

```bash
pip install networkx scipy
```

## Performance

| Deck Size        | Analysis Time |
| ---------------- | ------------- |
| <100 notes       | <1 second     |
| 100-1000 notes   | 1-5 seconds   |
| 1000-10000 notes | 5-30 seconds  |
| >10000 notes     | 30+ seconds   |

## Privacy

- ✅ All analysis happens **locally**
- ✅ No data sent to external services
- ✅ Output in `graph_output/` is git-ignored
- ✅ Works offline after initial data load
