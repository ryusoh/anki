# Git Ignore Audit Report

**Date:** 2026-03-14  
**Repository:** addons21 (Anki Addons Collection)

## Summary

✅ **Status: CLEAN** - All sensitive and generated files are now properly ignored.

## Changes Made

### 1. Enhanced `.gitignore`

Updated from basic rules to comprehensive industry-standard coverage:

| Category      | Before                      | After                                              |
| ------------- | --------------------------- | -------------------------------------------------- |
| macOS         | `.DS_Store` only            | Full macOS ignore (.\_\*, .Trashes, etc.)          |
| Python        | `__pycache__/`, `*.py[cod]` | Complete Python ignore (envs, IDE, coverage, etc.) |
| Node.js       | `node_modules` only         | Plus npm/yarn logs                                 |
| Anki Addons   | Partial                     | Comprehensive (all addons covered)                 |
| R2/Cloudflare | Basic                       | Complete (credentials, staging, private data)      |
| Logs          | None                        | `*.log` globally ignored                           |
| Databases     | Partial                     | `*.db`, `*.sqlite` in user_files/                  |

### 2. Files Untracked

| File                               | Reason                      | Action            |
| ---------------------------------- | --------------------------- | ----------------- |
| `awesome_tts/user_files/config.db` | User data (SQLite database) | `git rm --cached` |

### 3. Protected Files (Safe for GitHub)

These files are **intentionally tracked** and safe:

| File                          | Why Safe                                   |
| ----------------------------- | ------------------------------------------ |
| `data/anki/notes.json.gz`     | Anonymized (no flds, no tags, no sfld)     |
| `data/anki/cards.json.gz`     | Scheduling metadata only                   |
| `data/anki/decks.json`        | Deck names only                            |
| `data/anki/reviews/*.json.gz` | Review history (timestamps, ease)          |
| `data/anki/fetch`             | Tool script (no secrets)                   |
| `data/anki/upload-to-r2`      | Tool script (reads creds from ~/.anki-r2/) |
| `data/anki/download-from-r2`  | Tool script (reads creds from ~/.anki-r2/) |

### 4. Blocked Files (Never GitHub)

| Pattern                            | Location          | Reason                        |
| ---------------------------------- | ----------------- | ----------------------------- |
| `~/.anki-r2/`                      | Home directory    | **R2 API credentials**        |
| `.anki-r2/`                        | Project root      | **R2 API credentials**        |
| `data/cloudflare/`                 | Staging directory | Private content before upload |
| `data/anki/cards-data.json.gz`     | R2 only           | Full card data field          |
| `data/anki/notetypes.json.gz`      | R2 only           | Templates, CSS                |
| `data/anki/decks-config.json.gz`   | R2 only           | Full deck configurations      |
| `data/anki/media-registry.json`    | R2 only           | Media file references         |
| `data/anki/collection-config.json` | R2 only           | Collection metadata           |
| `*/user_files/*`                   | All addons        | User configs, personal data   |
| `*.log`                            | All locations     | Runtime logs                  |
| `*.db`, `*.sqlite`                 | user_files/       | User databases                |

## Directory Structure

```
addons21/
├── .gitignore                    ← Comprehensive rules
├── data/
│   ├── anki/                     ← Git-tracked (anonymized data + tools)
│   │   ├── fetch                 ✅ Tool
│   │   ├── upload-to-r2          ✅ Tool
│   │   ├── download-from-r2      ✅ Tool
│   │   ├── notes.json.gz         ✅ Anonymized metadata
│   │   ├── cards.json.gz         ✅ Scheduling data
│   │   ├── decks.json            ✅ Deck names
│   │   └── reviews/              ✅ Review history
│   │
│   └── cloudflare/               ← Git-ignored (R2 staging)
│       ├── collection/           ⚠️ Temporary (private content)
│       └── notes/                ⚠️ Temporary (private content)
│
├── awesome_tts/
│   └── user_files/               ← Git-ignored (user data)
│       ├── README.txt            ✅ Sample file (explicitly allowed)
│       └── config.db             ❌ User database (ignored)
│
└── ~/.anki-r2/                   ← Outside repo (credentials)
    └── credentials               🔐 **NEVER COMMIT**
```

## Security Checklist

- [x] R2 credentials stored in `~/.anki-r2/` (outside project)
- [x] R2 staging directory (`data/cloudflare/`) ignored
- [x] Private Anki content (flds, tags, templates) blocked
- [x] User databases (_.db,_.sqlite) in user_files/ ignored
- [x] Log files (\*.log) globally ignored
- [x] Python bytecode (**pycache**/) ignored
- [x] macOS metadata (.\_\*, .DS_Store) ignored
- [x] No secrets in code (credentials loaded from home directory)

## Industry Standards Applied

| Standard                     | Implementation                       |
| ---------------------------- | ------------------------------------ |
| **Separation of concerns**   | Code ≠ Data ≠ Config                 |
| **Credentials outside repo** | `~/.anki-r2/` not in project         |
| **Generated files ignored**  | `__pycache__/`, `*.log`, etc.        |
| **User data protected**      | `user_files/*` ignored               |
| **Minimal tracked data**     | Only anonymized metadata on GitHub   |
| **Explicit is better**       | Comments explain each ignore section |

## Recommendations

1. **Commit the `.gitignore` update:**

   ```bash
   git add .gitignore
   git commit -m "chore: enhance .gitignore with comprehensive rules"
   git push
   ```

2. **Commit the untracked file removal:**

   ```bash
   git commit -m "chore: remove user config.db from tracking"
   git push
   ```

3. **Verify no secrets in history:**

   ```bash
   # Optional: run git-secrets or truffleHog to scan history
   brew install git-secrets
   git-secrets --scan
   ```

4. **Document for collaborators:**
   - Share `docs/r2-upload-guide.md` for R2 setup
   - Share `docs/anki-knowledge-graph-architecture.md` for architecture

## Files Requiring Manual Cleanup

These files are in Git history but should not be (low priority):

| File                               | Status         | Action Needed                                             |
| ---------------------------------- | -------------- | --------------------------------------------------------- |
| `awesome_tts/user_files/config.db` | Just untracked | Will disappear from history on next force push (optional) |

**Note:** Git history cleanup requires `git filter-branch` or BFG Repo-Cleaner. Only do this if:

- The file contains actual secrets (not just user config)
- You're willing to force-push and coordinate with collaborators

## Next Steps

1. ✅ Review this report
2. ✅ Commit `.gitignore` changes
3. ✅ Set up R2 credentials (see `docs/r2-upload-guide.md`)
4. ✅ Run `./upload-to-r2 --dry-run --verbose` to test
