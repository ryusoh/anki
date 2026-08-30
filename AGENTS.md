# AGENTS.md

Single source of truth for agent guidance on this repo — **edit this file, not
`CLAUDE.md`** (that is a stub that imports this one). Deeper how-tos live in
`docs/`; slash-command workflows live in `.agents/skills/` (canonical — the
open Agent Skills format; `.claude/commands/` is generated from it by
`tools/sync_commands.py`, `.claude/skills` is symlinked to `.agents/skills`,
and the gate drift-checks it via `make sync-check`).

## Two audiences (do not mix these up)

- **Unattended Jules routines** (`.jules/` personas): these bots run without a
  human in the loop and open PRs. A human only does a binary approve/close on the
  result — they will **not** leave review comments or iterate with you. So every
  PR must be self-evidently correct and approvable at a glance. Optimize for
  **approve rate**, not for volume. The sections from "Non-negotiables" through
  "Lanes" are binding on Jules routines.
- **Interactive coding agents** (Claude Code, Kimi, Antigravity, etc.): you work
  directly with the user in a chat session. The project conventions below still
  apply, but the Jules-only **PR/branch/lane restrictions do not**. You may edit
  build files, Makefiles, configs, dependencies, and even `.jules/` persona files
  (no explicit permission needed — the user reviews the result; see the editing
  rules below). You may commit to `main` or open PRs as directed
  by the user. Do not invent Jules-style lane boundaries for normal interactive
  work — if the user asks you to change something, change it.
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
   (`fmt-check` + `lint` + `typecheck-js` + `quality-py` + `check` +
   `sync-check` + `thinking-check` + `bot-pr-check`). Red = don't open it. A failure "in a file
   you didn't touch" or a "pre-existing environment issue" is still red — not an
   exemption; report it and open no PR. And don't rerun a red
   gate on an unchanged tree — a failed gate over an untouched worktree cannot
   go green, so edit something first. `python3 tools/gate_guard.py` enforces
   this: `snapshot` before the run, `check <hash>` before a retry (exit 1 =
   unchanged).
2. **One concern, smallest possible diff.** No drive-by edits, no scope creep.
   Diff size is inversely proportional to approval — keep it tiny.
3. **Stay in your lane** (see "Lanes" below). If two routines touch the same files,
   one PR gets closed. Don't fix something another lane owns.
4. **Never hand-edit generated `data/`** — it is produced by the pipeline.
5. **Never touch vendored code** — `review_heatmap/libaddon/`, any `_vendor/` tree,
   and minified bundles are third-party. Their TODOs and defects are not ours.
6. **Don't commit to `main`.** Branch off `main`, open a PR. (Note: This applies to unattended Jules agents; interactive agents such as Claude Code and Antigravity may commit directly to `main` when explicitly instructed by the user).
7. **Don't leave scratch files in the tree** — no `fix_*.cjs`, scratchpads, or
   debug scripts. The diff contains only the change and its tests.
8. **Don't write a command/example you haven't actually run this session.** Verify
   behaviour; don't infer it from a name or a `case` label.
9. **Check open and recently-closed PRs before you start, and don't repeat them**
   (`python3 tools/prior_prs.py`; `--stats` prints per-lane accept rates). A
   closed PR was closed for a reason; an open one already claims that work.
   Pick something new.
10. **No stream-of-consciousness in the diff.** Your reasoning stays out of
    committed code: no thinking-out-loud comments ("Wait, ...", "Ah, ..."), no
    abandoned `pass`-only tests. If an approach fails mid-write, delete the
    attempt — don't commit the trail. Code comments state facts about behaviour.
    Enforced deterministically by `make thinking-check`
    (`tools/check_thinking_comments.py`) over all tracked py/js/css sources.
11. **Never open an empty PR.** If the run produces no diff (zero changed
    files), end the run with no PR — an empty PR can't be merged and costs the
    reviewer a manual close. This includes when your task's goal turns out to
    be already satisfied by the current repo state (e.g. a stale scheduled-task
    prompt): a satisfied goal is a no-op, not a PR. (The fund sibling repo
    hand-closed six zero-file Typist PRs from exactly this, 2026-08.)
    **The same holds mid-PR: never push an empty or no-op commit** — including
    add-then-remove placeholder files (`dummy_file.txt`). Before every push,
    `git show --stat HEAD` must show a real diff that matches the commit
    message and, when responding to review feedback, actually addresses it.
    If you have nothing real to push, push nothing. (PR #494: five churn/empty
    commits pushed after review questions, none answering them — closed
    unmerged.) Machine-enforced for bot-authored commits by
    `tools/check_bot_pr_hygiene.py` (`make bot-pr-check`, part of the
    precommit gate and PR CI).

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

