# Security Protocol - Private Data Protection

## Overview

This document describes the **EXTREMELY RIGOROUS** security measures in place to protect private Anki card content from being accidentally committed to GitHub.

## What Is Private

The following data must **NEVER** be committed to GitHub:

| Data Type    | Field Name              | Why Private                             |
| ------------ | ----------------------- | --------------------------------------- |
| Card Content | `flds`                  | Actual questions and answers            |
| User Tags    | `tags`                  | Personal organization system            |
| Full Notes   | `flds` + `mid` + `guid` | Complete note structure                 |
| R2 Staging   | `data/cloudflare/`      | Contains all private data before upload |

## Multi-Layer Security

### Layer 1: .gitignore

```
# Root .gitignore
data/cloudflare/          # R2 staging directory
graph/*.json              # Graph data files
graph/graph_data.json     # Specific graph data file

# graph/.gitignore
*.json                    # Block ALL JSON files in graph folder
!package.json             # Except package.json
```

### Layer 2: Automated Security Check

**File:** `data/anki/security_check.py`

**What it does:**

1. Scans ALL git-tracked files
2. Parses JSON files for private data structures
3. Detects `flds` + `mid`/`guid` combinations
4. Verifies R2 staging is gitignored
5. Verifies graph JSON files are gitignored

**When it runs:**

- Automatically in `make precommit-fix`
- Can run standalone: `make security`

**What happens on failure:**

```
======================================================================
🚨 SECURITY CHECK FAILED - PRIVATE DATA DETECTED 🚨
======================================================================

Violation #1:
  File: graph/graph_data.json
  Issue: File contains private note data with flds field
  Fields found: flds, mid, guid

======================================================================
DO NOT COMMIT! Remove private data immediately!
======================================================================
```

### Layer 3: Git Itself

Git will reject files matching `.gitignore` patterns:

```
The following paths are ignored by one of your .gitignore files:
graph/test.json
hint: Use -f if you really want to add them.
```

## How to Use

### Before Every Commit

```bash
# Run full pre-commit flow (includes security check)
make precommit-fix

# Or run security check alone
make security
```

### If Security Check Fails

1. **DO NOT COMMIT**
2. Identify the file flagged
3. Either:
   - Add to `.gitignore` if it's private data
   - Remove private fields from the file
   - Move to `data/cloudflare/` (R2 staging)

### Adding New Data Files

If you need to add new data files:

1. **Ask: Does this contain `flds` or full note content?**
   - YES → Must go in R2, add to `.gitignore`
   - NO → Can be in git, but run security check

2. **Add to appropriate .gitignore:**

   ```bash
   # For R2 staging files
   echo "data/cloudflare/myfile.json" >> .gitignore

   # For graph data
   echo "graph/mydata.json" >> .gitignore
   ```

3. **Run security check to verify:**

   ```bash
   make security
   ```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub (Public)                         │
│  ✅ Anonymized metadata (no flds, no tags)                  │
│  ✅ Graph structure (nodes, edges - no content)             │
│  ✅ Code, configs, documentation                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Cloudflare R2 (Private)                    │
│  🔒 Full card content (flds, tags)                          │
│  🔒 Complete note structures                                │
│  🔒 R2 staging files                                        │
│  🔒 Access: API credentials only                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Security Check (Pre-Commit)                    │
│  🔍 Scans ALL tracked files                                 │
│  🔍 Detects private data patterns                           │
│  🔍 Verifies .gitignore coverage                            │
│  🔍 BLOCKS commit if private data found                     │
└─────────────────────────────────────────────────────────────┘
```

## Testing the Security Check

To verify the security check works:

```bash
# Create a test file with private data
echo '[{"flds": "test", "mid": 123, "guid": "abc"}]' > graph/test.json

# Try to add it (git will block it)
git add graph/test.json
# Error: The following paths are ignored by one of your .gitignore files

# Run security check
make security
# Should pass (file not tracked)

# Clean up
rm graph/test.json
```

## Incident Response

If private data IS accidentally committed:

1. **DO NOT PUSH** - if already pushed, see step 2
2. **Remove from git history:**

   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch path/to/file' \
     --prune-empty --tag-name-filter cat -- --all
   git push --force origin main
   ```

3. **Contact GitHub support** to purge CDN cache
4. **Rotate any exposed credentials**
5. **Review and strengthen security checks**

## Checklist for Safe Commits

Before running `make precommit-fix`:

- [ ] No `graph/*.json` files with card content
- [ ] No `data/cloudflare/` files staged
- [ ] No JSON files with `flds` field
- [ ] All private data in R2 staging directory
- [ ] `.gitignore` up to date

## Contact

If unsure whether something is safe to commit:

1. Run `make security`
2. If it passes, review what files would be committed: `git status`
3. If still unsure, ask for review before committing

---

**This security protocol is CRITICAL. Never bypass it.**
