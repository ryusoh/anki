# AGENTS.md

Single source of truth for agent guidance on this repo — **edit this file, not
`CLAUDE.md`** (that is a stub that imports this one). Deeper how-tos live in
`docs/`; slash-command workflows live in `.agents/skills/` (canonical — the
open Agent Skills format; `.claude/commands/` is generated from it by
`tools/sync_commands.py`, and the gate drift-checks it via `make sync-check`).

Two audiences:

- **Unattended Jules routines** (`.jules/` personas): you run unattended and open
  PRs. A human only does a binary approve/close on the result — they will **not**
  leave review comments or iterate with you. So every PR must be self-evidently
  correct and approvable at a glance. Optimize for **approve rate**, not for
  volume. The sections from "Non-negotiables" through "Lanes" are binding on you.
- **Interactive agents** (Claude Code, Kimi, Antigravity, …): the repo guide
  (commands, gotchas, coding standards) applies to you. The PR/lane contract
  applies when you open PRs unattended; per-rule carve-outs are marked inline.
  When options are close, pick the best one and proceed — the human wants a
  recommendation, not a menu of questions.

This repo is a **monorepo of Anki add-ons (Python)** plus a JS/graph data pipeline.
Each top-level directory (`auto_wiktionary/`, `awesome_tts/`, `graph/`, `js/`,
`data/anki/`, …) is a self-contained add-on or tool with its own `tests/`. Add-ons
render into Anki's Qt **WebView**; there is no frontend build step (ES modules via
import map). New add-on? See `docs/creating-an-addon.md` (layout, hook/test
patterns). Debugging a field-transform add-on against a real card? Same doc's
"Field HTML reality" section — start with
`python3 tools/dump_field.py --contains '<text>'`, don't hand-roll sqlite3.
Writing a design spec for another agent to implement? See
`docs/delegation-specs.md` first (parity sign-off, anchor citations, doc gotchas).

## Non-negotiables (a PR that violates any of these will be closed)

1. **Open a PR only if `make precommit SKIP=1` is green.** It is the CI gate
   (`fmt-check` + `lint` + `typecheck-js` + `quality-py` + `check`). Red = don't
   open it.
2. **One concern, smallest possible diff.** No drive-by edits, no scope creep.
   Diff size is inversely proportional to approval — keep it tiny.
3. **Stay in your lane** (see "Lanes" below). If two routines touch the same files,
   one PR gets closed. Don't fix something another lane owns.
4. **Never hand-edit generated `data/`** — it is produced by the pipeline.
5. **Never touch vendored code** — `review_heatmap/libaddon/`, any `_vendor/` tree,
   and minified bundles are third-party. Their TODOs and defects are not ours.
6. **Don't commit to `main`.** Branch off `main`, open a PR. (Note: This applies to unattended Jules agents; Antigravity can commit directly to `main`).
7. **Don't leave scratch files in the tree** — no `fix_*.cjs`, scratchpads, or
   debug scripts. The diff contains only the change and its tests.
8. **Don't write a command/example you haven't actually run this session.** Verify
   behaviour; don't infer it from a name or a `case` label.
9. **Check open and recently-closed PRs before you start, and don't repeat them**
   (`gh pr list --state all --limit 30`). A closed PR was closed for a reason; an
   open one already claims that work. Pick something new.

## You cannot see the rendered page

Add-ons render into Anki's WebView; unit tests **cannot** observe a color, a
transparent edge, a glass refraction, spacing, or layout. Therefore:

- **Never claim visual parity, "matches/exceeds," or that something "looks good."**
  You have no eyes. Aesthetic quality is the human's call, not yours.
- For any change whose payoff is visual (glass effects, CSS injected into a stats
  or congrats page, chart styling), either (a) restrict yourself to **objectively
  verifiable** facts (an `aria-label` is present, a DOM attribute, a passing test),
  or (b) open the PR as **draft** and state plainly "visual review required by a
  human."

## The PR body must carry its own proof

Make the approve decision take ten seconds. Every PR description must include:

- **What & why** — one or two sentences.
- **Lane** — which routine/lane this is.
- **Verification** — the exact command(s) you ran and their result, pasted:
  `make precommit SKIP=1` → green, or the scoped proof for your lane (e.g. coverage
  on file X went 82% → 100%; `radon cc` on function Y went C → A).
- **Visual?** — "no visual surface" or "visual — human review required (draft)."

