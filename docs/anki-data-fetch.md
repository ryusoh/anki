# Anki Data Fetch

Fetch Anki collection stats and export to Git-friendly JSON format.

## Overview

This tool exports your Anki collection statistics to JSON files that can be safely committed to Git:

- **Card content is removed** - Only scheduling stats and review history are exported
- **Privacy-safe** - No actual flashcard questions/answers are included
- **Git-efficient** - Monthly partitions mean only new data is added each sync
- **Cross-machine** - Works on any machine with Anki installed

## Quick Start

```bash
# Using Make (recommended)
make fetch

# Or directly with Python
python3 data/anki/fetch

# Quiet mode
python3 data/anki/fetch -q

# Verbose mode
python3 data/anki/fetch -v

# Help
python3 data/anki/fetch --help
```

## Output Files

After running `fetch`, the following files are created in `data/anki/`:

| File                      | Size        | Description                           |
| ------------------------- | ----------- | ------------------------------------- |
| `cards.json.gz`           | ~2.6 MB     | Current card states (intervals, reps) |
| `decks.json`              | <1 KB       | Deck names and IDs                    |
| `reviews/YYYY-MM.json.gz` | ~100-700 KB | Monthly review history partitions     |

**Total size:** ~24 MB for full history

## Data Exported

### Preserved (Stats Only)

- Card scheduling: due date, interval, ease factor, reps, lapses
- Review history: timestamp, ease, time taken, review type
- Deck structure: names and IDs
- Note type metadata

### Removed (Privacy)

- Card content (questions, answers, definitions)
- Tags
- Custom note fields
- Any personal data

## Committing to Git

```bash
# Add the exported data
git add data/anki/

# Commit
git commit -m "Update Anki stats"

# Push to remote
git push
```

### Git Efficiency

- **First commit:** ~24 MB (full history)
- **Subsequent commits:** ~100-200 KB (only current month updates)
- **Monthly files:** Never change after creation (efficient for Git)

## Workflow

### On Your Local Machine

1. Make your Anki reviews as usual
2. Run `make fetch` to export latest stats
3. Commit and push to GitHub

### On a New Machine (after cloning)

1. Clone the repository
2. Install Anki and sync your collection
3. Run `make fetch` to update stats
4. All data is now consistent with your local Anki

## File Structure

```text
project-root/
├── Makefile
├── data/
│   └── anki/
│       ├── fetch              # CLI command
│       ├── export_for_git.py  # Export logic
│       ├── README.md          # This documentation
│       ├── cards.json.gz      # Card states
│       ├── decks.json         # Deck info
│       └── reviews/           # Monthly partitions
│           ├── 2026-02.json.gz
│           ├── 2026-01.json.gz
│           └── ...
```

## Troubleshooting

### "No Anki collection found"

Make sure Anki is installed and you have a profile created. The script looks for:

- macOS: `~/Library/Application Support/Anki2/<profile>/collection.anki2`

### Permission errors

Run with appropriate permissions or check Anki is not running during export.

## Technical Details

- **Format:** Gzip-compressed JSON
- **Schema:** Anki SQLite tables (minus content fields)
- **Partitions:** One file per month (`YYYY-MM.json.gz`)
- **Reviews:** Sorted by timestamp within each file
