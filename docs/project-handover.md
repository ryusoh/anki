# Anki Knowledge Graph Project - Complete Documentation

**Last Updated:** March 15, 2026  
**Status:** Functional but requires security review  
**Critical:** See SECURITY INCIDENT section below

> **Revision note (July 2026):** This document is a dated handover snapshot.
> The custom Three.js layer it originally described (`js/graph/viz_utils.js`,
> `js/graph/graph_viz.js`, `js/graph/lod_utils.js`) and its jest tests in
> `graph/tests/*.test.js` were removed (commit `a407b0ee` and follow-ups); the
> current visualization is a single browser module, `js/graph/graph.js` — see
> `js/graph/README.md`. The directory trees and testing sections below have
> been corrected; other details may still reflect the March 2026 state.

---

## Project Overview

This project builds a **knowledge relationship graph** from Anki flashcard data while keeping actual card content private. The system splits data between:

- **GitHub (Public):** Anonymized metadata, graph structure, code
- **Cloudflare R2 (Private):** Full card content (questions, answers, tags)
- **Local Machine:** Where both datasets merge for visualization

### Core Problem Solved

Anki users want to visualize relationships between their cards (which cards reference which concepts, which are most important, etc.) but cannot put card content on GitHub publicly. This project solves that by:

1. Fetching anonymized metadata to GitHub (no card content)
2. Storing full content privately in Cloudflare R2
3. Building knowledge graphs locally by merging both sources
4. Using PageRank to identify "hub" cards that connect many concepts

---

## ⚠️ CRITICAL: SECURITY INCIDENT

**What Happened:**

- `graph/graph_data.json` containing private card content (`flds` field) was accidentally committed to GitHub
- File contained actual Anki card questions/answers
- Was publicly accessible on GitHub for a period of time

**How It Was Fixed:**

1. File removed from current commit
2. Git history rewritten with `git filter-branch` to remove from ALL commits
3. Force pushed to GitHub
4. Added to `.gitignore` permanently
5. Created `graph/.gitignore` blocking all JSON files
6. Implemented automated security check (`data/anki/security_check.py`)
7. Security check now runs in `make precommit-fix`

**Current Security Measures:**

- `.gitignore` blocks `graph/*.json` and `data/cloudflare/`
- Automated security scanner checks ALL tracked files for private data
- Build FAILS if `flds` + `mid`/`guid` combination detected
- Multi-layer protection (gitignore + scanner + git itself)

**For New AI Agents:**

- **NEVER** commit files with `flds` field to GitHub
- **NEVER** commit full note structures (flds + tags + mid)
- **ALWAYS** run `make security` before committing
- **ALWAYS** keep private data in `data/cloudflare/` (gitignored)
- If security check fails, DO NOT COMMIT - remove private data first

**See:** `docs/security-protocol.md` for full security documentation

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Anki Desktop App                         │
│  collection.anki2 (SQLite database)                         │
│  - notes table (id, guid, mid, flds, tags, ...)             │
│  - cards table (id, nid, did, scheduling, ...)              │
│  - revlog table (review history)                            │
│  collection.media/ (5.2 GB images, audio)                   │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ fetch.py (local script)
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────────┐         ┌───────────────────┐
│   GitHub Repo     │         │  Cloudflare R2    │
│   (Public)        │         │  (Private)        │
│                   │         │                   │
│ notes.json.gz     │         │ collection/       │
│  - id, guid, mid  │         │  notes.json.gz    │
│  - mod, usn, csum │         │   - id, guid, mid │
│  - NO flds/tags   │         │   - flds, tags    │
│                   │         │                   │
│ cards.json.gz     │         │  cards.json.gz    │
│  - scheduling     │         │   - all cards     │
│  - deck names     │         │   - deck info     │
│                   │         │                   │
│ reviews/YYYY-MM   │         │  reviews.json.gz  │
│  - history        │         │   - full history  │
│                   │         │                   │
│ graph/            │         │  notes/           │
│  - index.html     │         │   {guid}.json.gz  │
│  - visualization  │         │   - individual    │
└───────────────────┘         └───────────────────┘
        │                               │
        └───────────┬───────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Local Merge (Browser)│
        │  - Load from GitHub   │
        │  - Load from R2       │
        │  - Build graph        │
        │  - PageRank analysis  │
        │  - Visualization      │
        └───────────────────────┘
