# Anki Knowledge Graph Architecture

## Overview

This system builds a **knowledge relationship graph** from Anki cards while keeping the actual card content private. The architecture splits data between:

- **GitHub** (public): Graph structure, metadata, relationships
- **Cloudflare R2** (private): Full card content (questions, answers, tags)

## Data Flow

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Anki Desktop App                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  collection.anki2 (SQLite)                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │   │
│  │  │   notes     │  │   cards     │  │      revlog         │   │   │
│  │  │  - id       │  │  - id       │  │  - id               │   │   │
│  │  │  - guid ★   │  │  - nid →    │  │  - cid →            │   │   │
│  │  │  - flds     │  │  - did      │  │  - ease             │   │   │
│  │  │  - tags     │  │  - due      │  │  - ivl              │   │   │
│  │  │  - mid      │  │  - reps     │  │  - ...              │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │   │
│  │                                                              │   │
│  │  collection.media/ (images, audio)                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ fetch.py (local script)
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────────────┐
│      GitHub Repo          │   │      Cloudflare R2 (Private)      │
│      (Public/Private)     │   │                                   │
│                           │   │  notes/{guid}.json.gz             │
│  data/anki/               │   │  ┌─────────────────────────────┐  │
│  ├── notes.json.gz        │   │  │ guid: "hNb(y8)oa*"          │  │
│  │   ┌─────────────────┐  │   │  │ flds: "Q: ... A: ..."       │  │
│  │   │ guid (★ bridge) │  │   │  │ tags: ["math", "calc"]      │  │
│  │   │ mid             │  │   │  └─────────────────────────────┘  │
│  │   │ id              │  │   │                                   │
│  │   │ csum            │  │   │  Encrypted at rest (optional)     │
│  │   │ ...             │  │   │  Access: API credentials only     │
│  │   └─────────────────┘  │   │                                   │
│  │                        │   └───────────────────────────────────┘
│  ├── cards.json.gz        │
│  │   ┌─────────────────┐  │
│  │   │ id              │  │
│  │   │ nid → notes.id  │  │
│  │   │ did → decks.id  │  │
│  │   │ due, ivl, reps  │  │
│  │   └─────────────────┘  │
│  │                        │
│  ├── decks.json           │
│  ├── reviews/YYYY-MM.json │
│  └── graph/               │
│      ├── nodes.json       │
│      └── edges.json       │
└───────────────────────────┘
```

## Data Split

### GitHub (Public - Anonymized)

| File                | Content                           | Size   | Purpose           |
|---------------------|-----------------------------------|--------|-------------------|
| `notes.json.gz`     | Note metadata **without content** | ~7 MB  | Graph nodes       |
| `cards.json.gz`     | Card scheduling data              | ~3 MB  | Learning stats    |
| `decks.json`        | Deck hierarchy                    | <1 KB  | Organization      |
| `reviews/*.json.gz` | Review history (monthly)          | ~22 MB | Learning patterns |
| `graph/nodes.json`  | Knowledge graph nodes             | TBD    | Graph structure   |
| `graph/edges.json`  | Relationships between nodes       | TBD    | Graph edges       |

**Fields in `notes.json.gz`:**

```json
{
  "id": 1214225649796, // Internal DB ID
  "guid": "hNb(y8)oa*", // ★ Stable identifier (bridge to R2)
  "mid": 1569057594173, // Note type ID
  "mod": 1664855079, // Modified timestamp
  "usn": 12673, // Sync sequence number
  "csum": 2651014713, // Field checksum
  "flags": 0 // User flags
}
```

**Excluded from GitHub:**

- ❌ `flds` - Actual card content (questions, answers)
- ❌ `tags` - User tags
- ❌ Media files (images, audio)

### Cloudflare R2 (Private - Full Content)

**Bucket structure:**

```text
anki-content/
├── collection/
│   ├── notes.json.gz           # All notes (flds, tags, data)
│   ├── cards-data.json.gz      # Cards with custom data field
│   ├── notetypes.json.gz       # Note type templates, CSS
│   ├── decks-config.json.gz    # Deck configurations
│   ├── media-registry.json     # Media file references
│   └── collection-config.json  # Collection metadata
└── notes/
    ├── {guid1}.json.gz         # Individual note lookup
    ├── {guid2}.json.gz
    └── ...
```

| Path                                | Content                               | Size (est.) |
|-------------------------------------|---------------------------------------|-------------|
| `collection/notes.json.gz`          | All notes with `flds`, `tags`, `data` | ~108 MB     |
| `collection/cards-data.json.gz`     | Cards with custom data field          | ~1 MB       |
| `collection/notetypes.json.gz`      | Note type templates, CSS, fields      | ~0.5 MB     |
| `collection/decks-config.json.gz`   | Deck configurations                   | ~0.1 MB     |
| `collection/media-registry.json`    | Media file references                 | ~0.1 MB     |
| `collection/collection-config.json` | Collection metadata                   | <0.1 MB     |
| `notes/{guid}.json.gz`              | Individual notes (for lookup)         | ~108 MB     |

**Total: ~110 MB compressed** (vs 5.2 GB media files stored locally)

**Structure:**

```json
// collection/notes.json.gz
[
  {
    "id": 1214225649796,
    "guid": "hNb(y8)oa*",
    "mid": 1569057594173,
    "flds": "What is calculus?::The study of continuous change...",
    "tags": "math calculus important",
    "data": ""
  }
]

// notes/{guid}.json.gz
{
  "guid": "hNb(y8)oa*",
  "mid": 1569057594173,
  "flds": "What is calculus?::The study of continuous change...",
  "tags": "math calculus important",
  "data": ""
}

// collection/notetypes.json.gz
[
  {
    "id": 1569057594173,
    "name": "Basic",
    "config": {
      "css": ".card { font-family: ... }",
      "templates": [
        {"name": "Card 1", "qfmt": "{{Front}}", "afmt": "{{Back}}"}
      ],
      "flds": [{"name": "Front"}, {"name": "Back"}]
    }
  }
]
```

## The Bridge: `guid`

The `guid` field is the **only link** between GitHub and R2:

| Property       | Value                              |
|----------------|------------------------------------|
| **Format**     | 9-character base64-like string     |
| **Stability**  | Never changes (even across syncs)  |
| **Uniqueness** | Unique per note                    |
| **Public**     | Yes (in GitHub)                    |
| **Sensitive**  | No (meaningless without R2 access) |

### How It Works

```text
GitHub                          R2
 ┌─────────────────┐           ┌─────────────────────────┐
 │ notes.json.gz   │           │ notes/hNb(y8)oa*.json.gz│
 │                 │           │                         │
 │ guid: "hNb(...)"│──────────▶│ { guid: "hNb(...)",     │
 │ mid: 1569...    │  lookup   │   flds: "...",          │
 │                 │           │   tags: [...] }         │
 └─────────────────┘           └─────────────────────────┘
```

## Local Workflow

```bash
# 1. Fetch from Anki DB (local)
./fetch

# 2. Commit anonymized data to GitHub
git add data/anki/ && git commit -m "Update Anki stats"
git push

# 3. Upload full content to R2 (private)
./upload-to-r2  # uses R2 API credentials

# 4. Build knowledge graph locally (merge both sources)
./build-graph   # downloads from R2, merges with GitHub data
```

## Knowledge Graph Structure

### Nodes (from Notes)

```json
{
  "id": "hNb(y8)oa*", // note.guid
  "type": "note",
  "mid": 1569057594173, // note type
  "card_count": 2, // number of cards from this note
  "decks": [456, 789], // deck IDs (from cards)
  "first_seen": 1234567890, // note.mod
  "review_count": 45, // aggregated from revlog
  "avg_ease": 2.5 // aggregated from revlog
}
```

### Edges (Relationships)

| Type              | From | To   | Weight |
|-------------------|------|------|--------|
| `shared_deck`     | note | note | 1.0    |
| `shared_notetype` | note | note | 1.0    |
| `same_note`       | card | card | 1.0    |
| `in_deck`         | note | deck | 1.0    |

## Security Model

| Component             | Visibility      | Access Control         |
|-----------------------|-----------------|------------------------|
| GitHub repo           | Public/Private  | GitHub auth            |
| R2 bucket             | Private         | API credentials        |
| `guid`                | Public          | Meaningless without R2 |
| Card content (`flds`) | Never on GitHub | R2 credentials only    |
| Tags                  | Never on GitHub | R2 credentials only    |

## Storage Costs (Cloudflare R2)

| Item                     | Size        | Cost/Month  |
|--------------------------|-------------|-------------|
| Full notes (108 MB text) | ~108 MB     | $0.0015     |
| Media files (optional)   | 5.2 GB      | $0.078      |
| **Total (text only)**    | **~0.1 GB** | **~$0.002** |

## Files

| File                     | Purpose                                  |
|--------------------------|------------------------------------------|
| `data/anki/fetch`        | Fetches Anki DB, exports anonymized data |
| `data/anki/upload-to-r2` | Uploads full content to R2 (TODO)        |
| `data/anki/build-graph`  | Merges GitHub + R2 data locally (TODO)   |

## Future Extensions

1. **Encrypted R2 storage** - Encrypt content before upload
2. **Automatic R2 sync** - GitHub Action to upload on push
3. **Graph visualization** - Web UI showing knowledge relationships
4. **Tag-based edges** - Connect notes by shared tags (from R2)
5. **Content similarity** - Analyze `flds` for semantic relationships
