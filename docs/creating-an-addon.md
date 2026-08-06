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

If the addon adds an editor or toolbar button, give it a distinct `icon.png`.
Don't reuse another addon's icon as a placeholder — users can't tell the buttons
apart in Anki's UI. This applies within a single addon too: two buttons sharing
one icon are indistinguishable in the toolbar, and the user WILL press the wrong
one (happened in `strip_html_tags`: a furigana button cloned the strip icon, the
user hit the strip-HTML button, and the "wrong" output came back as a bug
report). Unit tests can't see which button was pressed — button ambiguity is a
human-facing failure no mock catches. A good default is the service's own
favicon/logo, resized to 48×48. And before adding a second button at all, ask
whether the new action is a variant of an existing one — folding it into the
same button's pipeline (e.g. stripping furigana readings as part of stripping
HTML) beats a near-duplicate button.

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
  the mocked test suite cannot catch this; only launching Anki does. Ruff's
  `FA102` rule (enabled in `pyproject.toml`) blocks the annotation case in CI.

- **Hard-code Anki constants** (e.g. `LEECH_TAGONLY = 1`,
  `QUEUE_TYPE_SUSPENDED = -1`) rather than `from anki.consts import …`. The test
  harness mocks the `anki` package as a bare `MagicMock` with no real submodules,
  so `from anki.consts import X` raises at import time. A `from anki.hooks import
…` that may be missing should be wrapped in `try/except (ImportError,
AttributeError)`.

## Field HTML reality (for addons that transform field content)

Never develop a field transform against an imagined HTML format — every wrong
guess mangles real cards. Dump the **actual stored bytes** first:

```bash
python3 tools/dump_field.py 'front text'          # exact front-field match
python3 tools/dump_field.py --contains 'passage'  # any field contains
```

(It copies the collection to a temp file, so it's safe while Anki runs. It also
auto-picks the most-recently-modified profile, so you don't need to hunt for the
collection path — pass `--collection` only to override that.)

If a search substring matches many unrelated notes, search on the exact card
title/phrase the user gave you first (with `--contains`) rather than a broad
keyword — it's usually a one-shot unique match, cheaper than iterating broader
and narrower queries.

**Fresh, unsaved edits won't show up.** The collection file only reflects
fields Anki has flushed to disk (on field blur or card switch), not mid-edit
keystrokes — a note can be many months stale even though the user "just pasted"
into it moments ago. If the dump looks stale or the reported content is
missing, ask the user to click into another field or switch cards and back
(triggers the autosave) and re-run the dump; if they'd rather not interrupt
their edit, ask them to paste the raw field HTML directly instead.

**Before declaring a transform done, sweep it across the whole collection:**

```bash
python3 tools/sweep_transform.py auto_mathjax:_convert_dollar_to_mathjax
python3 tools/sweep_transform.py <module>:<function> --contains 'Quick' --limit 10
```

It mocks `aqt`, imports the addon's transform function, runs it over **every**
note field (on a temp copy of the collection), prints a diff per field that
would change, and re-applies the transform to each result to flag idempotency
bugs. The card the user reported is never the only shape in the collection:
auto_mathjax's bare-LaTeX feature was built against one reported card, a second
differently-shaped card came back as a bug report, and the first full sweep
then surfaced 184 further notes the heuristic would have mangled (stock
cashtags like `$INTC … $SOI` pairing into math, `$$` money slang matching the
block branch). Review every diff line before shipping; heuristics earn trust
by their blast radius, not by the one card they were written for.

What real fields look like (each of these was found in production cards, and
`reflow_paragraphs/` pins them all as regression tests):

- **Only `<br>` is a line break.** Multi-line paste is stored either as
  `line<br>line` (often with inline tags per line: `<i>line</i><br>`) or as
  one attribute-less **leaf `<div>` per line** — never assume just one format.
- **Literal `\n` characters inside field HTML are whitespace, not breaks.**
  Anki stores `line<br>\n`; treating the `\n` as a second break manufactures
  phantom blank lines.
