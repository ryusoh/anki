# Incremental Staging with Hash Map

## Overview

Instead of re-staging all 161K+ notes every time, the system now uses **content-based hashing** to only stage notes that actually changed.

## How It Works

### First Run

```
📦 Fetching Anki data...
   Staging 161,176 individual notes...
   [████████████████████████████████████] 161,176/161,176 (100.0%)
   ✅ Staged 161,176 notes
   💾 Hash map saved to: data/cloudflare/hash_map.json
```

### Subsequent Runs (Only Changed Notes)

```
📦 Fetching Anki data...
   📊 Incremental staging:
      Total notes: 161,176
      Changed/new: 23 (0.01%)
      Unchanged: 161,153 (99.99%)

   Staging 23 changed/new individual notes...
   [████████████████████████████████████] 23/23 (100.0%)
   ✅ Staged 23 changed/new notes
```

## Hash Map

### What Is It?

```json
{
  "hNb(y8)oa*": "a3f5d8c2e1b4f9a7...",
  "q;J;<U%WtQ": "b7e2c9f1a3d6e8b5...",
  ...
}
```

- **Key**: Note GUID (public, already on GitHub)
- **Value**: SHA256 hash of content (flds + tags + mid)

### Is It Safe for GitHub?

**YES!** The hash map is **completely safe** to commit:

| Component     | Safe?  | Why                               |
| ------------- | ------ | --------------------------------- |
| GUIDs         | ✅ Yes | Already public on GitHub          |
| SHA256 hashes | ✅ Yes | One-way function, reveals nothing |
| Content       | ❌ No  | Never in hash map (only hashed)   |

**You CANNOT reverse a hash to get the original content.**

### It Is Tracked and Auto-Committed

`data/cloudflare/hash_map.json` **is committed** — `make precommit-fix`
commits it after a successful R2 sync (`chore: update R2 hash map after
sync`). Losing it is not harmless: `upload-to-r2` would treat every note as
unseen and re-upload all 161K+ files, so git history doubles as its backup —
restore a known-good version with `git checkout` if it's ever damaged.

Two invariants keep the map trustworthy:

- **Only successful uploads are recorded.** A failed or interrupted run
  leaves its files out of the map, so the next run retries exactly those
  (pinned by `data/anki/tests/test_failed_upload_hash_map.py`).
- **`make verify-r2`** audits the map against the live bucket (read-only)
  and lists any entry the bucket cannot back.

## Collection Files Share the Same Map

Collection files (`collection/notes.json.gz`, `collection/reviews/YYYY-MM.json.gz`,
etc.) live in the same `hash_map.json`, keyed by their R2 path. The contract:

- **Both sides hash the canonical JSON content** —
  `sha256(json.dumps(content, sort_keys=True, ensure_ascii=False))` — computed
  by `fetch` when staging and by `upload-to-r2` (`_canonical_collection_hash`)
  when deciding what to upload.
- **Never hash the gzip bytes.** gzip embeds the compression mtime, so every
  rewrite produces different bytes for identical content. When the uploader
  hashed bytes while the stager hashed JSON, the two never matched and every
  daily sync re-staged and re-uploaded all ~80 historical monthly review
  files (fixed 2026-08; pinned end-to-end by
  `data/anki/tests/test_upload_only_content_hash.py`).

A healthy daily run stages/uploads only the current month's review file.

## Benefits

### Speed

| Scenario                 | Before | After  | Speedup  |
| ------------------------ | ------ | ------ | -------- |
| First run                | 5 min  | 5 min  | 1x       |
| Minor changes (10 notes) | 5 min  | 10 sec | **30x**  |
| No changes               | 5 min  | 2 sec  | **150x** |

### Storage

| Scenario         | Before | After  | Savings   |
| ---------------- | ------ | ------ | --------- |
| Full staging     | 260 MB | 260 MB | -         |
| 10 changed notes | 260 MB | ~1 MB  | **99.6%** |

### R2 Upload

- **Fewer files to upload** = faster sync
- **Only changed notes** uploaded to R2
- **Unchanged notes** skipped automatically

## Usage

### Automatic (No Extra Commands)

```bash
# Just run as normal
make precommit-fix

# First run: stages all notes
# Subsequent runs: only changed notes
```

### Force Full Staging

If you want to re-stage everything:

```bash
# Delete hash map
rm data/cloudflare/hash_map.json

# Next run will stage all notes
make fetch-and-stage-r2
```

## Technical Details

### Hash Computation

```python
def compute_note_hash(note):
    content = {
        'flds': note.get('flds', ''),      # Card content
        'tags': note.get('tags', ''),       # User tags
        'mid': note.get('mid', 0),          # Note type
    }
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content_str.encode()).hexdigest()
```

**What's included:**

- ✅ `flds` - Card fields (Q&A content)
- ✅ `tags` - User tags
- ✅ `mid` - Note type ID

**What's NOT included:**

- ❌ `guid` - Would make hash different for same content
- ❌ `mod` - Timestamp changes on every edit
- ❌ `usn` - Sync metadata
- ❌ `csum` - Field checksum (redundant)

### Change Detection

```python
# Load old hash map
old_map = load_hash_map('data/cloudflare/hash_map.json')

# Compare with current notes
changed, unchanged = find_changed_notes(notes, old_map)

# Only stage changed notes
for note in changed:
    stage_note(note)

# Update hash map
new_map = update_hash_map(old_map, notes)
save_hash_map(new_map, 'data/cloudflare/hash_map.json')
```

## Testing

```bash
# Run hash map tests
python3 -m pytest graph/tests/test_hash_map.py -v

# 14 tests covering:
# - Hash computation
# - Hash map loading/saving
# - Change detection
# - Hash map updates
```

## Troubleshooting

### "Staging all notes every time"

Check if `data/cloudflare/hash_map.json` exists:

```bash
ls -la data/cloudflare/hash_map.json
```

If missing, it will always stage all notes. This is normal for first run.

### "Hash map corrupted"

Restore the last committed version (the file is tracked), or delete it to
force a full re-stage and re-upload of everything:

```bash
git checkout -- data/cloudflare/hash_map.json   # preferred: restore
# or: rm data/cloudflare/hash_map.json && make fetch-and-stage-r2  # full restage
```

### "Did the map drift from what's actually on R2?"

```bash
make verify-r2   # read-only audit; exit 2 lists unbacked entries + fix advice
```

## Future Enhancements

- [ ] Compress hash map (gzip) for faster loading
- [ ] Parallel hash computation for speed
- [ ] Show diff of what changed (which fields)
- [ ] Option to review changes before staging
