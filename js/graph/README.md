# 3D Graph Visualization

Interactive 3D visualization of Anki knowledge graph using Three.js.

## Features

- 🎨 **Deck-based colors** - Each deck has a unique color
- 🌐 **True 3D nodes** - Spheres with metallic materials
- ✨ **No auto-rotation** - Only rotates when you drag
- 📍 **Bounded layout** - All nodes stay within view
- 🔍 **Zoom/pan** - Full camera control

## Usage

### 1. Export Data

```bash
cd /Users/lz/Library/Application\ Support/Anki2/addons21
python3 graph/export_data.py
```

### 2. Open in Browser

```bash
open graph/index.html
```

**Note:** Requires a local server due to ES6 modules. Use:

```bash
cd /Users/lz/Library/Application\ Support/Anki2/addons21
python3 -m http.server 8000
open http://localhost:8000/graph/index.html
```

## File Structure

```
js/graph/
├── viz_utils.js      # Pure JS utilities (tested)
├── graph_viz.js      # Three.js visualization
└── package.json      # JS dependencies

graph/
├── index.html        # Main HTML
├── graph_data.json   # Exported data
└── export_data.py    # Python export script

graph/tests/
└── test_graph_viz.test.js  # JS tests
```

## Testing

```bash
cd js/graph
npm install
npm test
```

## API

### `viz_utils.js`

```javascript
import { stripHtml, assignDeckColor, positionNodes } from "./viz_utils.js";

// Strip HTML from card content
const clean = stripHtml("<b>bold</b> text");

// Get consistent color for deck
const color = assignDeckColor("日本語", predefinedColors);

// Position nodes with force-directed layout
const positioned = positionNodes(nodes, { maxBounds: 250 });
```

### `graph_viz.js`

```javascript
import { initGraph } from "./graph_viz.js";

// Initialize visualization
const viz = initGraph("canvas", { nodes, links });

// Handle node clicks
viz.onNodeClick((node) => {
  console.log("Clicked:", node.label, node.deck);
});
```

## Deck Colors

Colors are assigned consistently based on deck name hash. Predefined colors:

| Deck     | Color            |
| -------- | ---------------- |
| 言語日語 | #FF6B6B (Red)    |
| 言語粵語 | #4ECDC4 (Teal)   |
| 言語英語 | #45B7D1 (Blue)   |
| 言語呉語 | #96CEB4 (Green)  |
| 言語台語 | #FFEAA7 (Yellow) |
| 金融産研 | #DDA0DD (Plum)   |
| 金融理論 | #98D8C8 (Mint)   |

Unknown decks get auto-generated HSL colors.