- **`<div>` is structure, not a line separator.** Web-clipped dictionary
  content nests `<ul><li><dl><dd><div>` many levels deep; converting div
  boundaries to breaks explodes the field. Distinguish _leaf_ divs (no nested
  block tags) from structural ones.
- **Fields mix content types**: styled spans, `<ol>` lists, `<img>`,
  `[sound:…]` refs, and prose can all share one field. A transform must
  return an untouched field **byte-identical** — never normalize what it
  didn't change.
- The **editor** can hand the addon different bytes than the database stores;
  when diagnosing, capture `editor.note.fields[i]` at click time (and keep
  such capture files away from paths the test suite writes to).
- Test fixtures: pin **structure-faithful synthetic fields**, not raw card
  dumps — card content stays out of the public repo.
- **Anki's browser search matches the RAW field HTML, not visible text.** An
  unqualified term compiles to a SQL `LIKE '%term%'` over `n.flds` verbatim —
  tags, attributes, and entities included (`rslib/src/search/sqlwriter.rs`,
  `write_unqualified`; verified in 25.02.5). So searching `BSP` matches every
  note containing `&nbsp;`, and `div` matches every `<div>`. Only exact
  `field:value` comparisons strip HTML (via
  `strip_html_preserving_media_filenames`, which keeps `<img src="...">`
  filenames searchable). An addon cannot change what core search returns, but
  it can prune false positives afterwards: `browser_did_search` fires after
  `context.ids` is populated and before the table consumes it, so reassigning
  `context.ids` filters the result rows. `highlight_search_matches/`
  implements this (see `note_has_real_match` in its `core.py` and the
  conservative skip rules in its `anki_integration.py`).
- **`[sound:]` resolves only inside `collection.media`.** A tag built from an
  add-on cache path renders but plays nothing (found 2026-07-31: AwesomeTTS
  single-click flow generated valid mp3s that were mute). Copy the file with
  `editor._addMedia(path)` and build the tag from its return value — it
  dedups/renames.
- **Appending a line to a field: use a `<div>` block, never `<br>`.** After
  content ending in a block close tag (`</div>`), a `<br>` renders as a
  _blank_ line; adjacent blocks never do. Collapse trailing `<br>`/whitespace
  runs first (the editor leaves them when Enter was pressed).
