# 3D Graph Visualization

Interactive 3D visualization of the Anki knowledge graph, rendered with Three.js.

The whole visualization is a single browser ES module, `graph.js`, loaded by
`graph/index.html`. It has no exports and boots the scene at import time
(top-level await). There is no npm install or build step: Three.js and
OrbitControls come from the jsDelivr CDN via the import map in `index.html`,
which also maps the `#js/`, `#ui/`, and `#data/` path aliases.

## Features

- **Layered point-cloud rendering** — grey background mist, always-on-top
  highlight layer, and an ambient particle mist
- **Deck-based colors** — an HSLA palette assigned to decks by size
  (node count, descending), matching the live legend
- **Review-history timeline** — a slider (also arrow keys) scrubs through
  daily review activity, lighting up reviewed cards and their neighbors
- **Camera control** — drag to orbit, scroll to zoom (OrbitControls), plus
  WASD movement
- **Optional background image** — toggled via `GRAPH_BACKGROUND_IMAGE` in
  `js/config.js`

## Data loading

On page load, `graph.js` fetches `/graph/graph_data.json` and
`/graph/history_data.json`. If the private files are not present, it falls
back to the anonymized public copies on Cloudflare R2
(`graph_data_public.json` / `history_data_public.json`).

## File Structure

```
js/graph/
└── graph.js          # The visualization (browser ES module, no exports)

graph/
├── index.html        # Page shell: import map, UI chrome, loads graph.js
├── graph_data.json   # Exported graph data (gitignored)
├── history_data.json # Review history for the timeline (gitignored)
└── export_data.py    # Python export script
```

## Usage

### 1. Export Data

```bash
cd /Users/lz/Library/Application\ Support/Anki2/addons21
python3 graph/export_data.py
```

### 2. Open in Browser

Serve the repo root (the page uses absolute `/js/...` and `/graph/...` paths):

```bash
cd /Users/lz/Library/Application\ Support/Anki2/addons21
python3 -m http.server 8000
open http://localhost:8000/graph/index.html
```

## Testing

There are no JS tests for this module. The graph data pipeline (parsing,
building, export) is covered by the Python suite in `graph/tests/` — run it
from the repo root:

```bash
make test-py SUITE=graph/tests
```
