---
name: sibling-repo-sync
description: Propagate a tooling/gate improvement from this repo to the sibling repos (fund, networking, ryusoh.github.io) — adapt, don't copy
argument-hint: "[what to sync, e.g. 'the complexity gate' or 'depcheck']"
---

Propagate an improvement from `~/dev/anki` to the sibling repos (verify against
each repo's current `AGENTS.md` and `Makefile`, as details drift).

## Shared sibling traits vs. repo-specific quirks

- **Home repo (`~/dev/anki`):** Python Anki add-ons + JS/graph pipeline; no
  `.pre-commit-config.yaml`; CI gate = `make precommit SKIP=1` (`fmt-check
lint typecheck-js quality-py check sync-check thinking-check bot-pr-check`);
  run everything from the repo root with `python3` (`conftest.py` mocks
  `aqt`/`anki`); Prettier owns Markdown formatting (`make fmt`);
  `tools/sync_commands.py` parses frontmatter via `content.split("---", 2)` and
  expects single-line `description`/`argument-hint` plus zero `---` horizontal
  rules in skill bodies.
- **Fund-only (absent in `anki`, `networking`, `ryusoh.github.io`):**
  `.husky/pre-push` fast-forward/deletion guard,
  `.github/workflows/commit-lint.yml`, and
  `scripts/agents/check_commit_message.py` — keep commit-title guidance generic
  per target `AGENTS.md`. Jules routines were retired across all four repos in
  November 2026.
- This skill exists in all four repos with perspective flipped to the home
  repo; sync improvements to this skill back to the other three copies.

## Sibling repo profiles

- **`~/dev/fund`** — static vanilla-JS/CSS financial dashboard + Python data
  pipeline. Default branch: `main`. CI gate: `make precommit-fix` (runs format,
  lint, JS/Python tests, and `.pre-commit-config.yaml` hooks whose eslint uses
  `--max-warnings=0`; `make verify` adds mypy, bandit, and sync-check without
  running hooks, so wire new checks into `verify` deps and `precommit-fix`).
  `precommit-fix` auto-fixes without committing/pushing, and ends with
  `git checkout data/transactions.csv || true` (check `git status` first in a
  shared tree). Diff-coverage gate requires 90% on PR diffs. `data/` is
  pipeline output; tracks `.ts` under `js/ui/cal-heatmap-src/`;
  `scripts/vendor/` and `tests/js/__mocks__/vendor/` are first-party (vendored
  exclusions are `assets/vendor/`, `js/vendor/`, `tests/js/vendor/`). Agent
  tooling lives in `scripts/agents/` (`gate_guard.py`, `prior_prs.py`,
  `check_commit_message.py`), while skill sync is `scripts/sync_commands.py` at
  top level; Python tests live in `tests/python/`. `ci.yml` checks out with
  `fetch-depth: 0`. Shares the home repo's `.github/workflows/pages.yml`
  shape (GitHub Pages deploy + service-worker cache stamping + 3-attempt
  deploy retry with backoff, synced Nov 2026).
- **`~/dev/networking`** — multi-language net-tools monorepo (JS Chrome
  extension, Python, C, eBPF); no `.pre-commit-config.yaml`. Default branch:
  `main`. CI gate: `make precommit` (on macOS: `make precommit-docker`, because
  raw-socket tests fail on host; host `make test-py`/`lint`/`thinking-check`
  need `PY=/Users/lz/dev/.venv/bin/python3` when system `python3` lacks
  `pytest`/`xenon`). `precommit-docker` exits 0 amid noisy logs — judge by exit
  code; cold path (colima + image build + tests) takes 10+ min, so warm Docker
  early and run once at the end. After a container run, clear leftover Linux
  ELF binaries in `nas_tools` / `nas_proxy` (`make -C nas_tools clean &&
make -C nas_proxy clean`) if host `make precommit` hits `Exec format error`.
  `test-py` hardcodes its pytest dirs (`tools` is already included; new
  top-level dirs need registration). `AGENTS.md` #6 restricts unrequested
  dep/config edits (#5 pins jest v29); covers `adblock/`. No stylelint or
  markdownlint (`prettier --check` covers CSS and Markdown). `ci.yml` rejects
  empty PRs and uses `fetch-depth: 0`. `ship` uses "Branch mode" and asks
  before push. Generated outputs: `coverage/`, `adblock/dist/`,
  `nas_proxy/out/`, `.claude/commands/`, command logs. No Pages deploy
  workflow — deploy-retry syncs do not apply.
- **`~/dev/ryusoh.github.io`** — JS-only static site (plain `<script>`, no ES
  modules, no Python data pipeline). Default branch: **`master`**. CI runs
  `pre-commit run --all-files` plus direct `npx` steps (not `make`), so a
  Makefile-wired check also needs a workflow step for CI enforcement. Local
  non-staging CI-parity gate: `make gate` (`check` + `test`, ~1 min);
  `make precommit-fix` runs `.pre-commit-config.yaml` hooks with `|| true` and
  stages auto-fixes via `git add -u`. `lint-js`/`lint-css` use
  `--max-warnings=0`; prettier runs via `./scripts/run-npx.sh prettier`.
  `package-lock.json` is authoritative (`pnpm-lock.yaml` drifts out-of-band).
  Python tooling lives in `tools/sync_commands.py` + `tools/__tests__/` (pytest
  via `/Users/lz/dev/.venv`, wired into a pre-push hook
  `pytest -q || [ $? -eq 5 ]`, unwired in Makefile). `ci.yml` uses
  `fetch-depth: 0` and Python 3.12. `ship` is a single linear `master` flow
  (`make check` + `make test`, asks before push). Shares the home repo's
  `.github/workflows/pages.yml` shape (GitHub Pages deploy + service-worker
  cache stamping + 3-attempt deploy retry with backoff, synced Nov 2026;
  branch `master`, cache prefix `ryusoh-cache-`).

## Process

Delegate one subagent per sibling repo to research, edit, and run scoped fast
checks in parallel, **but serialize/stagger the final full-repo CI-parity gate
(one repo at a time) to avoid CPU oversubscription on the shared host**. Brief
each with:

1. **Reference implementation:** concrete files in `~/dev/anki` carrying the
   pattern (config, Makefile target, hook, doc).
2. **Adapt to the target:** measure rules and ceilings against the target's own
   structure and `AGENTS.md` — drop decorative rules that match nothing it
   cares about, enable checks that fit, and adapt repo-local names (e.g. `ship`
   modes: `anki` "Mode B", `networking` "Branch mode", `ryusoh.github.io` a
   linear flow).
3. **Wire into the real CI gate:** read `.github/workflows`, `Makefile`, and
   `.pre-commit-config.yaml` first so the check runs in the actual CI path.
4. **Baselines and ratchets:** for legacy violations, pair error severity with
   a shrink-only baseline (ESLint bulk suppressions model); zero violations
   ships baseline-free.
5. **Probe protocol:** append a violating probe to an unmodified tracked file
   → confirm gate fails → `git restore` → confirm gate passes and `git status`
   is clean (let restore errors surface rather than masking with `|| true`;
   probing an untouched file avoids wiping your real edits on restore).
6. **Self-scanning scanner gates:** a source scanner (like
   `thinking-check`) scans its own comments too. Keep sample banned phrasings
   out of real comments (construct test fixtures dynamically, e.g. `'i' + 't'`)
   and run the scanner over its own source before finishing.
7. **Dependency-cruiser alias proof:** wire aliases via a webpack-config stub
   (avoids TS v7's `missing-typescript-transpiler` warning on
   `options.tsConfig`; `enhancedResolveOptions` rejects alias keys). Prove
   resolution by comparing `"N modules, M dependencies"` with and without
   aliases — identical dependency counts and no inflated external-node count.
   Skip stubs when a repo has no aliases.
8. **Python import-linter:** `grimp` lacks PEP 420 namespace-package support,
   so check `__init__.py` and edge visibility first; if invisible, document
   the skip with measurements and unblock criteria. Invoke via the click entry
   point (`python -m importlinter.cli` silently no-ops) and gitignore/delete
   `.grimp_cache/`.
9. **Finish per repo:** iterate with scoped checks, then run the full
   CI-parity gate once at the end sequentially across repos after parallel
   scoped edits finish (for docs-only changes in `networking`, decide whether the
   10-min container run is warranted first). Format new config files, update the repo's `AGENTS.md` and gate docs, leave changes
   uncommitted, and report: violation counts, resolution proof, files changed,
   probe exit codes, gate result, and evidenced skip decisions.

## After the sync & resilience

- Update the sibling profiles above with any newly discovered drift; keep
  repo-specific docs inside each sibling repo.
- Because each subagent is isolated to its own repo, if a provider error kills
  parallel workers mid-flight, resume each failed worker to audit `git status`
  / `git log` and continue. Any parallel work touching `~/dev/anki` follows
  AGENTS.md "Shared checkout".
