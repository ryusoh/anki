# Repository guide

Monorepo of Anki addons (Python) plus a JS/graph data pipeline. Each top-level
directory (`auto_wiktionary/`, `graph/`, `data/anki/`, …) is a self-contained
addon or tool with its own `tests/`. New addon? See `docs/creating-an-addon.md`
(layout, hook/test patterns). Debugging a field-transform addon against a real
card? Same doc's "Field HTML reality" section — start with
`python3 tools/dump_field.py --contains '<text>'`, don't hand-roll sqlite3.

## Running tests & checks

- **Run from the repo ROOT, always.** The root `conftest.py` mocks `aqt`/`anki`;
  running `pytest` inside an addon subdir fails with `ModuleNotFoundError`.
- **Use `python3`, not `python`** (`python` is not on PATH).
- **Scoped, fast run (tight loop):** `make test-py SUITE=auto_wiktionary/tests`
  (or `python3 -m pytest <addon>/tests/ -q`).
- **Do not run one combined `pytest`** over the whole repo: each addon bootstraps
  its own `sys.path`, so suites only collect in isolation. `make check-py` runs
  them one at a time and accumulates coverage.
- **JS tests: only root `tests/` (node runner, `node:test`) and `review_heatmap/tests/`
  (jest) are executed** — a `*.test.js` anywhere else silently never runs. Browser-side
  scripts are pinned with source-level regression tests. See `docs/js-testing.md`.
- `make check` = `check-node` (JS, c8 coverage) + `check-py` (per-addon, coverage).
  `make precommit` is the full gate (`fmt-check` + `lint` + `quality-py` + `check`);
  CI runs `make precommit SKIP=1` on push/PR (`.github/workflows/ci.yml`).
- **Lint/format/type/security:** `make lint` (ESLint + Stylelint + markdownlint) and
  `make quality-py` (ruff / black / mypy / bandit). Auto-fix with `make lint-fix` and
  `make fmt-py`. Tooling is pinned in `requirements-dev.txt` and covers all addon
  source we maintain; only vendored code (`review_heatmap/libaddon`, `_vendor/` trees)
  and minified bundles are excluded. See `docs/lint-and-quality.md`.

## Gotchas

- A `coverage/` **directory** at the repo root shadows the `coverage` command —
  invoke coverage as `python3 -m coverage`, never bare `coverage`.
- `check-py` needs `pytest-cov` (in `requirements.txt`; `make install` first) and,
  for `graph/tests`, `networkx`.
- **Python dev/lint tools need a venv.** System `python3` is Homebrew and
  externally-managed (PEP 668), so a bare `pip3 install` of ruff/black/mypy/bandit is
  blocked. Install the pinned tools into a venv: `make install-dev` (or
  `pip install -r requirements-dev.txt`). CI installs them fresh, so no venv there.
- TDD-style corner-case tests live next to each addon (e.g.
  `auto_wiktionary/tests/` pins Wiktionary redirect cases). Add a failing test
  there first, then fix.
- **`make` runs the repo-local `.venv/bin/python3`, not your shell's `python3`** —
  they can have different packages (e.g. `fa2_modified`), so a test green under a
  bare `python3 -m pytest` can be red under `make check`; re-run with
  `.venv/bin/python3` before debugging. And never spawn a real `ProcessPoolExecutor`
  in a test (spawn children re-import the module and drop your mocks — patch it to
  `ThreadPoolExecutor`). Both detailed in `docs/creating-an-addon.md`.
