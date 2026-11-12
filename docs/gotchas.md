# Cross-cutting gotchas

Operational traps and historical fixes that apply across the repo. Binding
rules still live in `AGENTS.md`; this page is the reference for why the trap
exists and how to avoid it.

## `make precommit-fix` is NOT a dry run under `make -n`

GNU make executes `$(MAKE)`-bearing recipe lines even under `-n`, and the
`precommit-fix` recipe is one such compound command — a "dry run" used to really
commit and push. The Makefile now refuses `-n`/`-q`/`-t` for this target at
parse time (`tests/test_makefile_dryrun_guard.py` pins it).

To verify recipe changes, extract and `sh`-execute snippets in a test instead
(`tests/test_makefile_push_gate.py` shows the pattern).

## `precommit-fix` with `YOLO=1`/`MSG=` runs `git add -A`

The commit step stages **everything** in the working tree, not just what this
invocation touched. If another process (a concurrent agent session, a background
task without worktree isolation) has unrelated uncommitted changes sitting in
the checkout when it runs, they get swept into that commit under an unrelated
message (observed 2026-07-13, commit `e3800278`).

Check `git status` before running `precommit-fix` with `YOLO=1`/`MSG=`, and
prefer worktree isolation for any spawned session that might invoke it.

## Concurrent agents sharing one worktree

When running parallel subagents (swarms, background agents) in this checkout:

- Stage only files you changed (`git add <specific-files>`, never `git add -A`).
- Never `git stash`, `git reset --hard`, or `git commit --no-verify` — a sibling
  agent's work may be sitting in the same tree.
- Keep concurrent agents on disjoint file sets; if a rebase/conflict lands
  mid-run, resolve only files your task owns.
- Never let a spawned session run `precommit-fix` with `YOLO=1`/`MSG=` against
  the shared checkout — its commit step is `git add -A` (see above).

## Limited / slow network

`precommit-fix` pushes via `tools/git_push_retry.py` (backoff retries +
per-commit chunking; run it directly to drain unpushed commits) and caps its
backgrounded R2/graph uploads at `NET_DEADLINE` seconds (default 1800; raise with
`NET_DEADLINE=3600` to let a slow upload finish). Failures are loud, never
silent, and reruns resume incrementally.

Full map: [`docs/limited-network.md`](limited-network.md).

## Graph scripts are standalone scripts

Any script under `graph/` that imports sibling modules (`from graph.builder
import ...`) must insert the repo root into `sys.path` _before_ those imports.
See [`docs/graph-analysis-guide.md`](graph-analysis-guide.md).

## The user commits reviewed changes themselves

The user's work pattern is: back-and-forth in chat → they review the diff in
VSCode → they commit it themselves and move on. So if your edits vanish from
`git status` between turns, run `git log --oneline -3` first — a fresh user
commit containing them means the work was accepted. Don't re-verify, re-explain,
or dig into "where did my changes go"; check the log once and continue from
HEAD.

## Never discard uncommitted user work without explicit confirmation

`git checkout -- <file>`, `git reset --hard`, and similar destructive resets can
destroy changes the user made in another session or is still reviewing. This is
especially risky in `data/`, where the "never hand-edit generated data" rule
means _agents shouldn't create manual edits there_, not that an agent may freely
revert whatever is uncommitted. If you see uncommitted changes and don't know
their origin, ask before resetting.

## Skill and command regeneration

A running agent session sees skills as of session start. Editing or syncing
`.agents/skills/` mid-session does not change what the running session has
loaded — an invoked skill still uses the pre-edit text (observed: `/retro`
loading a pre-consolidation copy). Start a new session to pick up skill edits.

## A shim `node` first in PATH silently breaks `check-node`

Agent-spawned shells (e.g. Kimi desktop sessions) can have a shim `node`
ahead of the real interpreter on PATH — observed: `process.execPath` pointing
at a desktop-app helper binary reporting as Node v24. Under that shim, jest
30's ESM detection fails even with `NODE_OPTIONS=--experimental-vm-modules`,
so `make check-node` dies on `review_heatmap/tests/` with
`Must use import to load ES Module ... require of ESM` while CI on the same
commit is green (observed 2026-10-15; `npm ci` does not fix it).