| Need                                                       | Command                                |
| ---------------------------------------------------------- | -------------------------------------- |
| Full CI gate (fmt + lint + quality + tests)                | `make precommit SKIP=1`                |
| All tests (JS c8 + per-addon pytest, coverage)             | `make check`                           |
| Python lint/format/type/security (ruff/black/mypy/bandit)  | `make quality-py`                      |
| Auto-fix Python format                                     | `make fmt-py`                          |
| Lint (JS + CSS + Markdown)                                 | `make lint`                            |
| JS dependency-structure gate (dependency-cruiser)          | `make depcheck`                        |
| Auto-fix lint findings                                     | `make lint-fix`                        |
| Format JS/CSS/**MD**/JSON/HTML (Prettier)                  | `make fmt`                             |
| Scoped, fast Python test (tight loop, no coverage)         | `make test-py SUITE=<addon>/tests`     |
| Worktree snapshot guard (don't rerun a red gate unchanged) | `python3 tools/gate_guard.py snapshot` |
| Scoped test for one add-on (`test-py SUITE=<dir>/tests`)   | `make test-addon ADDON=<dir>`          |
| Scoped mypy for one add-on                                 | `make typecheck-addon ADDON=<dir>`     |
| JS test suite (c8 coverage)                                | `make check-node`                      |
| Mutation smoke run (mutmut, NOT part of any gate)          | `make mutate-py`                       |
| JS strict type check (whitelist)                           | `make typecheck-js`                    |
| Stream-of-consciousness scan (comments, abandoned tests)   | `make thinking-check`                  |
| Bot commit hygiene (empty commits, test deletions)         | `make bot-pr-check`                    |
| Build AVIF/WebP tiers for site CSS backgrounds             | `make images`                          |

Gate internals, complexity ratchet, dependency-structure rules, coverage
floors, and tool-config conventions live in `docs/lint-and-quality.md`. The
measured `precommit` baseline and parallelization notes live in
`docs/precommit-speed.md`. JS test discovery rules live in `docs/js-testing.md`.
Add-on coding standards (imports, config pattern, Python version/dependency
rules, Unicode hygiene) live in `docs/creating-an-addon.md`.

- **Run everything from the repo ROOT.** The root `conftest.py` mocks `aqt`/`anki`;
  running `pytest` inside an add-on subdir fails to import them. Use **`python3`**,
  never `python` (not on PATH).
- **Verify with the same python `make` uses.** `make` runs the repo-local
  `.venv/bin/python3`; a test green under a bare `python3 -m pytest` can be red
  under `make check`. A "verified" claim only counts if `make precommit SKIP=1`
  passed.
- **Run `make fmt` after hand-authoring any `docs/*.md`** — Prettier owns Markdown
  table/list formatting and `fmt-check` fails otherwise.
- **Run `make fmt-py` after hand-editing Python** — black owns formatting; scoped
  test runs don't catch a format miss, `fmt-py-check` does.

### Workflow maintenance

When bumping action versions in `.github/workflows/*.yml`, verify the tag exists
first (`gh api repos/<owner>/<repo>/git/refs/tags/v<N>`). A non-existent major
version such as `actions/cache@v7` fails the runner before the job starts.

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
- `sw.js` — root service worker. It precaches the core shell for `/`, `/terminal/`,
  and `/graph/` and serves live data (`/data/anki/`, `/graph/*.json`) network-first.
  The Pages workflow (`.github/workflows/pages.yml`) stamps `CACHE_NAME` with the
  deploy SHA on every deploy — don't hand-bump it. The register
  script (`js/ui/service_worker_register.js`) unregisters any existing SW on
  localhost to keep dev caches from shadowing local changes.
- `jsconfig.json` — the `tsc --checkJs` strict-mode whitelist; see
  `docs/js-typing-strategy.md` before touching it.
- `<addon>/` — each Anki add-on (Python) with its own `__init__.py`, hooks, and
  `tests/`. New add-on? See `docs/creating-an-addon.md`.
- `graph/` — Python graph pipeline (networkx). `data/anki/` — stats generators.
- `tests/` — root-level node tests (`*.test.cjs` / `*.test.mjs`).
- `tools/` — shared repository tooling (`gate_guard.py`, `check_thinking_comments.py`,
  `sync_commands.py`, `coverage_rank.py`, `dump_field.py`, etc.). Scripts referenced across
  agent docs and skills are verified by `tools/test_doc_tool_references.py`.
- `docs/` — cross-cutting how-tos and gotchas. **Read the relevant doc before deep
  work**: `docs/creating-an-addon.md`, `docs/lint-and-quality.md`,
  `docs/js-typing-strategy.md`, `docs/gotchas.md`.

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
- **Cross-cutting operational gotchas** (`precommit-fix` `YOLO=1` `git add -A`,
  concurrent agents sharing one worktree, limited network retry, `make -n`
  guard, skill regeneration, standalone graph scripts) live in
  `docs/gotchas.md`.

## Skills and slash commands

- **`.agents/skills/<name>/SKILL.md` is canonical** — the open Agent Skills
  format: YAML frontmatter declaring `name` and `description` (used for
  triggering), instructions in the markdown body. Edit skills there.
- **Self-contained skill bundles:** Each skill is a directory containing its
  `SKILL.md`, plus any skill-scoped helper scripts (`scripts/`) or prompt/data
  references (`references/`). Keep skill-specific logic bundled within its skill
  directory rather than placing one-off scripts in global `tools/` or `bin/`.
- **Progressive disclosure:** only the frontmatter `name` + `description` enter
  an agent's system prompt; the body is read on demand once the skill triggers.
  So the `description` is the only always-loaded surface — write it as a
  discriminative trigger ("Use when ..."), and don't contort the body to save
  prompt space; length there is free until the skill fires.
- **Never put a `---` horizontal rule in a skill body** — the generator's
  frontmatter parser is a naive `content.split("---", 2)`, so a `---` line in
  the body mangles the generated command.
- **`.claude/skills` is symlinked to `../.agents/skills`** for autonomous agent
  discovery across tools (Claude Code, DeepSeek Harness, etc.).
- **`.claude/commands/<name>.md` is generated** from the skills by
  `tools/sync_commands.py` for Claude Code interactive slash commands. Never edit
  the generated files by hand — run `python3 tools/sync_commands.py` after editing
  a skill, and note that `make sync-check` (wired into `make precommit`) fails if
  regeneration is not a no-op.
- **Skill schema validation:** `tools/test_skills.py` (run by `make check`)
  enforces schema validity, non-empty descriptions, directory-name matching, and
  symlink resolution across all skills.
- **Externalized state & transaction boundaries (State-Oriented Architecture):**
  On multi-step workflows (action-item sweeps, TDD loops, bug diagnosis), never rely on
  conversation memory as an execution ledger ($P = p^N$ failure). Follow Arista EOS's
  SysDB design: the disk-backed state ledger (`.agents/state/` via `tools/task_harness.py`
  or governing findings doc) is the single source of truth; worker agents are ephemeral,
  stateless transforms ($O(1)$ context) reading only their active gate slice. At each
  transaction boundary (after commits or gate checks) and on session resumption, follow
  the skill's `## Resume protocol`: re-anchor working memory directly from authoritative
  ground truth (`git status`, `git log`, state file) before dispatching tools.

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

| Routine     | Owns                                                                                                    | Must NOT touch                                                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Testpilot   | test-only additions/coverage, append-only (never delete or rewrite existing tests), no prod-code change | any production file                                                                                                                   |
| Refactoring | cyclomatic-complexity refactors (behaviour-preserving)                                                  | error-handling/security, tests, features                                                                                              |
| Sentinel    | security + error-handling (XSS, injection, silent catches)                                              | complexity refactors, features                                                                                                        |
| Palette     | accessibility (ARIA, keyboard, focus) in `js/` + CSS                                                    | security, perf, complexity                                                                                                            |
| Janitor     | dead code, stale deps, real TODOs only                                                                  | complexity, error-handling, tests, infrastructure/tools (`tools/`, `scripts/`, `bin/`, `.agents/`, `.jules/`, `.github/`, `Makefile`) |
| Bolt        | measurable performance/efficiency on a real hot path                                                    | anything another lane owns in the same PR                                                                                             |
| Typist      | JS strict-type annotations (JSDoc) + whitelist expansion                                                | runtime behaviour                                                                                                                     |

If your finding belongs to another lane, **skip it** — that lane will get it. If a
scan finds nothing actionable in your lane, **open no PR**; an empty pass is a
success, not a reason to invent work or reach into another lane.

## `.jules/` personas — editing rules

The files in `.jules/<name>.md` are **persona definitions** for the unattended
Jules routines: they encode identity, lane, and constraints, read at the start of
an unattended run. They are **not logs**.

- **Unattended Jules routines** must treat `.jules/` as read-only. They may **not**
  append to, modify, or create files under `.jules/`. A PR from a Jules routine
  that changes a `.jules/` file is out of scope and will be closed.
- **Interactive coding agents** (Claude Code, Kimi, Antigravity, etc.) **may**
  edit `.jules/` persona files whenever they spot a harness bug or unclear
  guidance — no explicit user direction needed; the user reviews the result.
  The change must still be a single-concern PR or direct commit with a green
  `make precommit SKIP=1`, and the agent must note in the commit/PR body that
  the edit is to a persona file.
- **Keep the Jules scheduled-task prompt generic** ("read `AGENTS.md` and your
  persona, work your lane"). A stale task-specific prompt is worse than the
  generic one: the routine satisfies the goal vacuously and still publishes the
  empty PR (non-negotiable #11). If a lane is finished, pause its schedule —
  don't leave a satisfied goal running.

Capture durable learnings in this file or `docs/` instead of leaving the persona
files as the only source of truth.