- **Extracting text from field HTML: never a bare tag-regex.** Entities
  survive it (`&nbsp;` got read aloud by TTS as "and and nbsp") and adjacent
  tags merge words (`<b>a</b><b>b</b>` → `ab`). Replace tags with spaces,
  `html.unescape`, collapse all whitespace — or reuse the add-on's own
  sanitizer if it has one (AwesomeTTS's `addon.strip.from_note`).

## Runtime third-party dependencies (frozen Anki Python)

Anki's bundled Python is PyInstaller-frozen — **no pip, no way to install
into it**. Worse, the version is not guessable: the same Anki release ships
builds with different Pythons (found 2026-07-31: the user's 25.02.5 "ao"
build runs **3.9.18**, not the 3.13 the release notes implied). Never derive
the target version from release notes — read it at runtime
(`sys.version_info`) or ask for the user's Help → About line.

The working pattern (implemented in `awesome_tts/awesometts/deps.py`):

1. Install from an _external_ python3 into a deps dir inside Anki's data
   folder (a sibling of `addons21`, e.g. `<Anki2>/awesome_tts_deps/` — never
   inside this repo, which is symlinked as `addons21`):
   `python3 -m pip install --target <deps> --only-binary=:all:
--python-version <Anki's X.Y> --platform macosx_11_0_arm64
--platform macosx_10_13_universal2 <spec>`
2. At add-on load, `sys.path.append` (not insert — Anki's bundled packages
   keep precedence) the deps dir; auto-install in a daemon thread when
   missing, and treat **any** import exception (not just `ImportError`) as
   "not installed" — a wrong-version deps dir fails with `TypeError` and must
   never crash add-on loading.
3. **pip cross-install gotcha:** `--python-version` changes wheel and
   `Requires-Python` checks but NOT dependency marker evaluation — the
   installing interpreter's markers win, so conditional deps are silently
   dropped (aiohttp's `async-timeout` on Python < 3.11 was). Request them
   explicitly in the spec list.
4. Verify against a **real** interpreter of Anki's version
   (`uv python install 3.9` takes seconds) — "imports fine in the repo venv"
   proves nothing about Anki's runtime, and a wrong-version install crashing
   the add-on is exactly the failure this pattern exists to prevent.

## Verifying aqt/anki APIs (source is not on disk)

The installed Anki is PyOxidizer-compiled — there is **no `aqt`/`anki` Python
source anywhere under `/Applications/Anki.app`**, and no venv in this repo has
them installed. Don't burn time searching the bundle; go straight to the
pinned source on GitHub:

```bash
defaults read /Applications/Anki.app/Contents/Info.plist CFBundleShortVersionString  # e.g. 25.02.5
curl -sL https://raw.githubusercontent.com/ankitects/anki/<version>/qt/aqt/browser/table/__init__.py
```

Useful landmarks: hook signatures live in `qt/aqt/gui_hooks.py` (generated),
browser `SearchContext` in `qt/aqt/browser/table/__init__.py`, search SQL
compilation in `rslib/src/search/sqlwriter.rs`. Verify a hook's dataclass
fields against the user's installed version before building on them — the
repo's `conftest.py` mocks `aqt`, so tests will happily pass against an API
that doesn't exist.

## Offline SQLite database queries

If a script or test queries Anki's `.anki2` SQLite database directly (without importing Anki's Python libraries), it will likely crash with `no such collation sequence: unicase`. Anki registers a custom `unicase` collation function at the database level. To execute queries safely offline, copy the DB and register a dummy collation function:

```python
import sqlite3
import shutil

# Always query a copy to prevent locking Anki's live DB
shutil.copy2(db_path, temp_db_path)
conn = sqlite3.connect(temp_db_path)

# Register a dummy collation to bypass the error
conn.create_collation("unicase", lambda x, y: (x > y) - (x < y))
```

## Test pattern

The root `conftest.py` globally mocks `aqt`/`anki`, so a plain `import <addon>`
works **under pytest only**. In a bare `python3 -c` or standalone script there
are no mocks, and `import <addon>` executes `__init__.py`, which imports `aqt`
at module top and dies with `ModuleNotFoundError: No module named 'aqt'`. To
replay a captured payload (a saved Wiktionary/API response) through a parser
function, write a quick throwaway pytest that reads the fixture from disk —
the conftest mocks make the import work — or copy the mock-then-import pattern
from `tools/sweep_transform.py`. Don't hand-roll `importlib` shims. To test the module-level _registration_ and behavior, install your own
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

## Making HTTP requests from an addon

Don't hand-roll network calls — vendor the shared proxy-fallback helper so the
addon keeps working when the user's uplink only reaches the internet through a
local proxy client (Clash Verge, Astrill OpenWeb, …):

1. Copy `shared/proxy_fallback.py` verbatim to `<addon>/proxy_fallback.py`.
2. In your module: `from .proxy_fallback import urlopen_with_proxy_fallback`,
   then use it anywhere you would call `urllib.request.urlopen`.
3. Import it in tests via the package (`from <addon> import proxy_fallback`),
   not `sys.path` hacks — the relative import in step 2 only resolves in
   package context, which the root `conftest.py` mocks make possible.

The vendored copy must stay byte-identical to the canonical file —
`tests/test_proxy_fallback_sync.py` enforces it, so improvements to the helper
are re-copied to every addon. Background and port list:
`docs/limited-network.md`, failure mode 3.

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
- **Every `<addon>/tests/` is auto-gated for pytest, BUT `quality-py` requires `PY_SRC`.**
  `PY_TEST_SUITES` is discovered from `git ls-files '*/test_*.py'`, so a new addon's tests join `make check-py` the moment they're committed. However, `make quality-py` (Ruff, Mypy, Bandit, Xenon) and `importlinter` require registering the addon:
  1. Append `<addon>` to `PY_SRC` in `Makefile`.
  2. Append `<addon>` to `root_packages` and `modules` under `[tool.importlinter]` in `pyproject.toml`.
  3. If the addon requires per-file ignores for legacy imports, add an entry under `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`.