A PR with no pasted verification output reads as unverified and will be closed.

## Changed behaviour must be covered by a test

If your change adds or alters runtime behaviour (a bug fix, a security fix, a
behavioural change), **ship a test that fails before your change and passes after**,
covering the changed lines. Behaviour-preserving changes (complexity refactors,
dead-code removal) need no new test — keep the existing suite green. **Never reach a
coverage number by suppressing it** (`/* c8 ignore */`, `# pragma: no cover`, or
deleting assertions); earn it with a real test or leave the line uncovered and say
why.

## Commit and PR-title conventions

Commits follow **Conventional Commits**, matching this repo's history. The
squash-merge uses the PR title as the commit subject, so the **PR title must also be
a valid Conventional Commit subject**.

- Format: `type(scope): summary`
  - **type** ∈ `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`,
    `build`, `ci`, `style`.
  - **scope** — optional, lower-case, the affected add-on/area (`auto_wiktionary`,
    `awesome_tts`, `review_heatmap`, `graph`, `a11y`, `security`, `deps`, …).
  - **summary** — imperative mood, lower-case, no trailing period, ≤ 72 chars.
- **No emoji, and no routine-name prefix in the subject** (no `Sentinel:`,
  `Bolt:`, no `🛡️`). Attribution rides on the
  `Co-authored-by: google-labs-jules[bot]` trailer — keep the subject clean.
