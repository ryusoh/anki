# Anki Graph Analysis - Quick Reference Card

**Your one-page cheat sheet for knowledge graph analysis**

---

## 🎯 Deck Aliases

**Use these instead of typing full deck names!**

| Alias    | Deck                   | Cards |
| -------- | ---------------------- | ----- |
| `J`, `1` | 言語日語 (Japanese)    | 50K   |
| `C`, `2` | 言語粵語 (Cantonese)   | 34K   |
| `E`, `3` | 言語英語 (English)     | 30K   |
| `S`, `4` | 言語呉語 (Wu/Shanghai) | 19K   |
| `T`, `5` | 言語台語 (Taiwanese)   | 15K   |
| `F`, `6` | 金融 (Finance)         | 13K   |

---

## 🚀 Common Commands

### Quick Analysis

```bash
# All decks overview
make graph-analyze

# Specific deck (use aliases!)
make graph-deck DECK=J
make graph-deck DECK=C
make graph-deck DECK=F

# Export for Gephi
make graph-export
```

### Full Workflow

```bash
# Fetch + analyze + upload
make precommit-fix
# → Prompts for fetch
# → Runs tests
# → Prompts for R2 upload
```

### Incremental Staging

```bash
# First run: stages all 161K notes (~5 min)
make fetch-and-stage-r2

# Future runs: only changed notes (~10 sec)
make fetch-and-stage-r2
```

---

## 📊 Understanding Output

### PageRank Scores

| Score Range             | Meaning   | Action           |
| ----------------------- | --------- | ---------------- |
| **High (>0.01)**        | Hub card  | Study first!     |
| **Medium (0.001-0.01)** | Connected | Normal           |
| **Low (<0.001)**        | Isolated  | Review or delete |

### Graph Metrics

| Metric         | What It Means                        |
| -------------- | ------------------------------------ |
| **Edges**      | References between cards             |
| **Density**    | How interconnected your knowledge is |
| **In-Degree**  | How many cards reference this one    |
| **Out-Degree** | How many other cards this references |

---

## 💡 Pro Tips

### Study Strategy

1. **Start with hub cards** (high PageRank)
   - They're referenced by many other cards
   - Understanding them helps with dozens of others

2. **Review isolated cards** (low PageRank)
   - Either add connections (tags, related cards)
   - Or consider deleting if truly isolated

3. **Compare decks**

   ```bash
   make graph-analyze
   ```

   - Denser decks = more interconnected knowledge
   - Sparser decks = may need more connections

### Performance Tips

| Scenario                   | Command                   | Time     |
| -------------------------- | ------------------------- | -------- |
| First staging              | `make fetch-and-stage-r2` | ~5 min   |
| Daily staging (no changes) | `make fetch-and-stage-r2` | ~2 sec   |
| Daily staging (10 changes) | `make fetch-and-stage-r2` | ~10 sec  |
| Upload all                 | `make fetch-r2`           | ~30 min  |
| Upload changes only        | `make fetch-r2`           | ~1-2 min |

### File Management

```bash
# View hash map (incremental staging cache)
cat .hash_map.json | head

# Force full re-staging
rm .hash_map.json
make fetch-and-stage-r2

# Clean R2 staging
rm -rf data/cloudflare
make fetch-and-stage-r2
```

---

## 📁 File Locations

| File/Directory     | Purpose                   | Git?   |
| ------------------ | ------------------------- | ------ |
| `.hash_map.json`   | Incremental staging cache | ❌ No  |
| `data/cloudflare/` | R2 staging                | ❌ No  |
| `graph_output/`    | Exported graphs           | ❌ No  |
| `graph/`           | Graph analysis code       | ✅ Yes |
| `docs/`            | Documentation             | ✅ Yes |

---

## 🔧 Troubleshooting

### "Staging all notes every time"

```bash
# Check if hash map exists
ls -la .hash_map.json

# If missing, recreate it
make fetch-and-stage-r2
```

### "Upload stuck"

```bash
# Stop and restart
# Ctrl+C, then:
make precommit-fix

# Check progress bar updates every file
```

### "Deck not found"

```bash
# List available decks
python3 graph/analyze.py --list-decks

# Or use aliases instead of full names
make graph-deck DECK=J  # Instead of 言語日語
```

---

## 📚 Full Documentation

| Doc                            | Purpose            |
| ------------------------------ | ------------------ |
| `docs/graph-analysis-guide.md` | Complete CLI guide |
| `docs/incremental-staging.md`  | Hash map & staging |
| `docs/deck-aliases.md`         | All deck aliases   |
| `docs/r2-upload-guide.md`      | R2 backup setup    |
| `SETUP.md`                     | Installation guide |

---

## 🎓 Example Workflow

```bash
# Morning study session
make graph-deck DECK=J
# → Shows top 10 hub cards
# → Study those first!

# After learning new cards
make precommit-fix
# → Stages only changed notes
# → Uploads to R2
# → Commits to GitHub

# Weekend review
make graph-analyze
# → See which decks are well-connected
# → Identify isolated cards to review
```

---

**Print this page or keep it open for quick reference!** 📋
