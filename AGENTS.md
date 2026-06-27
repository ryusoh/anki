# AGENTS.md

Shared operating contract for **automated agents** (Jules scheduled routines) on
this repo. You run unattended and open PRs. A human only does a binary
approve/close on the result — they will **not** leave review comments or iterate
with you. So every PR must be self-evidently correct and approvable at a glance.
Optimize for **approve rate**, not for volume.

This repo is a **monorepo of Anki add-ons (Python)** plus a JS/graph data pipeline.
Each top-level directory (`auto_wiktionary/`, `awesome_tts/`, `graph/`, `js/`,
`data/anki/`, …) is a self-contained add-on or tool with its own `tests/`. Add-ons
render into Anki's Qt **WebView**; there is no frontend build step (ES modules via
import map). Human-facing detail lives in `CLAUDE.md` and `docs/`.

## Non-negotiables (a PR that violates any of these will be closed)

1. **Open a PR only if `make precommit SKIP=1` is green.** It is the CI gate
   (`fmt-check` + `lint` + `quality-py` + `check`). Red = don't open it.
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
| Scoped, fast Python test (tight loop, no coverage)        | `make test-py SUITE=<addon>/tests` |
| JS test suite (c8 coverage)                               | `make check-node`                  |

- **Run everything from the repo ROOT.** The root `conftest.py` mocks `aqt`/`anki`;
  running `pytest` inside an add-on subdir fails to import them. Use **`python3`**,
  never `python` (not on PATH).
- **Don't run one combined `pytest`** over the whole repo — each add-on bootstraps
  its own `sys.path`, so suites only collect in isolation. `make check-py` runs them
  one at a time and accumulates coverage.
- A `coverage/` **directory** at the repo root shadows the `coverage` command —
  invoke it as `python3 -m coverage`, never bare `coverage`.

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
- `<addon>/` — each Anki add-on (Python) with its own `__init__.py`, hooks, and
  `tests/`. New add-on? See `docs/creating-an-addon.md`.
- `graph/` — Python graph pipeline (networkx). `data/anki/` — stats generators.
- `tests/` — root-level node tests (`*.test.cjs` / `*.test.mjs`).
- `docs/` — cross-cutting how-tos and gotchas. **Read the relevant doc before deep
  work**: `docs/creating-an-addon.md`, `docs/lint-and-quality.md`.

## Lanes (keep PRs disjoint to avoid collisions)

| Routine     | Owns                                                       | Must NOT touch                            |
| ----------- | ---------------------------------------------------------- | ----------------------------------------- |
| Testpilot   | test-only additions/coverage, no prod-code change          | any production file                       |
| Refactoring | cyclomatic-complexity refactors (behaviour-preserving)     | error-handling/security, tests, features  |
| Sentinel    | security + error-handling (XSS, injection, silent catches) | complexity refactors, features            |
| Palette     | accessibility (ARIA, keyboard, focus) in `js/` + CSS       | security, perf, complexity                |
| Janitor     | dead code, stale deps, real TODOs only                     | complexity, error-handling, tests         |
| Bolt        | measurable performance/efficiency on a real hot path       | anything another lane owns in the same PR |

If your finding belongs to another lane, **skip it** — that lane will get it. If a
scan finds nothing actionable in your lane, **open no PR**; an empty pass is a
success, not a reason to invent work or reach into another lane.

## `.jules/` is read-only personas — never write to it

The files in `.jules/<name>.md` are **persona definitions**: your identity, lane,
and constraints, which you read at the start of a run. They are **not logs**.
**Never append to, modify, or create files under `.jules/`.** A PR that changes a
`.jules/` file is out of scope and will be closed — those files are edited by a
human, not by routines.
</content>