- **Body** (when the change isn't self-evident): wrap ~72 cols, explain _what and
  why_, not how. Severity, metrics, and measurements live here, not in the subject.

## Command interface — prefer `make` (matches CI)

| Need                                                      | Command                            |
| --------------------------------------------------------- | ---------------------------------- |
| Full CI gate (fmt + lint + quality + tests)               | `make precommit SKIP=1`            |
| All tests (JS c8 + per-addon pytest, coverage)            | `make check`                       |
| Python lint/format/type/security (ruff/black/mypy/bandit) | `make quality-py`                  |
| Auto-fix Python format                                    | `make fmt-py`                      |
| Lint (JS + CSS + Markdown)                                | `make lint`                        |
| Auto-fix lint findings                                    | `make lint-fix`                    |
| Format JS/CSS/**MD**/JSON/HTML (Prettier)                 | `make fmt`                         |
| Scoped, fast Python test (tight loop, no coverage)        | `make test-py SUITE=<addon>/tests` |
| Scoped test for one add-on (`test-py SUITE=<dir>/tests`)  | `make test-addon ADDON=<dir>`      |
| Scoped mypy for one add-on                                | `make typecheck-addon ADDON=<dir>` |
| JS test suite (c8 coverage)                               | `make check-node`                  |
| JS strict type check (whitelist)                          | `make typecheck-js`                |

- **Run everything from the repo ROOT.** The root `conftest.py` mocks `aqt`/`anki`;
  running `pytest` inside an add-on subdir fails to import them. Use **`python3`**,
  never `python` (not on PATH).
- **Don't run one combined `pytest`** over the whole repo — each add-on bootstraps
  its own `sys.path`, so suites only collect in isolation. `make check-py` runs them
  one at a time and accumulates coverage.
- A `coverage/` **directory** at the repo root shadows the `coverage` command —
  invoke it as `python3 -m coverage`, never bare `coverage`.
- **Verify with the same python `make` uses.** `make` runs the repo-local
  `.venv/bin/python3`, which may have a different package set than your shell's
  `python3`. A test green under a bare `python3 -m pytest` can be red under
  `make check` — so a "verified" claim only counts if `make precommit SKIP=1`
  passed, not a hand-run pytest. (Also: never spawn a real `ProcessPoolExecutor`
  in a test — spawn children re-import the module and drop your mocks; patch it to
  `ThreadPoolExecutor`. See `docs/creating-an-addon.md`.)
- **Run `make fmt` after hand-authoring any `docs/*.md`** — Prettier owns Markdown
  table/list formatting and `fmt-check` fails otherwise.
- **JS tests: only root `tests/` (node runner, `node:test`) and
  `review_heatmap/tests/` (jest) are executed** — a `*.test.js` anywhere else
  silently never runs. Browser-side scripts are pinned with source-level regression
  tests. See `docs/js-testing.md`.

## Environment setup (run once in the VM before working)

```sh
make install        # runtime + pytest-cov + node deps
make install-dev    # pinned ruff/black/mypy/bandit into a venv (PEP-668 system py3)
```

If dev tools aren't installed, `make quality-py` can't run and your "verified" claim
is false. Confirm both pytest **and** the JS runner execute.

## Layout

- `js/` — frontend ES modules: `js/commands/` (terminal commands), `js/graph/`,
  `js/transactions/`, `js/ui/`, `js/utils/`, `js/config.js`. No build step.
  `js/types/*.d.ts` — type-only ambient declarations for `tsc --checkJs`
  (never shipped).
- `jsconfig.json` — the `tsc --checkJs` strict-mode whitelist; see
  `docs/js-typing-strategy.md` before touching it.
- `<addon>/` — each Anki add-on (Python) with its own `__init__.py`, hooks, and
  `tests/`. New add-on? See `docs/creating-an-addon.md`.
- `graph/` — Python graph pipeline (networkx). `data/anki/` — stats generators.
- `tests/` — root-level node tests (`*.test.cjs` / `*.test.mjs`).
- `docs/` — cross-cutting how-tos and gotchas. **Read the relevant doc before deep
  work**: `docs/creating-an-addon.md`, `docs/lint-and-quality.md`,
  `docs/js-typing-strategy.md`.

## Gotchas

- `check-py` needs `pytest-cov` (in `requirements.txt`; `make install` first) and,
  for `graph/tests`, `networkx`.
- **`make install` also runs `npm ci`**, syncing `node_modules` exactly to
  `package-lock.json`. `make check-node`/`precommit` never install JS deps
  themselves — a stale `node_modules` can silently drift from a changed
  `package.json` and nothing in the gate will catch it except re-running the
  affected suite. See `docs/js-testing.md`'s jsdom pin note for a case where
  this bit us.
- **Python dev/lint tools need a venv.** System `python3` is Homebrew and
  externally-managed (PEP 668), so a bare `pip3 install` of ruff/black/mypy/bandit
  is blocked. Install the pinned tools into a venv: `make install-dev` (or
  `pip install -r requirements-dev.txt`). CI installs them fresh, so no venv there.
  Nothing auto-syncs this venv, but `quality-py`'s targets fail loudly on a version
  mismatch against the `requirements-dev.txt` pin (formerly a stale local tool
  silently passed and only broke in CI); the fix is always `make install-dev`.
- TDD-style corner-case tests live next to each add-on (e.g.
  `auto_wiktionary/tests/` pins Wiktionary redirect cases). Add a failing test
  there first, then fix.
- **Workspace layout.** The repo lives at `~/dev/anki` and is symlinked back into
  Anki's add-on folder at `~/Library/Application Support/Anki2/addons21`. Edit
  files in `~/dev/anki`; Anki follows the symlink to see the same content. If you
  ever move the working tree back under a path that contains a space (such as the
  original `Application Support/Anki2/addons21` path), Makefile recipes that build
  `VAR=$(CURDIR)/...` as an env-var prefix MUST quote it (`VAR="$(CURDIR)/..."`)
  — unquoted, `/bin/sh` word-splits at the space and tries to _execute_ the tail
  of the path instead of setting the var. Pinned by
  `tests/test_makefile_curdir_quoting.py`.
- **`precommit-fix`'s `YOLO=1`/`MSG=` commit step runs `git add -A`.** If another
  process has unrelated uncommitted changes sitting in this working tree when it
  runs — a concurrent agent session sharing the checkout, a background task not
  given worktree isolation — they get swept into that commit under an unrelated
  message (this happened: 2026-07-13, commit `e3800278`). Check `git status`
  before running `precommit-fix` with `YOLO=1`/`MSG=`, and prefer worktree
  isolation for any spawned session that might invoke it.
- **Limited/slow network:** `precommit-fix` pushes via `tools/git_push_retry.py`
  (backoff retries + per-commit chunking; run it directly to drain unpushed
  commits) and caps its backgrounded R2/graph uploads at `NET_DEADLINE` seconds
  (default 900; raise with `NET_DEADLINE=3600` to let a slow upload finish).
  Failures are loud, never silent, and reruns resume incrementally. Full map:
  `docs/limited-network.md`.
- **`make -n precommit-fix` is NOT a dry run** — GNU make executes
  `$(MAKE)`-bearing recipe lines under `-n`, so it used to really commit. The
  Makefile now refuses `-n`/`-q`/`-t` for this target at parse time (pinned by
  `tests/test_makefile_dryrun_guard.py`); don't try to "syntax check" it that way.
- **A running agent session sees skills as of session start.** Editing or
  syncing `.agents/skills/` mid-session does not change what the running session
  has loaded — an invoked skill still uses the pre-edit text (observed: `/retro`
  loading a pre-consolidation copy). Start a new session to pick up skill edits.

## Coding standards

### Anki imports

- **Explicit imports:** avoid wildcard imports (`from aqt.qt import *`). Use
  explicit imports: `from aqt.qt import Qt, QAction, QDialog, ...`.
- `anki` and `aqt` modules are provided by the Anki runtime and are not available
  in the local dev environment; use `# type: ignore` on those imports to suppress
  unresolved-import warnings in editors.
- **Never bind `mw` at module top level** (`from aqt import mw` at module root):
  when the module is first imported by Anki, `aqt.mw` is `None`, so the local
  reference stays bound to `None` permanently. Look up `mw` dynamically inside
  functions or methods (`import aqt; mw = aqt.mw`, or `from aqt import mw` inside
  the function).

### Configuration pattern

- **Dictionary-first:** always ensure config objects are initialized to a dict,
  even if `getUserOption()` returns `None`:
  `conf = getUserOption() or getDefaultConfig()` or `conf = getUserOption() or {}`.
- Use `Dict[str, Any]` for config objects to avoid "None type is not
  subscriptable" errors.

### Python version & dependencies

- The CI workflow (`.github/workflows/ci.yml`) is pinned to Python **3.13** to
  match the local development venv and avoid issues with newer/pre-release Python
  (e.g. Bandit crashing on 3.14 due to AST deprecations).
- Any third-party package used in add-on code or tests that is not in the standard
  library (e.g. `beautifulsoup4`) must be listed in `requirements.txt`. Anki
  bundles packages like `beautifulsoup4` and `requests` at runtime, but they are
  not available in local/CI test runs outside Anki unless declared.

## Sibling repositories

This project is part of a cluster of repositories. Note the primary branch names
and verification commands.

| Repository        | Path                     | Primary Branch | Verification     |
| ----------------- | ------------------------ | -------------- | ---------------- |
| **Anki Addons**   | `.`                      | `main`         | `make precommit` |
| **Fund**          | `~/dev/fund`             | `main`         | `make precommit` |
| **Networking**    | `~/dev/networking`       | `main`         | `make precommit` |
| **Personal Site** | `~/dev/ryusoh.github.io` | **`master`**   | `make check`     |

### Multi-repo workflow

- **Automation:** use the `/ship <branch>` command in any repo to fix quality
  failures, merge to the primary branch, and clean up.
- **Git hooks:** all repos use pre-commit hooks (e.g., `prettier`). If a push
  fails, run the repo's fix command (e.g., `make fmt-py`, `make fmt`, or
  `make precommit-fix`) before retrying.