Diagnose with `node -p process.execPath` — if it is not a real node binary,
re-run with one, e.g.
`PATH="/opt/homebrew/bin:$PATH" make check-node`. Do not report this as a
code failure, and do not "fix" repo files for it.

## Dead code, hook callbacks, and dependency traps

- **Mandatory reference search:** Search with `git grep -n <target>` across
  **all** tracked files before deleting (including `.md`, `.sh`, `.yml`,
  `Makefile`, `.agents/`, `js/`, `docs/`, and add-on Python source). Never use
  `rg <target>` without explicit paths (`.`): in non-interactive agent
  execution where `stdin` is a pipe, `rg` searches empty `stdin` and silently
  returns zero matches.
- **Anki hook / entry-point hazards:** A function is not dead code just because
  nothing calls it by name in-repo. Hook callbacks registered via
  `gui_hooks.<event>.append(fn)` (or `addHook`/`wrap`), add-on `__init__`
  entry points, CLI `main()` / `argparse` functions, and re-exported public API
  are invoked by Anki, users, or importers at runtime.
- **Import mapping trap:** PyPI distribution names frequently differ from
  top-level module names (e.g. `beautifulsoup4` provides `bs4`, `PyYAML`
  provides `yaml`). Search for both the distribution name and all top-level
  module names before pruning dependencies.
- **Standalone pytest / Anki runtime trap:** Packages bundled by Anki at desktop
  runtime (e.g. `beautifulsoup4`) must remain declared in `requirements.txt` so
  that standalone pytest suites and CI test runners can run outside Anki.
- **Virtualenv ghost-green trap:** Removing a line from `requirements.txt` does
  not uninstall the package from your local `.venv`. A local `make precommit`
  will pass because the package is still present in `site-packages`, but clean CI
  runner builds will fail.
- **Foreign package managers:** Never run `pnpm`, `yarn`, or `bun` — dependency
  work here is strictly `npm` + `package-lock.json`.

## Testing tools/ imports and script entry points

- **Flat tools imports:** Tests for `tools/<tool>.py` must import the module
  flat — `from prior_prs import ...` after `sys.path.insert(0, ...)` at the top
  of the test file — never `from tools.prior_prs import ...`. The package-path
  form makes mypy see the file under two module names (`Source file found twice
under different module names`) and fails `make typecheck`.
- **Testing script `__main__` entry points:** Prefer calling functions
  directly. When testing `__main__` via
  `runpy.run_module(..., run_name="__main__")` with `patch("sys.exit")`, never
  wrap `runpy` in blanket `try: ... except Exception: pass` — exceptions in
  `main()` must fail the test, not be swallowed for coverage theater.

## Security, error-handling, and DOM sinks

- **DOM XSS in `js/`:** Never assign dynamic strings to `innerHTML`,
  `insertAdjacentHTML`, or D3 `.html()`. Build elements with
  `document.createElement`, `textContent`, and `replaceChildren`; clear
  containers with `textContent = ""`.
- **Python → WebView HTML escaping:** When a Python add-on constructs HTML for
  the WebView (`awesome_tts`, `review_heatmap`), escape every interpolated
  variable with `html.escape(value, quote=True)`.
- **SQLite parameterization:** Parameterize SQL values with `?`. Quote table and
  column identifiers with `"` and escape internal quotes (`.replace('"', '""')`).
  Never `%s`-interpolate identifiers.
- **Silent error swallowing:** Never write bare `except:` or empty `catch {}`
  blocks. Bind the exception and log it (`print(..., file=sys.stderr)` or
  `console.warn`), or add an explicit comment explaining why it is safe to
  ignore.
- **Accessible terminal / live output:** Containers receiving appended output
  lines need `role="log"`, `aria-live="polite"`, `aria-atomic="false"`. Custom
  interactive elements (`div`/`span` buttons) must have `role="button"`,
  `tabindex="0"`, `aria-pressed` (if toggling), and Enter/Space `keydown`
  listeners mirroring the `click` logic. Never remove `outline: none` without a
  `:focus-visible` replacement.