```

### File Structure

```
addons21/
├── data/anki/
│   ├── fetch                      # Fetch from Anki DB
│   ├── upload-to-r2               # Upload to Cloudflare R2
│   ├── download-from-r2           # Download from R2
│   ├── security_check.py          # CRITICAL: Security scanner
│   ├── export_data.py             # Export graph data
│   └── ...
│
├── data/cloudflare/               # R2 STAGING (GITIGNORED!)
│   └── collection/
│       ├── notes.json.gz          # Full notes with flds
│       ├── cards.json.gz          # All cards
│       └── ...
│
├── graph/
│   ├── index.html                 # 3D visualization
│   ├── graph_data.json            # Graph data (GITIGNORED!)
│   ├── parser.py, builder.py, ... # Data pipeline (Python)
│   └── tests/
│       ├── test_parser.py         # Pipeline tests (Python)
│       ├── test_builder.py
│       └── ...
│
├── js/graph/
│   └── graph.js                   # Visualization (browser ES module)
│
├── css/graph.css                  # Visualization styles
│
├── docs/
│   ├── security-protocol.md       # Security documentation
│   ├── anki-knowledge-graph-architecture.md
│   ├── graph-analysis-guide.md
│   └── ...
│
├── .gitignore                     # CRITICAL: Blocks private data
├── graph/.gitignore               # Blocks all JSON in graph/
└── Makefile                       # Build targets
```

---

## Key Components

### 1. Data Fetching (`data/anki/fetch`)

**Purpose:** Fetch data from Anki's SQLite database

**What it exports:**

- **For GitHub (anonymized):**
  - `notes.json.gz` - id, guid, mid, mod, usn, csum, flags (NO flds, NO tags)
  - `cards.json.gz` - Card scheduling data
  - `decks.json` - Deck names only
  - `reviews/*.json.gz` - Review history by month

- **For R2 (full content):**
  - `collection/notes.json.gz` - Full notes with flds, tags
  - `collection/cards.json.gz` - All cards with deck info
  - `collection/reviews/YYYY-MM.json.gz` - Full review history by month
  - `notes/{guid}.json.gz` - Individual notes for lookup

**Usage:**

```bash
# Fetch for GitHub only
./fetch

# Fetch + stage for R2
./fetch --stage-r2
```

### 2. R2 Upload (`data/anki/upload-to-r2`)

**Purpose:** Upload private content to Cloudflare R2

**Features:**

- Sync mode (deletes orphaned notes from R2)
- Progress bars with parallel uploads
- Test upload before bulk transfer
- Incremental updates (only changed notes)

**Usage:**

```bash
# Upload with sync
./upload-to-r2 --upload-only --sync --verbose

# Or via Makefile
make fetch-r2
```

**Credentials Setup:**

```bash
cat > ~/.anki-r2/credentials << EOF
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET=anki-content
EOF
chmod 600 ~/.anki-r2/credentials
```

### 3. Security Check (`data/anki/security_check.py`)

**Purpose:** EXTREMELY RIGOROUS scan for private data before commit

**What it checks:**

1. All git-tracked files for `flds` + `mid`/`guid` combinations
2. Verifies `data/cloudflare/` is in `.gitignore`
3. Verifies `graph/*.json` is in `.gitignore`
4. Parses JSON files for private note structures

**When it runs:**

- Automatically in `make precommit-fix`
- Standalone: `make security`

**What happens on failure:**

```
======================================================================
🚨 SECURITY CHECK FAILED - PRIVATE DATA DETECTED 🚨
======================================================================
DO NOT COMMIT! Remove private data immediately!
```

### 4. Graph Visualization (`graph/index.html`)

**Purpose:** Beautiful 3D visualization of knowledge graph

**Features:**

- Three.js-based 3D rendering
- Deck-based clustering (each deck in separate region)
- PageRank-based node sizing (important cards are larger)
- Color-coded by deck
- Click nodes for details
- Drag to rotate, scroll to zoom

**Visual Elements:**

- Nodes = Cards (spheres)
- Size = PageRank (importance)
- Color = Deck
- Edges = References between cards
- Clusters = Decks arranged in circle

**Usage:**

```bash
# Generate graph data
python3 graph/export_data.py

# Open in browser
open graph/index.html

# Or via Makefile
make graph-analyze
```

### 5. Graph Rendering (`js/graph/graph.js`)

**Purpose:** Browser-side rendering of the exported graph

> The former performance layer (`js/graph/lod_utils.js`, `graph_viz.js`,
> `viz_utils.js` — LOD, frustum culling, instanced meshes) was removed.
> Rendering now lives entirely in `js/graph/graph.js`, which draws layered
> `THREE.Points` clouds instead. LOD and frustum culling are again listed
> under Future Work.

**Performance (historical figures for the removed layer):**

- 100 nodes: Instant
- 1,000 nodes: Smooth 60 FPS
- 5,000 nodes: ~30 FPS
- 10,000+ nodes: Requires optimization (see Future Work)

---

## Makefile Targets

```bash
# Install dependencies
make install

# Fetch data
make fetch                    # GitHub data only
make fetch-and-stage-r2       # + R2 staging
make fetch-r2                 # Upload to R2

# Graph analysis
make graph-analyze            # Analyze all decks
make graph-deck DECK=J        # Analyze specific deck (J, C, E, S, T, F)
make graph-export             # Export for Gephi
make graph-viz                # Create HTML visualization

# Security
make security                 # Run security check

# Pre-commit
make precommit                # Run checks (no fixes)
make precommit-fix            # Fix issues + security check

# Tests
make check                    # Run all tests

# Formatting
make fmt                      # Format code
make fmt-check               # Check formatting
make lint                    # Run linters
make lint-fix                # Fix lint issues
```

---

## Deck Aliases

Quick reference for deck names:

| Alias    | Deck Name | Notes                   |
| -------- | --------- | ----------------------- |
| `J`, `1` | 言語日語  | Japanese (50K cards)    |
| `C`, `2` | 言語粵語  | Cantonese (34K cards)   |
| `E`, `3` | 言語英語  | English (30K cards)     |
| `S`, `4` | 言語呉語  | Wu/Shanghai (19K cards) |
| `T`, `5` | 言語台語  | Taiwanese (15K cards)   |
| `F`, `6` | 金融      | Finance (13K cards)     |

---

## Testing

### Test Files

The jest tests that used to live in `graph/tests/` were removed along with
the viz layer they tested. What remains is the Python suite for the data
pipeline:

```
graph/tests/
├── test_parser.py             # Field/reference parsing
├── test_builder.py            # Graph construction
├── test_export_data.py        # Data export
├── test_incremental.py        # Incremental export
└── ... (see graph/tests/)
```

### Run Tests

```bash
# All suites
make check

# Graph tests only (run from the repo ROOT — root conftest.py mocks aqt/anki)
python3 -m pytest graph/tests/ -v

# Security check
make security
```

---

## Known Issues & Limitations

### Current Limitations

1. **Scale:** Max ~10,000 nodes smoothly (beyond that requires WebGL2/compute shaders)
2. **Edges:** Too many edges cause visual clutter (22K+ edges for 1K nodes)
3. **Mobile:** Not optimized for mobile browsers
4. **Real-time:** No real-time updates (must regenerate)

### Known Bugs

1. **Pulse animation** was accumulating scale (fixed)
2. **LOD clearing meshes** before recreation (fixed)
3. **Camera positioning** too close initially (fixed)
4. **Node colors** too pale (fixed with saturated colors)

### Performance Bottlenecks

1. **Edge rendering** - 22K lines slow down rendering
2. **LOD updates** - Every 500ms causes stutter
3. **Raycasting** - Click detection slow with 1K+ nodes
4. **JSON parsing** - Large graph_data.json slow to load

---

## Future Work

### Immediate Priorities

1. **Client-side R2 fetch** - Load data directly from R2 in browser (no committed JSON)
2. **Edge bundling** - Reduce visual clutter from edges
3. **Progressive loading** - Load visible nodes first
4. **Web Workers** - Move graph computation off main thread

### Medium-term

1. **LOD system** - Proper level-of-detail for distant nodes
2. **Frustum culling** - Only render visible nodes
3. **Octree spatial index** - Fast neighbor queries
4. **Cluster analysis** - Automatically detect knowledge clusters

### Long-term

1. **WebGL2 compute shaders** - GPU-based positioning for 100K+ nodes
2. **Server-side clustering** - Load cluster centers, drill down for details
3. **Data streaming** - Stream nodes as camera moves
4. **Collaborative** - Multiple users viewing same graph

---

## Dependencies

### Python

```txt
networkx>=3.0      # Graph algorithms
scipy>=1.10        # PageRank computation
boto3>=1.28        # R2 uploads
pytest>=8.0        # Testing
```

### JavaScript

Three.js `0.128.0` is loaded in the browser from the jsDelivr CDN via an
import map in `graph/index.html` — there is no npm dependency, build step,
or JS test dependency for the graph.

### System

- Python 3.10+
- Node.js 18+
- Cloudflare R2 account
- Anki desktop app

---

## Deployment

### GitHub Pages

The visualization can be deployed to GitHub Pages:

1. Enable GitHub Pages in repo settings
2. Set source to `main` branch, `/graph` folder
3. Generate `graph/graph_data.json` locally
4. Commit and push
5. Access at `https://username.github.io/repo/graph/`

**WARNING:** Only deploy anonymized data! Never commit `graph_data.json` with `flds` field!

### Local Development

```bash
# Start local server
python3 -m http.server 8000

# Open in browser
open http://localhost:8000/graph/index.html
```

---

## Troubleshooting

### "No notes found"

```bash
# Check staging exists
ls -la data/cloudflare/collection/notes.json.gz

# Regenerate
python3 data/anki/fetch --stage-r2
```

### "Security check failed"

```bash
# Identify flagged file
make security

# If it's graph_data.json:
git rm --cached graph/graph_data.json
echo "graph/*.json" >> .gitignore

# If it's R2 staging:
echo "data/cloudflare/" >> .gitignore
```

### "Out of memory" (Prettier)

```bash
# Exclude large files
# Edit Makefile to exclude:
# - *.min.js
# - node_modules/
# - assets/vendor/
```

### "R2 upload failed: 403 Forbidden"

```bash
# Check credentials
cat ~/.anki-r2/credentials

# Regenerate R2 API token
# Cloudflare Dashboard → R2 → API Tokens → Create token
# Template: Object Read & Write
# Bucket: anki-content
```

### "Graph not showing nodes"

```bash
# Check browser console (Cmd+Option+J)
# Look for:
# - "Created X nodes" message
# - "Scene has X children"
# - Any WebGL errors

# Try different browser (Chrome/Firefox)
# Check WebGL enabled
```

---

## Contact & Support

### Documentation

- `docs/security-protocol.md` - Security procedures
- `docs/graph-analysis-guide.md` - Graph usage guide
- `docs/r2-upload-guide.md` - R2 setup guide
- `docs/anki-knowledge-graph-architecture.md` - Architecture overview

### Key Files

- `data/anki/security_check.py` - Security scanner (READ THIS)
- `graph/index.html` - Main visualization
- `.gitignore` - Critical security file
- `Makefile` - All commands

### Emergency Procedures

**If private data is committed:**

1. **DO NOT PUSH** - if already pushed, see step 2
2. **Remove from history:**

   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch path/to/file' \
     --prune-empty --tag-name-filter cat -- --all
   git push --force origin main
   ```

3. **Contact GitHub support** to purge CDN cache
4. **Review security procedures** in `docs/security-protocol.md`

---

## Credits & Acknowledgments

**Original Concept:** Knowledge graph visualization for Anki cards  
**Implementation:** TDD approach with 76+ tests  
**Security:** Multi-layer protection system  
**Visualization:** Three.js with LOD and clustering

**Lessons Learned:**

- Always verify .gitignore before committing
- Automated security checks are critical
- Never trust AI with private data without verification
- Test security measures actually work

---

**END OF DOCUMENTATION**

_This document was created to enable another AI agent to take over the project from scratch based on all work completed._
