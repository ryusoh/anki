# R2 Upload Quick Start

## Directory Structure

```text
R2 Bucket: anki-content/
├── collection/
│   ├── notes.json.gz           # All notes with full content
│   ├── cards-data.json.gz      # Cards with custom data
│   ├── notetypes.json.gz       # Templates, CSS
│   ├── decks-config.json.gz    # Deck configs
│   ├── media-registry.json     # Media references
│   └── collection-config.json  # Collection metadata
└── notes/
    ├── {guid1}.json.gz         # Individual note by GUID
    ├── {guid2}.json.gz
    └── ... (161,176 files)
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

### Upload All Private Data

```bash
cd data/anki
./upload-to-r2 --verbose
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

| Item              | Monthly Cost |
| ----------------- | ------------ |
| Storage (0.11 GB) | $0.0017      |
| Writes (1x/month) | negligible   |
| Reads             | negligible   |

## Security

- ✅ R2 bucket is private by default
- ✅ API credentials required for access
- ✅ `guid` is public but meaningless without R2 access
- ✅ Card content never on GitHub
- ⚠️ Keep `~/.anki-r2/credentials` secure (chmod 600)

## GitHub vs R2

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

# 3. Upload full content to R2 (private)
./upload-to-r2 --verbose

# 4. Build knowledge graph locally (merge both)
# (Future: ./build-graph)
```
