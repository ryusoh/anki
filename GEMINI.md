# Anki Addons Development Guide

## Coding Standards

### Anki Imports

- **Explicit Imports:** Avoid wildcard imports (`from aqt.qt import *`). Use explicit imports: `from aqt.qt import Qt, QAction, QDialog, ...`.
- **Environment Gotcha:** `anki` and `aqt` modules are provided by the Anki runtime and are not available in the local dev environment.
- **Linter Suppression:** Use `# type: ignore` on imports from `anki` or `aqt` to suppress unresolved import warnings in editors.

### Configuration Pattern

- **Dictionary-first:** Always ensure configuration objects (`conf`) are initialized to a dictionary, even if `getUserOption()` returns `None`.
- **Pattern:** `conf = getUserOption() or getDefaultConfig()` or `conf = getUserOption() or {}`.
- **Type Hints:** Use `Dict[str, Any]` for config objects to avoid "None type is not subscriptable" errors.

## Verification Workflow

### Python Quality Gate

Run checks from the repo root.

- **Fast Lint/Type/Format:** `make quality-py`
- **Scoped Typecheck:** `make typecheck-addon ADDON=<addon_dir>`
- **Scoped Test:** `make test-addon ADDON=<addon_dir>`

### Common Commands

- `make check-py`: Run all Python tests with coverage.
- `make fmt-py`: Auto-format Python code (Black + Ruff).
- `make precommit`: Full gate (fmt + lint + quality + tests).
