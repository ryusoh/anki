# Graph Merger Module - TDD Implementation

## Status: ✅ Core Tests Passing (37/37)

## What We Built

A **per-deck knowledge graph** builder with **PageRank** infrastructure for Anki cards.

### Key Features

1. **Per-Deck Isolation** - No cross-deck references (English ≠ Calculus ≠ Biology)
2. **Directed Graph** - Front field → Other fields (natural reference direction)
3. **PageRank** - Find "hub" cards that are referenced by many other cards
4. **TDD** - 37 tests covering parser, references, and builder

---

## Architecture

```text
Anki Notes (per deck)
        ↓
graph/parser.py (extract fields, tokenize)
        ↓
graph/references.py (find within-deck references)
        ↓
graph/builder.py (build DiGraph + PageRank)
        ↓
Output: networkx.DiGraph with pagerank attributes
```

---

## Module Structure

```text
graph/
├── __init__.py              # Package marker
├── parser.py                # Field extraction, tokenization, deck grouping
├── references.py            # Find cross-references (within deck only)
├── builder.py               # Build graph + PageRank
└── tests/
    ├── __init__.py
    ├── fixtures.py          # Test data (3 decks: English, Calculus, Biology)
    ├── test_parser.py       # 14 tests ✅
    ├── test_references.py   # 10 tests ✅
    └── test_builder.py      # 13 tests ✅
```

---

## Test Coverage

### Parser (14 tests)

- ✅ Field extraction (`::` delimiter)
- ✅ Tokenization (lowercase, stop words, min length)
- ✅ Deck info extraction
- ✅ Group by deck

### References (10 tests)

- ✅ Find references within English deck
- ✅ Find references within Calculus deck
- ✅ Find references within Biology deck
- ✅ **No cross-deck edges** (critical!)
- ✅ Edge weights
- ✅ Edge types (front_reference vs field_reference)

### Builder (13 tests)

- ✅ Create nodes for all notes
- ✅ Create edges for references
- ✅ Directed graph (DiGraph)
- ✅ Edge weights
- ✅ PageRank computation
- ✅ PageRank sums to ~1.0
- ✅ PageRank attached to nodes
- ✅ PageRank ranking
- ✅ Per-deck graphs
- ✅ Export to dict

---

## Usage (When Complete)

```bash
# Analyze a specific deck
python3 graph/analyze --deck "English Vocabulary" --pagerank --top 10

# Analyze all decks (separate graphs)
python3 graph/analyze --all-decks --pagerank

# Export graph
python3 graph/analyze --deck "Calculus" --export graph_output/
```

---

## Example Output

```text
📊 Top 10 Notes by PageRank (English Vocabulary)
┌──────┬──────────────────┬───────────┬─────────────────────┬──────────┐
│ Rank │ Front Field      │ PageRank  │ Tags                │ Refs In  │
├──────┼──────────────────┼───────────┼─────────────────────┼──────────┤
│ 1    │ baroque          │ 0.2840    │ vocab, english, art │ 2 notes  │
│ 2    │ style            │ 0.2340    │ vocab, english      │ 2 notes  │
│ 3    │ flamboyant       │ 0.1840    │ vocab, english      │ 1 note   │
│ 4    │ ornate           │ 0.1540    │ vocab, english      │ 1 note   │
│ 5    │ rococo           │ 0.1440    │ vocab, english, art │ 0 notes  │
...

💡 Insight: "baroque" and "style" are hub concepts in this deck.
   They're referenced by multiple other cards.
```

---

## Next Steps (TODO)

### Phase 5: CLI Tool

- [ ] Create `graph/analyze.py` - Main CLI
- [ ] Add `--deck` filter
- [ ] Add `--all-decks` option
- [ ] Add `--top N` ranking
- [ ] Add `--export` format (JSON, GraphML)
- [ ] Add `--isolated` (find disconnected notes)
- [ ] Add `--hubs` (find high-PageRank notes)

### Phase 6: Integration

- [ ] Load data from `data/anki/notes.json.gz` (GitHub)
- [ ] Merge with R2 data (when available)
- [ ] Add Makefile target: `make graph-analyze`

### Phase 7: Visualization (Optional)

- [ ] Export to GraphML (for Gephi)
- [ ] Export to D3.js format (web viz)
- [ ] Terminal-based graph view

---

## Design Decisions

### 1. Per-Deck Only

**Why:** Decks are distinct knowledge domains (language vs math vs science).

**Implementation:** `group_by_deck()` → build separate graphs → no cross-deck edges.

### 2. Directed Graph

**Why:** References have natural direction (Front field → appears in → Other fields).

**Implementation:** `nx.DiGraph()` not `nx.Graph()`.

### 3. Edge Weights

**Why:** Not all references are equal.

| Reference Type          | Weight |
| ----------------------- | ------ |
| Front→Front (component) | 3.0    |
| Front→Back (content)    | 2.0    |
| Other→Front             | 1.5    |
| Other→Back              | 1.0    |

### 4. Stop Words Filter

**Why:** Avoid creating edges for common words ("the", "is", "which").

**Implementation:** `STOP_WORDS` set in `parser.py`.

### 5. Tokenization (min 3 chars)

**Why:** Avoid edges for short words ("an", "is", "at").

**Implementation:** `min_length=3` in `tokenize()`.

---

## Running Tests

```bash
# All graph tests
python3 -m pytest graph/tests/ -v

# Specific test file
python3 -m pytest graph/tests/test_builder.py -v

# With coverage
python3 -m pytest graph/tests/ --cov=graph --cov-report=html
```

---

## Dependencies

```ini
networkx>=3.0      # Graph algorithms (PageRank)
scipy              # Required by networkx for PageRank
pytest             # Testing framework
```

Install:

```bash
pip install networkx scipy pytest
```

---

## Security

| Data            | Location                         | Never Leaves |
| --------------- | -------------------------------- | ------------ |
| Graph structure | Memory → `graph_output/`         | Your machine |
| PageRank scores | Memory → `graph_output/`         | Your machine |
| Note content    | Never loaded (only Front fields) | N/A          |

**`.gitignore` blocks:** `graph_output/`

---

## TDD Approach Followed

1. ✅ Write failing test
2. ✅ Write minimal code to pass
3. ✅ Refactor
4. ✅ Repeat

**Total:** 37 tests written before full implementation complete.

---

## Current Status

**Core infrastructure: COMPLETE** ✅

- Parser: ✅ 14/14 tests
- References: ✅ 10/10 tests
- Builder: ✅ 13/13 tests

**CLI tool: TODO**

- analyze.py: Not yet created
- Integration with fetch: Not yet created

**Ready for next phase!**