## Lanes (keep PRs disjoint to avoid collisions)

| Routine     | Owns                                                       | Must NOT touch                            |
| ----------- | ---------------------------------------------------------- | ----------------------------------------- |
| Testpilot   | test-only additions/coverage, no prod-code change          | any production file                       |
| Refactoring | cyclomatic-complexity refactors (behaviour-preserving)     | error-handling/security, tests, features  |
| Sentinel    | security + error-handling (XSS, injection, silent catches) | complexity refactors, features            |
| Palette     | accessibility (ARIA, keyboard, focus) in `js/` + CSS       | security, perf, complexity                |
| Janitor     | dead code, stale deps, real TODOs only                     | complexity, error-handling, tests         |
| Bolt        | measurable performance/efficiency on a real hot path       | anything another lane owns in the same PR |
| Typist      | JS strict-type annotations (JSDoc) + whitelist expansion   | runtime behaviour                         |

If your finding belongs to another lane, **skip it** — that lane will get it. If a
scan finds nothing actionable in your lane, **open no PR**; an empty pass is a
success, not a reason to invent work or reach into another lane.

## `.jules/` is read-only personas — never write to it

The files in `.jules/<name>.md` are **persona definitions**: your identity, lane,
and constraints, which you read at the start of a run. They are **not logs**.
**Never append to, modify, or create files under `.jules/`.** A PR that changes a
`.jules/` file is out of scope and will be closed — those files are edited by a
human, not by routines.
