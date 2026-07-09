# Anki Addons Development Guide

## Coding Standards

### Anki Imports

- **Explicit Imports:** Avoid wildcard imports (`from aqt.qt import *`). Use explicit imports: `from aqt.qt import Qt, QAction, QDialog, ...`.
- **Environment Gotcha:** `anki` and `aqt` modules are provided by the Anki runtime and are not available in the local dev environment.
- **Linter Suppression:** Use `# type: ignore` on imports from `anki` or `aqt` to suppress unresolved import warnings in editors.
- **MainWindow (`mw`) Reference Gotcha:** Do not import and bind `mw` at the module's top level (e.g., `from aqt import mw` at module root). When the module is first imported by Anki, `aqt.mw` is `None`. Doing a top-level import will permanently bind your local reference to `None`. Instead, look up `mw` dynamically inside functions or methods (e.g., `import aqt; mw = aqt.mw` or `from aqt import mw` inside the function).

### Configuration Pattern

- **Dictionary-first:** Always ensure configuration objects (`conf`) are initialized to a dictionary, even if `getUserOption()` returns `None`.
- **Pattern:** `conf = getUserOption() or getDefaultConfig()` or `conf = getUserOption() or {}`.
- **Type Hints:** Use `Dict[str, Any]` for config objects to avoid "None type is not subscriptable" errors.

### Python Version & Dependency Consistency

- **Python Version Consistency:** The CI workflow in `.github/workflows/ci.yml` is pinned to Python `3.13` to match the local development virtual environment and prevent issues with newer/pre-release Python versions (such as Bandit crashing on Python 3.14 due to AST deprecations).
- **External Dependencies:** Any third-party packages (e.g., `beautifulsoup4`) used in addon code or tests that are not part of Python's standard library must be explicitly listed in `requirements.txt`. While Anki bundles packages like `beautifulsoup4` and `requests` at runtime, they are not available during local testing/CI execution outside of Anki unless declared.

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

## Sibling Repositories

This project is part of a cluster of repositories. Note the primary branch names and verification commands.

| Repository        | Path                  | Primary Branch | Verification     |
| ----------------- | --------------------- | -------------- | ---------------- |
| **Anki Addons**   | `.`                   | `main`         | `make precommit` |
| **Fund**          | `../fund`             | `main`         | `make precommit` |
| **Networking**    | `../networking`       | `main`         | `make precommit` |
| **Personal Site** | `../ryusoh.github.io` | **`master`**   | `make check`     |

### Multi-repo Workflow

- **Automation:** Use the `/ship <branch>` command in any repo to fix quality failures, merge to the primary branch, and cleanup.
- **Git Hooks:** All repos use pre-commit hooks (e.g., `prettier`). If a push fails, run the repo's fix command (e.g., `make fmt-py`, `make fmt`, or `make precommit-fix`) before retrying.
