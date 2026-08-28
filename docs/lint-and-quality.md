# Lint & quality gate

This repo enforces formatting, linting, type, and security checks across **all addon
source we maintain** — including addons originally installed from AnkiWeb
(`awesome_tts`, `review_heatmap`, `enhance_main_window`, `custom_background`, …) that
we modify here. The only code kept out of the gates is **genuinely vendored**:
`review_heatmap/libaddon/` (a vendored framework and its `_vendor/` package trees)
and minified bundles (`**/*.min.{js,css}`). Those exclusions live in the tool
configs, not in the `Makefile` scope.

## Toolchain

| Layer                        | Tool                  | Config                                  | Scope                                                         |
| ---------------------------- | --------------------- | --------------------------------------- | ------------------------------------------------------------- |
| JS lint                      | ESLint (flat)         | `eslint.config.cjs`                     | addon `*.js` (vendored excluded)                              |
| CSS lint                     | Stylelint             | `.stylelintrc.cjs` + `.stylelintignore` | addon `*.css` (vendored excluded)                             |
| Markdown lint                | markdownlint-cli      | `.markdownlint.json`                    | tracked `*.md`                                                |
| Format (JS/CSS/MD/JSON/HTML) | Prettier              | _defaults_ (no `.prettierrc`)           | `make fmt` glob                                               |
| JS types                     | tsc `--checkJs`       | `jsconfig.json`                         | strict-mode whitelist only (see `docs/js-typing-strategy.md`) |
| Python lint                  | Ruff                  | `[tool.ruff]` in `pyproject.toml`       | `PY_ALL`                                                      |
| Python format                | Black                 | `[tool.black]` in `pyproject.toml`      | `PY_ALL`                                                      |
| Python types                 | mypy                  | `mypy.ini`                              | `PY_SRC`                                                      |
| Python security              | Bandit                | `.bandit` (INI, via `--ini`)            | `PY_SRC`                                                      |
| Python complexity            | xenon (radon)         | `Makefile` `complexity-py`              | `PY_ALL` (vendored excluded via `-e`)                         |
| JS dependency structure      | dependency-cruiser    | `.dependency-cruiser.cjs`               | `js/` (`js/vendor` excluded)                                  |
| Python dependency structure  | import-linter (grimp) | `pyproject.toml` `[tool.importlinter]`  | addon packages (`data/anki` excluded)                         |

`PY_SRC` / `PY_ALL` are defined in the `Makefile`: the addon source we maintain
(broader than `PY_TEST_SUITES`), with vendored code excluded via the tool configs.

## Running it

```bash
make install-dev          # one-time: pin'd ruff/black/mypy/bandit into a venv
make lint                 # ESLint + Stylelint + markdownlint
make typecheck-js         # tsc --checkJs on the jsconfig.json whitelist
make quality-py           # ruff + black --check + mypy + bandit
make precommit SKIP=1     # the whole gate (what CI runs)
```

Auto-fix the mechanical findings:

```bash
make fmt-py               # black + ruff --fix  (Python)
make lint-fix             # eslint --fix + stylelint --fix + markdownlint --fix
make fmt                  # prettier --write
```

After hand-authoring Python, run `make fmt-py` **before** `make quality-py`: the
gate's black step is check-only, so a formatting miss costs a full mypy pass over
the whole repo before you find out.

## Complexity ratchet

Both languages freeze their current cyclomatic-complexity state and fail on any
regression (the Refactoring lane works the backlog down):

- **JS:** `eslint.config.cjs` sets `complexity: ['error', { max: 20 }]` and
  `eslint-suppressions.json` baselines the legacy violations (file → rule →
  count; ESLint bulk suppressions only apply to error-severity rules). Any **new
  or worsened** violation fails `lint-js`. The suppressions file is the backlog:
  after fixing one, run `npx eslint --prune-suppressions` to shrink it — the
  baseline only ratchets down. Never hand-edit it.
- **Python:** `make complexity-py` (part of `quality-py`, so part of the CI
  gate) runs xenon over `PY_ALL` with ceilings freezing the measured state:
  `--max-average A --max-modules F --max-absolute F` (average A / 3.29, worst
  blocks F). Never raise the ceilings; tighten them only after refactors lower
  the measured ranks. Find targets with
  `.venv/bin/python3 -m radon cc <dirs> -s -n B`.

## Stream-of-consciousness gate

`make thinking-check` (part of `VERIFY_GATE`) deterministically enforces
AGENTS.md non-negotiable #10 across **all** in-scope Python, JS, and CSS
sources — tracked files plus untracked-but-not-ignored ones, so a new file is
scanned before commit, not after (unattended agents write both languages, so
this is not test-only). `tools/check_thinking_comments.py` fails on:

