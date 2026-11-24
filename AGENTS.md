# AGENTS.md

Canonical agent guidance for this repo — edit this file; `CLAUDE.md` only
imports it. Deeper how-tos live in `docs/`. Skills live in `.agents/skills/`
(canonical; `.claude/skills` symlinks to it, `.claude/commands/` is generated
by `tools/sync_commands.py`, and `make sync-check` catches drift).

## Context

A monorepo of Anki add-ons (Python) plus a JS/graph data pipeline. Each
top-level directory (`auto_wiktionary/`, `awesome_tts/`, `graph/`, `js/`,
`data/anki/`, …) is a self-contained add-on or tool with its own `tests/`.
Add-ons render into Anki's Qt WebView; there is no frontend build step (ES
modules via import map).

You are an interactive agent working with the user in chat; unattended
automation is limited to GitHub Actions workflows (the Jules routines were
retired in November 2026 — see `docs/lint-and-quality.md`). Edit build files,
Makefiles, configs, and dependencies whenever the task calls for it. When
options are close, pick the best one and proceed.

- New add-on → `docs/creating-an-addon.md` (layout, hooks, tests, Python 3.9
  floor).
- Debugging a field-transform add-on against a real card → "Field HTML reality"
  in `docs/creating-an-addon.md`, starting with
  `python3 tools/dump_field.py --contains '<text>'`.
- Writing a design spec for delegation → `docs/delegation-specs.md`.

## How the user works

- The user reviews diffs in VSCode and commits accepted work themselves. If
  your edits vanish from `git status` between turns, run
  `git log --oneline -3` once — a fresh user commit means the work was
  accepted; continue from HEAD.
- Commit or push only when asked (or when invoking a skill that commits as part
  of its workflow: `/ship`, `/implement-action-items`, `/gh-action-rescue`).
  Branch off `main` for PRs.
- On multi-step workflows (action-item sweeps, TDD loops, diagnosis), the
  progress ledger is `git status`, `git log`, and `.agents/state/` (via
  `tools/task_harness.py`) or the governing findings doc. Re-anchor from them
  at each commit boundary and after compaction via the skill's
  `## Resume protocol`.

## Shared checkout

The user, other agents, and background sessions edit this tree concurrently.

- Stage the files you changed by name (`git add <file>`). Uncommitted changes
  elsewhere belong to someone else — leave them in place.
- Keep `make precommit-fix` with `YOLO=1` or `MSG=` out of a shared checkout:
  its commit step runs `git add -A` and sweeps in unrelated edits.
- Discard only your own edits after `git diff <file>` confirms every hunk is
  yours. Wider resets (`git checkout -- <file>`, `git restore <file>`,
  `git reset --hard`, `git clean`, `git stash`) and `--no-verify` require
  explicit user confirmation.
- Keep concurrent agents on disjoint file sets; in a conflict, resolve only
  your own files.

## Quality bar for every change

1. **The CI gate is `make precommit SKIP=1`** (`fmt-check` + `lint` +
   `typecheck-js` + `quality-py` + `check` + `sync-check` + `thinking-check` +
   `bot-pr-check`). Open a PR only on a green gate. A red gate on an unchanged
   tree stays red — change something before rerunning
   (`python3 tools/gate_guard.py snapshot`, then `check <hash>`).
2. **One concern, smallest diff,** inside the task's files. For self-chosen
   work, run `python3 tools/prior_prs.py` (`--stats` for bot-PR outcomes) first
   so you pick something no open or closed PR already covers.
3. **`data/` is pipeline output** — regenerate it via `make fetch`. Leave
   vendored trees (`review_heatmap/libaddon/`, `_vendor/`, minified bundles)
   untouched.
4. **Write down only what you ran.** Commands and examples in docs or code must
   have been executed this session; verify behaviour rather than inferring it.
5. **Code comments state facts about behaviour** — keep thinking-out-loud notes
   and abandoned `pass`-only tests out of diffs (`make thinking-check` /
   `tools/check_thinking_comments.py` enforces this over py/js/css).
