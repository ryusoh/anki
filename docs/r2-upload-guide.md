# R2 Upload Quick Start

## Directory Structure

### Local Staging (data/cloudflare/)

```text
data/cloudflare/          ← Local staging (git-ignored)
├── collection/
│   ├── notes.json.gz
│   ├── cards-data.json.gz
│   ├── notetypes.json.gz
│   ├── decks-config.json.gz
│   ├── media-registry.json
│   └── collection-config.json
└── notes/
    ├── {guid1}.json.gz   ← Staged before upload
    ├── {guid2}.json.gz
    └── ...
```

### Cloudflare R2 Bucket

```text
anki-content/             ← Your R2 bucket
├── collection/
│   ├── notes.json.gz     ← Uploaded from staging
│   ├── cards-data.json.gz
│   ├── notetypes.json.gz
│   ├── decks-config.json.gz
│   ├── media-registry.json
│   └── collection-config.json
└── notes/
    ├── {guid1}.json.gz   ← Uploaded from staging
    ├── {guid2}.json.gz
    └── ...
```

## Setup

### 1. Create R2 Bucket

```text
Cloudflare Dashboard → R2 → Create bucket
Name: anki-content
Region: Choose closest to you
```

### 2. Create API Token

```text
R2 → API Tokens → Create token
Template: Object Read & Write
Scope: Specific bucket → anki-content
```

### 3. Save Credentials

```bash
mkdir -p ~/.anki-r2
cat > ~/.anki-r2/credentials << EOF
R2_ACCOUNT_ID=your-account-id-here
R2_ACCESS_KEY_ID=your-access-key-id-here
R2_SECRET_ACCESS_KEY=your-secret-key-here
R2_BUCKET=anki-content
EOF
chmod 600 ~/.anki-r2/credentials
```

## Usage

### Via Makefile (Recommended)

```bash
# Stage and upload to R2
make fetch-r2

# Or skip R2 upload during precommit-fix
make precommit-fix SKIP_R2=1
```

### Direct Script

### Stage Files (Prepare for Upload)

```bash
cd data/anki
./upload-to-r2 --verbose
```

This will:

1. Fetch private data from Anki
2. Stage files in `data/cloudflare/`
3. Ask for confirmation before uploading

### Skip Upload (Stage Only)

Press Enter when prompted to skip upload. Files remain in `data/cloudflare/` for later upload.

### Upload Only (Files Already Staged)

```bash
./upload-to-r2 --upload-only
```

### Dry Run (Preview)

```bash
./upload-to-r2 --dry-run --verbose
```

### Download Single Note

```bash
./download-from-r2 <guid> --verbose
```

Example:

```bash
./download-from-r2 hNb(y8)oa* --verbose
```

### Download to File

```bash
./download-from-r2 hNb(y8)oa* --output note.json
```

## What Gets Uploaded

| Category     | Size        | Contains                |
| ------------ | ----------- | ----------------------- |
| Notes (flds) | ~108 MB     | Card questions, answers |
| Notes (tags) | <1 MB       | User tags               |
| Cards (data) | <1 MB       | Custom card data        |
| Notetypes    | <1 MB       | Templates, CSS          |
| Decks config | <1 MB       | Deck options            |
| **Total**    | **~110 MB** | **Compressed**          |

## What Stays Local (NOT Uploaded)

| Category    | Size   | Location            |
| ----------- | ------ | ------------------- |
| Media files | 5.2 GB | `collection.media/` |
| Anki DB     | 276 MB | `collection.anki2`  |

## Cost Estimate

| Item              | Monthly Cost      |
| ----------------- | ----------------- |
| Storage (0.11 GB) | $0.0017           |
| Writes (1x/month) | negligible        |
| Reads             | negligible        |
| **Total**         | **~$0.002/month** |

## Security

- ✅ R2 bucket is private by default
- ✅ Already encrypted at rest by Cloudflare
- ✅ API credentials required for access
- ✅ `guid` is public but meaningless without R2 access
- ✅ Card content never on GitHub
- ⚠️ Keep `~/.anki-r2/credentials` secure (chmod 600)

## GitHub vs R2 vs Local

| Platform   | Data Type                             | Access            |
| ---------- | ------------------------------------- | ----------------- |
| **GitHub** | Anonymized metadata (guid, mid, csum) | Public/Private    |
| **R2**     | Full content (flds, tags, templates)  | Private (API key) |
| **Local**  | Media files, original DB              | You only          |

## Workflow

```bash
# 1. Fetch from Anki (anonymized for GitHub)
./fetch

# 2. Commit to GitHub
git add data/anki/notes.json.gz data/anki/cards.json.gz
git commit -m "Update Anki stats"
git push

# 3. Stage and upload to R2 (private)
./upload-to-r2 --verbose
# Type 'yes' when prompted to upload

# 4. Verify in Cloudflare Dashboard
# R2 → anki-content → Browse objects

# 5. Clean up staging (optional)
rm -rf ../cloudflare/
```

## Troubleshooting

### "R2 credentials not found"

Make sure `~/.anki-r2/credentials` exists and has correct permissions:

```bash
cat ~/.anki-r2/credentials
chmod 600 ~/.anki-r2/credentials
```

### Upload failed for some files

Check Cloudflare R2 bucket limits and API token permissions. The staging directory keeps local copies so you can retry.

### Want to re-upload after changes

Delete objects from R2 bucket (via Dashboard or CLI), then run:

```bash
./upload-to-r2 --force --verbose
```
