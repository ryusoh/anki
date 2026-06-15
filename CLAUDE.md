# Repository guide

Monorepo of Anki addons (Python) plus a JS/graph data pipeline. Each top-level
directory (`auto_wiktionary/`, `graph/`, `data/anki/`, …) is a self-contained
addon or tool with its own `tests/`.

## Running tests & checks

- **Run from the repo ROOT, always.** The root `conftest.py` mocks `aqt`/`anki`;
  running `pytest` inside an addon subdir fails with `ModuleNotFoundError`.
- **Use `python3`, not `python`** (`python` is not on PATH).
- **Scoped, fast run (tight loop):** `make test-py SUITE=auto_wiktionary/tests`
  (or `python3 -m pytest <addon>/tests/ -q`).
- **Do not run one combined `pytest`** over the whole repo: each addon bootstraps
  its own `sys.path`, so suites only collect in isolation. `make check-py` runs
  them one at a time and accumulates coverage.
- `make check` = `check-node` (JS, c8 coverage) + `check-py` (per-addon, coverage).
  `make precommit` is the full gate; `make lint` / `make fmt-check` for style.

## Gotchas

- A `coverage/` **directory** at the repo root shadows the `coverage` command —
  invoke coverage as `python3 -m coverage`, never bare `coverage`.
- `check-py` needs `pytest-cov` (in `requirements.txt`; `make install` first) and,
  for `graph/tests`, `networkx`.
- TDD-style corner-case tests live next to each addon (e.g.
  `auto_wiktionary/tests/` pins Wiktionary redirect cases). Add a failing test
  there first, then fix.