- **Thinking-out-loud comments** — openers like "Wait, ...", "Ah, ...", "Hmm",
  "Actually, ...", "Let's check ...", and coverage-chasing notes like "to
  hit/reach line N". Python comments are matched via `tokenize` (string
  contents never count); JS/CSS via a block-comment-aware line scan that
  ignores URL schemes (`https://`).
- **Abandoned test bodies** — pytest-collectable functions (module-level
  `test_*`, `Test*` methods) whose body is only `pass`/`...`/a docstring, and
  JS `it()`/`test()` calls with an empty callback. Nested helpers (a `test_func`
  closure exercising a decorator) are not collectable and not flagged.

Vendored trees (`libaddon/`, `_vendor*/`, `assets/vendor/`) and minified bundles
are excluded. The pattern list is deliberately high-precision — a comment that
states a fact about behaviour must never match, so extend it only with observed
phrasings, and re-run the scan on the whole tree before shipping an addition.
The scanner's own source is scanned too: only **comments** are matched
(docstrings are exempt), so quote literal example phrasings in the module
docstring and paraphrase in trailing `#` comments — a quoted `"Wait, ..."`
example in a `#` comment self-matches.

## Bot PR hygiene gate

`make bot-pr-check` (part of `VERIFY_GATE`) deterministically enforces AGENTS.md
non-negotiable #11 on commits authored by the Jules bot
(`google-labs-jules[bot]`) in `origin/main..HEAD`. Wording alone did not stop
PR #494 (existing tests deleted in a coverage PR, then five empty churn
commits), so `tools/check_bot_pr_hygiene.py` fails the gate on bot commits
that change no files, touch files with zero content lines (the
`dummy_file.txt` placeholder pattern), or delete lines from test files — bot
lanes are append-only in `tests/` (Testpilot owns tests; no other bot lane may
touch them). Human-authored commits are skipped: interactive agents may
legitimately rewrite tests on request. CI runs the same check on every PR
(`ci.yml` checks out with `fetch-depth: 0` so the branch commits are visible
behind the merge commit).

## Mutation testing

Scaffold only — **not part of any gate** (a full run multiplies the suite
runtime by the mutant count). `make mutate-py` runs mutmut scoped to one
small real addon (`strip_html_tags`, via `pyproject.toml [tool.mutmut]`) and
prints the kill report; the weekly `.github/workflows/mutation-testing.yml`
(Mondays 02:00 UTC, `continue-on-error`) runs it in CI, restores the
`.mutmut-cache` incrementally, and uploads the report as an artifact.
Surviving mutants are information for Testpilot, not a failure.

- Smoke run (2026-07-26): **849 mutants, 553 killed, 267 survived, 17
  no-cover, 12 timeouts — 65% kill ratio** in ~52s (16.45 mutations/s).
  Survivors cluster in the GUI-hook wiring (`on_editor_did_init_buttons`,
  `on_js_message` return-shape details) — expected: those paths are only
  smoke-tested, and killing them is Testpilot backlog, not scaffold work.
- Config gotcha: mutmut sandboxes into `mutants/` and copies only
  `also_copy` paths — the addon's own `tests/` dir and the root `conftest.py`
  must be listed there or pytest collects nothing (exit 4). `debug = true` is
  kept in the config because mutmut swallows the underlying pytest error
  without it, which cost a debugging round-trip. `mutants/` and
  `.mutmut-cache/` are gitignored.
- **JS (Stryker) — evaluated and skipped, with evidence.** The only jest
  suites (`review_heatmap/tests/`) load the code under test via
  `fs.readFileSync` + `window.eval` inside jsdom (verified in
  `test_tooltip.test.js:8-50`). Stryker's jest runner instruments code
  through jest's transform/module hooks; a file read off disk and evaled
  bypasses instrumentation entirely, so every mutant would be an untested
  "survivor" and the score meaningless. The rest of the JS suite runs on a
  custom `node:test` runner (`tools/node_test_runner.mjs`), which Stryker
  has no test-runner plugin for. Unblock condition: convert the heatmap
  tests to import the bundle through jest's module system. `make mutate-js`
  exists only to print this pointer.

## Test streams

Two streams exist (per the agentic-quality-gates recommendation): the **unit
stream** (`<addon>/tests/test_*.py`) and a seed **acceptance stream**
(`strip_html_tags/tests/test_acceptance_strip_button.py`) — behaviour-level
tests that enter through the addon's real boundary (the pycmd message the
editor JS sends when the strip button is pressed) and assert user-visible
outcomes with hand-computed expectations in domain language. Acceptance tests
for an addon live next to its unit tests so `check-py` discovery picks them
up automatically; name them `test_acceptance_*.py`.

