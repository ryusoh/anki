# R2 Sync Guide

## Problem: Deleted Notes in Anki

When you delete a note from Anki, it's removed from your local database, but **it remains in R2** unless you explicitly sync.

## Solution: `--sync` Flag

The `--sync` flag tells the upload script to:

1. **List** all note files currently in R2
2. **Compare** with your local staged notes
3. **Delete** orphaned notes (exist in R2 but not locally)
4. **Upload** new/changed notes

## Usage

### Via Makefile (Recommended)

```bash
# Full workflow with sync
make precommit-fix
# → Prompts for fetch
# → Prompts for R2 upload (with sync enabled by default)

# Just upload with sync
make fetch-r2
```

### Direct Script

```bash
# Upload with sync
python3 data/anki/upload-to-r2 --upload-only --sync --verbose

# Upload without sync (faster, but orphans accumulate)
python3 data/anki/upload-to-r2 --upload-only --verbose
```

## What Gets Deleted

**Orphaned notes only** - notes that:

- ✅ Exist in R2 `notes/` folder
- ❌ Don't exist in your local staging directory

**Example:**

```text
R2 has:        Local has:       Action:
notes/abc.json.gz  notes/abc.json.gz  → Keep
notes/def.json.gz  (missing)          → DELETE (orphaned)
notes/ghi.json.gz  notes/ghi.json.gz  → Keep
                   notes/jkl.json.gz  → Upload (new)
```

## Performance

| Operation        | Time                          |
| ---------------- | ----------------------------- |
| List R2 objects  | ~1-2 seconds per 1000 objects |
| Delete orphans   | ~0.5 seconds per 1000 objects |
| Upload new notes | ~1-2 seconds per 1000 notes   |

**Example:** 161K notes

- List: ~3-5 minutes
- Delete (if 1K orphans): ~30 seconds
- Upload (if 1K new): ~30 seconds

## Skip Sync (Faster Upload)

If you know you haven't deleted any notes:

```bash
# Skip sync for faster upload
python3 data/anki/upload-to-r2 --upload-only --verbose
```

## Dry Run (Preview Changes)

```bash
# See what would be synced without actually deleting
python3 data/anki/upload-to-r2 --dry-run --verbose
```

## How It Works

```python
# 1. List all objects in R2 notes/ prefix
r2_objects = s3.list_objects_v2(Bucket='anki-content', Prefix='notes/')

# 2. Get local note filenames
local_notes = {'abc123.json.gz', 'def456.json.gz', ...}

# 3. Find orphans
orphans = [obj for obj in r2_objects if obj.name not in local_notes]

# 4. Delete orphans in batches of 1000
s3.delete_objects(Bucket='anki-content', Delete={'Objects': orphans})

# 5. Upload new/changed notes
for note_file in local_notes:
    s3.upload_file(note_file, 'anki-content', f'notes/{note_file}')
```

## Best Practices

1. **Run sync regularly** - Every upload is a good time to sync
2. **Review before deleting** - Use `--dry-run` first if unsure
3. **Backup important data** - R2 deletion is permanent
4. **Monitor R2 bucket** - Check Cloudflare Dashboard occasionally

## Troubleshooting

### "Sync requires boto3"

```bash
pip install boto3
```

### "Too many API calls"

Sync makes additional API calls (list + delete). If you hit rate limits:

- Run during off-peak hours
- Skip sync occasionally (`--no-sync`)
- Contact Cloudflare for higher limits

### Accidental deletion

R2 deletion is **permanent**. To recover:

1. Re-fetch from Anki (if note still exists)
2. Re-upload manually
3. Restore from R2 backup (if enabled)

## Cost Impact

| Operation           | Cost     |
| ------------------- | -------- |
| List objects (161K) | ~$0.0005 |
| Delete (1K orphans) | Free     |
| Upload (1K new)     | ~$0.0005 |

**Sync adds ~$0.001 per upload** - negligible for most users.
