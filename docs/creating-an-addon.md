# Creating a new addon

Anatomy of a self-contained Python addon in this monorepo, plus the test pattern
the existing addons use. Goal: a new addon that passes `make precommit` on the
first try. For the lint/format/type/security gate itself, see
[lint-and-quality.md](lint-and-quality.md).

## Directory layout

```
<addon>/
├── __init__.py        # entry point — runs on Anki startup
├── manifest.json      # required
└── tests/
    └── test_<addon>.py
```

`manifest.json` minimally needs `package` (the folder name) and `name`. Addons
shipped to AnkiWeb also carry `anki_version` and `version`:

```json
{
  "package": "no_leech_suspend",
  "name": "No Leech Suspend",
  "anki_version": "2.1.0",
  "version": "1.0.0"
}
```

## `__init__.py` patterns

The module runs once at startup, so registration happens at module scope.

- **Register a hook** — append a handler to a `gui_hooks` (or `anki.hooks`) list:

  ```python
  from aqt import gui_hooks, mw

  def on_profile_did_open():
      if mw is not None and mw.col is not None:
          ...

  gui_hooks.profile_did_open.append(on_profile_did_open)
  ```

- **Monkeypatch a method** — guard with a sentinel attribute so reloading the
  addon doesn't wrap twice (see `hide_window_title/__init__.py`):

  ```python
  if not hasattr(AnkiQt, "_my_addon_patched"):
      original = AnkiQt.setWindowTitle
      def patched(self, title): original(self, "")
      AnkiQt.setWindowTitle = patched
      AnkiQt._my_addon_patched = True
  ```

- **Write for Anki's bundled Python, not the repo's.** Anki 25.02 ships
  Python 3.9, so syntax the test suite happily runs (e.g. PEP 604 `int | None`
  annotations, evaluated at `def` time) crashes the addon at load with
  `TypeError: unsupported operand type(s) for |`. Add
  `from __future__ import annotations` as the first import in every module —
  the mocked test suite cannot catch this; only launching Anki does.

- **Hard-code Anki constants** (e.g. `LEECH_TAGONLY = 1`,
  `QUEUE_TYPE_SUSPENDED = -1`) rather than `from anki.consts import …`. The test
  harness mocks the `anki` package as a bare `MagicMock` with no real submodules,
  so `from anki.consts import X` raises at import time. A `from anki.hooks import
…` that may be missing should be wrapped in `try/except (ImportError,
AttributeError)`.

## Test pattern

The root `conftest.py` globally mocks `aqt`/`anki`, so a plain `import <addon>`
works. To test the module-level _registration_ and behavior, install your own
mocks into `sys.modules` and `importlib.reload` the addon so its top-level code
re-runs against them. `gui_hooks.<hook>` must be a real list (not a MagicMock) so
`.append` is observable:

```python
import importlib, sys
from unittest.mock import MagicMock

def _load(mw):
    aqt = MagicMock()
    aqt.mw = mw
    aqt.gui_hooks.profile_did_open = []   # real list → assert registration
    sys.modules['aqt'] = aqt
    import no_leech_suspend
    importlib.reload(no_leech_suspend)
    return no_leech_suspend

def test_hook_registered():
    mod = _load(MagicMock(col=MagicMock()))
    assert mod.on_profile_did_open in mod.gui_hooks.profile_did_open
```

Factor the real logic into plain functions that take `col`/`card` so they can be
unit-tested directly without touching `mw`. See
`no_leech_suspend/tests/` and `hide_window_title/tests/` for full examples.

## Verify (from the repo root, with `python3`)

```bash
python3 -m pytest <addon>/tests/ -q     # scoped, fast
make quality-py                         # ruff + black + mypy + bandit (handles flags)
make precommit SKIP=1                   # the full gate CI runs
```

Run from the **root** — `conftest.py` lives there and supplies the `aqt`/`anki`
mocks; `pytest` inside an addon subdir fails to import them. Invoke the quality
tools via `make`, not by hand: e.g. Bandit needs `--ini .bandit` (its `-c`
expects YAML), which the Makefile already passes.

## Test gotchas that pass in your shell but fail under `make`

- **`make` runs the repo-local `.venv/bin/python3`, not your shell's `python3`.**
  The Makefile's `PYTHON` is `$(wildcard .venv/bin/python3)` when present. That venv
  can have a **different package set** than the `python3` on your PATH — e.g. the
  graph pipeline's `fa2_modified` (ForceAtlas2) may be installed in one and not the
  other. A test that passes with a bare `python3 -m pytest` can still fail under
  `make check`. **When a test is green in your shell but red in `make check`, re-run
  it with `.venv/bin/python3 -m pytest …` before debugging anything else.**
- **Never let a test spawn a real process pool.** `ProcessPoolExecutor` /
  `multiprocessing` (default **spawn** on macOS) starts a fresh interpreter that
  **re-imports the target module** — so any module-level `import` that isn't
  installed in the repo `.venv` (e.g. `from fa2_modified import ForceAtlas2`) raises
  `ModuleNotFoundError` in the child, and your `@patch`/`sys.modules` stubs (which
  only exist in the parent) don't cross the process boundary. Patch the executor to
  run in-process: `@patch('concurrent.futures.ProcessPoolExecutor',
concurrent.futures.ThreadPoolExecutor)` keeps real `Future`/`as_completed`
  semantics while the mocks apply. See `graph/tests/test_export_data.py::test_compute_layout`.
- **Every `<addon>/tests/` is auto-gated.** `PY_TEST_SUITES` is discovered from
  `git ls-files '*/test_*.py'`, so a new addon's tests join `make check-py` the moment
  they're committed — nothing to register. `tests/test_makefile_test_gate.py` fails if
  that discovery ever silently drops to empty.