## Whole-suite coverage floor

Both suites carry a low global floor so coverage can't silently erode while
per-file work continues (Testpilot ratchets the floors upward, never down):

- **JS:** thresholds live in package.json's `"c8"` key (`lines`/`branches`/
  `functions`/`statements`), enforced by `tools/node_test_runner.mjs` after
  the c8 report (c8's CLI is unusable here — its yargs import crashes under
  Node 26 — so the runner drives the `Report` class and compares the summary
  itself). Measured 2026-07-26: lines/statements 72.3%, branches 92.05%,
  functions 87.9%; floors set at 70/90/85/70. Verified: passes at the set
  values, fails with exit ≠ 0 when `lines` was raised to 73.
- **Python:** `--fail-under=75` on the combined `coverage report` in
  `make check-py` (the flag must live in the recipe, NOT in `.coveragerc`'s
  `fail_under` — pytest-cov reads that file too, and a global floor there
  fails every per-suite run since each suite only covers its own addon;
  verified: suites at 45–60% went red with all tests passing). Measured
  2026-07-26: 77% total (branch coverage). Verified with `--fail-under=99`
  → exit 2.

## Dependency structure

Two gates, both preventive (zero violations on the day they landed, so no
baseline was needed), both part of the CI gate (`make depcheck` hangs off
`lint`; `make imports-py` hangs off `quality-py`):