6. **Publish a PR as one commit with a real diff** and no scratch files. Commit
   once, gate that exact tree, push; on revision, amend or squash and
   `git push --force-with-lease`. A goal the repo already satisfies is a no-op,
   not a PR (`make bot-pr-check` / `tools/check_bot_pr_hygiene.py` enforces
   commit hygiene and the `eslint-suppressions.json` complexity ratchet, which
   only shrinks via `npx eslint --prune-suppressions`).
7. **Behaviour changes ship a test** that fails before and passes after,
   covering the changed lines. Behaviour-preserving refactors and dead-code
   removal keep the existing suite green. Earn coverage with real tests rather
   than suppression comments (`/* c8 ignore */`, `# pragma: no cover`).

## Visual changes

Add-ons render into Anki's Qt WebView; unit tests cannot observe colour, glass
refraction, spacing, or layout. Report objectively verifiable facts (DOM
attribute, `aria-label`, passing test) and leave aesthetic judgment to the
user. A PR whose payoff is visual is a draft marked "visual review required by
a human."

## Commits and PRs

- **Conventional Commits** (squash-merge uses the PR title as the commit
  subject, so both commits and PR titles follow it): `type(scope): summary`
  with `type` ∈ `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`,
  `build`, `ci`, `style`; optional lower-case scope (`auto_wiktionary`,
  `awesome_tts`, `review_heatmap`, `graph`, `a11y`, `security`, `deps`, …);
  imperative lower-case summary ≤ 72 chars, no trailing period, no emoji or
  routine-name prefix. Wrap the body at ~72 cols explaining what and why
  (metrics and severity belong in the body).
