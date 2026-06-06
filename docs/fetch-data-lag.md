# Fetch Data Lag: Why `make fetch` Doesn't See Changes Immediately

## Summary

After editing or reviewing cards in Anki, `make fetch` may not reflect those changes for several seconds to a few minutes. This is caused by SQLite's Write-Ahead Logging (WAL), not any network or API delay.

## How `make fetch` Reads Data

`make fetch` reads directly from Anki's live SQLite database:

```
~/Library/Application Support/Anki2/LZ/collection.anki2
```

There is no network call, no AnkiConnect API, no AnkiWeb sync involved. The fetch script copies the database file via `shutil.copy2()` and queries the copy.

## Why the Lag Exists: SQLite WAL

Anki uses SQLite in WAL (Write-Ahead Logging) mode. When you perform card operations:

1. Anki writes changes to the **WAL file** (`collection.anki2-wal`), not directly to the main database file
2. The main `collection.anki2` only gets updated when Anki performs a **WAL checkpoint** -- this merges the WAL back into the main DB
3. `make fetch` copies the main DB file, which may not include uncommitted WAL changes

### What triggers a WAL checkpoint?

- SQLite auto-checkpoints when WAL reaches ~1000 pages (~4MB)
- Anki checkpoints on collection close (switching profiles, quitting Anki)
- Anki checkpoints on sync (AnkiWeb sync)
- Anki checkpoints periodically during idle time

### Typical lag duration

| Scenario                     | Lag                                                              |
| ---------------------------- | ---------------------------------------------------------------- |
| Rapid reviewing (many cards) | A few seconds (WAL fills quickly, auto-checkpoint)               |
| Single card edit             | Up to a few minutes (WAL stays small, waits for idle checkpoint) |
| After closing/reopening Anki | None (checkpoint on close)                                       |
| After AnkiWeb sync           | None (checkpoint on sync)                                        |

## Workarounds

To ensure `make fetch` sees the latest data:

- **Close Anki** before running `make fetch` (forces a checkpoint on close)
- **Trigger a sync** (AnkiWeb sync forces a checkpoint)
- **Wait a few minutes** for Anki's idle checkpoint to run

## Why Not Read the WAL Directly?

Opening the database with WAL support while Anki is also using it risks lock contention and potential corruption. The current design of copying the main DB file is the safe approach -- it gives a consistent point-in-time snapshot at the cost of a small delay.