- **JS (`make depcheck`):** dependency-cruiser over `js/` with a single rule,
  `no-circular`. Measured 2026-07-25: 39 modules, 29 dependencies, zero cycles.
  Alias resolution (`#js/`, `#ui/`, `#utils/`) goes through a webpack-config
  stub, `.dependency-cruiser.webpack.cjs` — deliberately not `options.tsConfig`,
  which makes dependency-cruiser look for a typescript <7 compiler (this repo
  has v7) and print a spurious `missing-typescript-transpiler` warning every
  run (verified). Resolution was verified by count comparison and JSON
  inspection: `#js/config.js` resolves to the real `js/config.js` module in all
  configurations; without the stub's `resolve.roots`, the web-root-absolute
  imports (`/js/…` in `js/mobile_ambient_bootstrap.js`) surface as 2 fake
  modules (41 modules cruised instead of 39), and the only unresolvable
  specifier left is `three` (a genuine CDN/import-map external) — unresolved
  aliases would silently neuter path-based rules. Two rules from the fund
  reference were **measured but not ported**: the cross-page rule (this repo
  has no `js/pages/` concept) and the not-to-vendor rule (`js/cursor-init.js`
  imports `js/vendor/cursor.js` directly by design — it is the vendor loader
  entry — so the rule measured 1 violation on day one and would gate the
  repo's own accepted pattern).
- **Python (`make imports-py`):** one import-linter `independence` contract —
  addons are self-contained (AGENTS.md: "each top-level directory is a
  self-contained add-on or tool") — over the 22 first-party packages. This is
  the opposite outcome from the fund repo, where the gate was skipped: there
  the interesting dirs were PEP 420 namespace packages invisible to grimp, but
  here every addon has an `__init__.py` and grimp 3.15 sees all edges (235
  files, 355 dependencies measured; even the namespace `tools/` package
  resolves). The contract found exactly two cross-addon imports, both
  intentional optional integrations in `tabbed_stats/__init__.py` (try/except
  runtime imports of sibling addons that may not be installed), whitelisted via
  `ignore_imports`. `data/anki` is excluded — standalone scripts, not a
  package. Any **new** cross-addon import fails the gate.

## `precommit` vs `precommit-fix`

Both end with the **same** `$(VERIFY_GATE)` (`fmt-check lint typecheck-js
quality-py check sync-check`), defined once in the `Makefile` so they cannot
drift:

- `make precommit` — **verify only.** Exactly what CI runs (`make precommit SKIP=1`).
- `make precommit-fix` — **fix then verify.** Auto-fixes first (`fmt`, `lint-fix`,
  `fmt-py`), then runs the identical gate. So **a green `precommit-fix` means a green
  CI** — if it passes, all lint/format/type/security and tests pass. It can also
  commit/push (`MSG=…` / `YOLO=1`); because it runs the full gate first, it won't push
  something CI would reject.

To add a new check to the gate, edit `VERIFY_GATE` once — it applies to both paths
and to CI. The commit that introduces a check must also leave the whole tree green
under it — run the new target before committing (the `thinking-check` introduction
shipped with its own source file self-matching and broke CI until fixed).

## Environment gotchas

System `python3` is Homebrew and **externally-managed (PEP 668)** — a bare
`pip3 install ruff` fails. Install dev tools into a venv (`make install-dev`, or
`pip install -r requirements-dev.txt`). Versions are **pinned** in
`requirements-dev.txt` so local and CI produce identical formatting; bumping black
or ruff can change formatting and turn the build red, so bump deliberately.

Unlike `node_modules` (auto-synced by `make install` via `npm ci`), nothing
re-installs this venv when `requirements-dev.txt` changes — it can silently drift
(e.g. `black` bumped in the pin but not in your local venv). `lint-py`,
`fmt-py-check`, `typecheck`, and `security-py` each compare their tool's
`--version` against the pin before running and fail fast with `make install-dev`
as the fix, so a stale local tool can no longer format/lint with the wrong version
and produce a result that silently diverges from CI.

**Fresh git worktrees have no `.venv`** — and without one, `$(PYTHON)` falls back
to the system python3, whose bundled pip is too old to even resolve the pinned
tools (`make install-dev` used to fail with "No matching distribution found for
black==…"). `make install-dev` (and `make install`) now bootstrap `.venv` first:
in a linked worktree they symlink the main checkout's `.venv` (instant, shares
the pins), otherwise they create a fresh one. So the fix in a new worktree is
still just `make install-dev`.

### Makefile Execution Gotchas

- **Spaces in paths:** The repo path `$(CURDIR)` contains spaces (e.g., `/Application Support/`). Always quote commands that interpolate `$(CURDIR)`, and avoid using `$(wildcard)` with absolute paths since it splits on spaces. Use relative paths with `$(wildcard)` (e.g., `$(wildcard .venv/bin/python3)`).
- **Python tool invocation:** Python CLIs (like `ruff`, `pytest`, `mypy`) installed in the virtual environment should always be invoked via `$(PYTHON) -m <tool>` in the `Makefile`. This ensures the exact local virtual environment is respected, preventing system PATH leaks and `ImportError`s (e.g., missing `networkx`).
- **Background vs Foreground Concurrency:** The user's terminal and background agent tasks share the same filesystem. When writing `Makefile` targets that generate files, always use a uniquely generated temporary directory (e.g., `mktemp -d`) rather than a hardcoded static path (like `coverage/py-data`) to completely prevent filesystem race conditions if the target is invoked concurrently.
- **mktemp Path Gotcha:** By default, `mktemp -d` on macOS generates an absolute path (e.g., `/var/folders/...`). If your `Makefile` recipes prefix variables with `$(CURDIR)/`, this will create invalid double-paths (e.g., `$(CURDIR)//var/folders/...`) that fail silently. When creating temporary directories that will be prefixed with `$(CURDIR)`, force `mktemp` to generate a relative path by passing a template in the current directory, for example: `mktemp -d .tmp.XXXXXX`.

## Conventions baked into the configs

- **Ruff** selects `E,F,I,B`, ignores `E501` (black owns line length, 100). Anki
  addons manipulate `sys.path` before importing, so `E402` and test-fixture
  `F401`/`F811` are ignored per-file (see `[tool.ruff.lint.per-file-ignores]`).
- **ESLint** `no-undef` is an error; webview/bridge globals (`pycmd`,
  `bridgeCommand`, `MathJax`) and vendored libs (`d3`, `Chart`, `gsap`) are declared.
  Style nits (`no-var`, `prefer-const`) are warnings — they don't fail CI.
- **Bandit** runs at high severity (`-lll`) and skips `B404`/`B603` (intentional
  subprocess use in tooling). Read the `--ini .bandit` flag: Bandit's `-c` expects
  YAML, so the INI config must be passed with `--ini`.
- **Prettier** uses defaults on purpose — adopting a custom style would reformat the
  entire repo (incl. third-party) for no lint benefit.
- **Config detection in `lint-js`/`lint-css`** pipes `ls` to `grep -q .`, never
  `ls glob >/dev/null 2>&1`. `ls a* b*` exits non-zero when _either_ glob is
  unmatched, so the exit-code form silently skipped the linter whenever a flat
  `eslint.config.cjs` existed but legacy `.eslintrc*` didn't. `tests/test_makefile_lint_gate.py`
  pins this — a silently-skipping lint gate fails the test suite.

## CI

`.github/workflows/ci.yml` runs `make precommit SKIP=1` on push/PR to `main`:
`npm ci` + `pip install -r requirements-dev.txt`, then the full gate. `SKIP=1`
drops the interactive fetch/R2 prompts and disables auto-fixing — CI verifies, it
does not mutate.