- **PR body:** **What & why** (1–2 sentences); **Verification** (exact commands
  and pasted results, e.g. `make precommit SKIP=1` → green); **Visual?** ("no
  visual surface" or "visual — human review required (draft)").

## Commands — prefer `make` (matches CI)

| Need                                                                     | Command                                |
| ------------------------------------------------------------------------ | -------------------------------------- |
| Full CI gate (fmt + lint + quality + tests)                              | `make precommit SKIP=1`                |
| All tests (JS c8 + per-addon pytest, coverage)                           | `make check`                           |
| Python lint/format/type/security (ruff/black/mypy/bandit)                | `make quality-py`                      |
| Auto-fix Python format                                                   | `make fmt-py`                          |
| Lint (JS + CSS + Markdown + depcheck)                                    | `make lint`                            |
| JS dependency-structure gate (dependency-cruiser)                        | `make depcheck`                        |
| Auto-fix lint findings                                                   | `make lint-fix`                        |
| Format JS/CSS/**MD**/JSON/HTML (Prettier)                                | `make fmt`                             |
| Scoped, fast Python test (tight loop, no coverage)                       | `make test-py SUITE=<addon>/tests`     |
| Worktree snapshot guard                                                  | `python3 tools/gate_guard.py snapshot` |
| Scoped test for one add-on (`test-py SUITE=<dir>/tests`)                 | `make test-addon ADDON=<dir>`          |
| Scoped mypy for one add-on                                               | `make typecheck-addon ADDON=<dir>`     |
| JS test suite (c8 coverage)                                              | `make check-node`                      |
| Mutation smoke run (mutmut, manual only)                                 | `make mutate-py`                       |
| JS strict type check (whitelist)                                         | `make typecheck-js`                    |
| Stream-of-consciousness scan (comments, abandoned tests)                 | `make thinking-check`                  |
| Bot commit hygiene (empty commits, test deletions, stray files, ratchet) | `make bot-pr-check`                    |
| Build AVIF/WebP tiers for site CSS backgrounds                           | `make images`                          |

- **Run everything from the repo root.** The root `conftest.py` mocks
  `aqt`/`anki`; running `pytest` inside an add-on subdir fails to import them.
  Use `python3` (`python` is absent from PATH).
- **Verify with the same python `make` uses (`.venv/bin/python3`).** System
  Homebrew `python3` is PEP 668 externally-managed and has different packages.
  Set up once with `make install` (runtime + `pytest-cov` + `npm ci` syncing
  `node_modules` to `package-lock.json`) and `make install-dev` (pinned
  ruff/black/mypy/bandit into `.venv`; `quality-py` fails fast on pin drift).
  Confirm both pytest and the JS runner execute.
- **Format after hand-editing:** `make fmt` for Markdown (Prettier owns
  tables/lists) and `make fmt-py` for Python (black owns formatting).
- **Workflow maintenance:** when bumping action versions in
  `.github/workflows/*.yml`, verify the tag exists first
  (`gh api repos/<owner>/<repo>/git/refs/tags/v<N>`).
- Deeper references: `docs/lint-and-quality.md` (gate internals, complexity
  ratchet, dependency rules, coverage floors), `docs/precommit-speed.md`,
  `docs/js-testing.md`, `docs/creating-an-addon.md`, `docs/gotchas.md`.

## Layout

- `js/` — frontend ES modules (`js/commands/`, `js/graph/`, `js/ui/`,
  `js/utils/`, `js/config.js`; no build step) and `js/types/*.d.ts` ambient
  declarations for `tsc --checkJs`.
- `sw.js` — root service worker precaching `/`, `/terminal/`, `/graph/` and
  serving `/data/anki/` and `/graph/*.json` network-first.
  `.github/workflows/pages.yml` stamps `CACHE_NAME` with the deploy SHA
  automatically; `js/ui/service_worker_register.js` unregisters it on
  localhost.
- `jsconfig.json` — `tsc --checkJs` strict-mode whitelist
  (`docs/js-typing-strategy.md`).
- `<addon>/` — self-contained Python add-on with `__init__.py`, hooks, and
  `tests/`.
- `graph/` — Python graph pipeline (`networkx`). `data/anki/` — stats
  generators. `tests/` — root-level node tests (`*.test.cjs` / `*.test.mjs`).
- `tools/` — repository tooling (`gate_guard.py`, `check_thinking_comments.py`,
  `check_md_boxes.py`, `check_md_latex.py`, `sync_commands.py`,
  `coverage_rank.py`, `dump_field.py`, `task_harness.py`, etc.); script
  references in agent docs and skills are checked by
  `tools/test_doc_tool_references.py`.
- `docs/` — subsystem how-tos and gotchas (every doc is linked from
  `docs/README.md`).

## Gotchas & skills

- **Workspace symlink & spaces:** The repo lives at `~/dev/anki` and symlinks
  into `~/Library/Application Support/Anki2/addons21`. Quote `$(CURDIR)` in
  Makefile env-var prefixes (`VAR="$(CURDIR)/..."`, pinned by
  `tests/test_makefile_curdir_quoting.py`) in case the tree lives under a
  space-containing path.
- **TDD corner-case tests** live next to each add-on (`<addon>/tests/`);
  `check-py` requires `pytest-cov` and `networkx` (`graph/tests`).
- **Operational & security traps** (`precommit-fix` `YOLO=1`/`MSG=`, `make -n`
  guard, shim `node`, dead-code/hook traps, flat `tools/` imports, DOM XSS,
  HTML escaping, SQLite parameterization, a11y) → `docs/gotchas.md`.
- **Skills (`.agents/skills/<name>/SKILL.md`):** Keep skill-specific helpers
  in `<skill>/scripts/` or `<skill>/references/`. Only `name` and `description`
  enter the always-loaded prompt, so write `description` as a single-line
  discriminative trigger ("Use when ..."). Omit `---` horizontal rules from
  skill bodies (`tools/sync_commands.py` splits frontmatter on
  `content.split("---", 2)`). Regenerate `.claude/commands/` with
  `python3 tools/sync_commands.py`; `make sync-check` and `tools/test_skills.py`
  validate every skill.

## Sibling repositories

| Repository        | Path                     | Primary Branch | Verification     |
| ----------------- | ------------------------ | -------------- | ---------------- |
| **Anki Addons**   | `.`                      | `main`         | `make precommit` |
| **Fund**          | `~/dev/fund`             | `main`         | `make precommit` |
| **Networking**    | `~/dev/networking`       | `main`         | `make precommit` |
| **Personal Site** | `~/dev/ryusoh.github.io` | **`master`**   | `make check`     |

Use `/ship <branch>` in any repo to verify, merge to the primary branch, and
clean up.
