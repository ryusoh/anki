# Setup Guide

## Quick Start

```bash
# 1. Install dependencies
make install

# 2. Fetch data from Anki
make fetch

# 3. Analyze knowledge graphs
make graph-analyze
```

## Prerequisites

- Python 3.10+
- pip3
- Anki desktop app
- Cloudflare R2 account (optional, for private backup)

## Installation

### Install Python Dependencies

```bash
make install
```

Or manually:

```bash
pip3 install -r requirements.txt
```

### What Gets Installed

| Package       | Purpose             | Required For         |
| ------------- | ------------------- | -------------------- |
| `networkx`    | Graph algorithms    | Graph analysis       |
| `scipy`       | Numerical computing | PageRank computation |
| `boto3`       | AWS S3 SDK          | R2 uploads           |
| `pytest`      | Testing framework   | Running tests        |
| `pytest-cov`  | Coverage reports    | Test coverage        |
| `pytest-mock` | Mocking utilities   | Testing              |

## Configuration

### R2 Setup (Optional)

For private content backup:

```bash
# Create credentials file
mkdir -p ~/.anki-r2
cat > ~/.anki-r2/credentials << EOF
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET=anki-content
EOF
chmod 600 ~/.anki-r2/credentials
```

See `docs/r2-upload-guide.md` for detailed setup.

## Verify Installation

```bash
# Run tests
make check

# Or specific test suite
python3 -m pytest graph/tests/ -v

# List available decks
python3 graph/analyze.py --list-decks
```

## First Run

```bash
# 1. Fetch from Anki (creates GitHub + R2 data)
make fetch-and-stage-r2

# 2. Analyze all decks
make graph-analyze

# 3. (Optional) Upload to R2
make fetch-r2
```

## Troubleshooting

### "Module not found: networkx"

```bash
make install
# or
pip3 install networkx scipy boto3
```

### "No notes found"

Make sure Anki is closed and data is fetched:

```bash
make fetch
```

### "R2 credentials not found"

Create credentials file (see R2 Setup above) or set environment variables:

```bash
export R2_ACCOUNT_ID=xxx
export R2_ACCESS_KEY_ID=xxx
export R2_SECRET_ACCESS_KEY=xxx
```

### "Permission denied" for scripts

Make scripts executable:

```bash
chmod +x data/anki/fetch
chmod +x data/anki/upload-to-r2
chmod +x graph/analyze.py
```

## Update Dependencies

```bash
pip3 install -r requirements.txt --upgrade
```

## Uninstall

```bash
# Remove installed packages
pip3 uninstall networkx scipy boto3 pytest pytest-cov pytest-mock

# Or use pip with requirements
pip3 uninstall -r requirements.txt
```

## Development

### Run Tests

```bash
# All tests
make check

# Graph tests only
python3 -m pytest graph/tests/ -v

# With coverage
python3 -m pytest graph/tests/ --cov=graph --cov-report=html
```

### Code Style

```bash
# Format code
make fmt

# Check formatting
make fmt-check

# Lint
make lint
```

## Next Steps

After setup:

1. **Read docs:**
   - `docs/graph-analysis-guide.md` - Graph analysis usage
   - `docs/r2-upload-guide.md` - R2 backup setup
   - `docs/anki-knowledge-graph-architecture.md` - Architecture overview

2. **Try commands:**

   ```bash
   make graph-analyze      # Analyze all decks
   make graph-deck DECK='Your Deck'  # Analyze specific deck
   make fetch-r2           # Upload to R2
   ```

3. **Explore graphs:**

   ```bash
   make graph-export       # Export for Gephi visualization
   ```

## Support

- **Issues:** Check `docs/` folder
- **Tests:** `python3 -m pytest graph/tests/ -v`
- **Help:** `python3 graph/analyze.py --help`
