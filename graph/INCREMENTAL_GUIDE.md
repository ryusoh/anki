# Incremental Graph Export System

Progressively scale from 100 → 160,000+ nodes for testing and visualization.

## Why Incremental?

- **Test performance** at different scales
- **Avoid browser crashes** from loading 160K nodes at once
- **Gradual optimization** - find bottlenecks early
- **Background updates** - no manual intervention needed

## Quick Start

### Manual Increments

```bash
# Next increment (100 → 200 → 300 → ...)
python3 graph/incremental_export.py

# Go to specific size
python3 graph/incremental_export.py --size 500

# Reset to 100
python3 graph/incremental_export.py --reset

# Check current status
python3 graph/incremental_export.py --status
```

### Background Watcher

```bash
# Auto-increment every 30 seconds
python3 graph/watch_and_update.py

# Custom interval (60 seconds)
python3 graph/watch_and_update.py --interval 60

# Stop at 1000 nodes
python3 graph/watch_and_update.py --max 1000

# Auto-refresh browser (Chrome)
python3 graph/watch_and_update.py --auto-refresh

# Run once and exit
python3 graph/watch_and_update.py --once
```

## Scaling Strategy

| Sample Size     | Increment | Use Case                             |
| --------------- | --------- | ------------------------------------ |
| 100-1,000       | +100      | Initial testing, visual verification |
| 1,000-5,000     | +100      | Performance baseline                 |
| 5,000-10,000    | +500      | Stress testing                       |
| 10,000-50,000   | +1,000    | Large-scale testing                  |
| 50,000-160,000+ | +5,000    | Production scale                     |

## File Structure

```
graph/
├── incremental_export.py       # Main export script
├── watch_and_update.py         # Background watcher
├── .incremental_config.json    # Current sample size (auto-generated)
├── graph_data.json             # Exported data
└── tests/
    └── test_incremental.py     # TDD tests
```

## Configuration

`.incremental_config.json`:

```json
{
  "sample_size": 200,
  "increment": 100
}
```

## Browser Refresh

For auto-refresh on macOS:

```bash
python3 graph/watch_and_update.py --auto-refresh
```

For manual refresh:

```bash
# In browser
Cmd + R

# Or run
open http://localhost:8000/graph/index.html
```

## Performance Tips

### 100-1,000 nodes

- ✅ Smooth 60 FPS
- ✅ Full interactivity
- ✅ All features work

### 1,000-10,000 nodes

- ⚠️ May see slight slowdown
- ⚠️ Consider reducing particle count
- ✅ Still usable

### 10,000-100,000 nodes

- ⚠️ Significant slowdown expected
- 💡 Consider level-of-detail rendering
- 💡 Consider server-side clustering

### 100,000+ nodes

- 💡 Need WebGL optimization
- 💡 Consider data streaming
- 💡 Implement frustum culling

## Monitoring

Watch file size:

```bash
watch -n 1 'ls -lh graph/graph_data.json'
```

Watch node count:

```bash
watch -n 1 'python3 -c "import json; print(len(json.load(open(\"graph/graph_data.json\"))[\"nodes\"]))"'
```

## Troubleshooting

### "Out of memory"

- Reduce sample size: `python3 graph/incremental_export.py --size 500`
- Clear browser cache
- Close other tabs

### "Browser crashes"

- Start smaller: `python3 graph/incremental_export.py --reset`
- Increment slowly: +100 at a time
- Use Firefox (handles large datasets better)

### "Watcher not incrementing"

- Check interval: `--interval 10` (faster)
- Check max limit: remove `--max` if set
- Check logs for errors

## TDD Tests

```bash
# Run incremental export tests
cd graph
python3 -m pytest tests/test_incremental.py -v
```

## Example Workflow

```bash
# 1. Start fresh
python3 graph/incremental_export.py --reset

# 2. Start watcher in background
python3 graph/watch_and_update.py --interval 60 --max 1000 &

# 3. Open browser
open http://localhost:8000/graph/index.html

# 4. Watch it grow: 100 → 200 → 300 → ... → 1000

# 5. Stop watcher when done
pkill -f watch_and_update
```

## Next Steps

For production with 160K+ nodes:

1. **Implement LOD** (Level of Detail)
2. **Add frustum culling** (only render visible nodes)
3. **Use WebGL instancing** (batch rendering)
4. **Implement data streaming** (load chunks progressively)
5. **Add server-side clustering** (group nearby nodes)
