# Lint & quality gate

This repo enforces formatting, linting, type, and security checks across **all addon
source we maintain** — including addons originally installed from AnkiWeb
(`awesome_tts`, `review_heatmap`, `enhance_main_window`, `custom_background`, …) that
we modify here. The only code kept out of the gates is **genuinely vendored**:
`review_heatmap/libaddon/` (a vendored framework and its `_vendor/` package trees)
and minified bundles (`**/*.min.{js,css}`). Those exclusions live in the tool
configs, not in the `Makefile` scope.

## Toolchain

| Layer                        | Tool             | Config                                  | Scope                             |
| ---------------------------- | ---------------- | --------------------------------------- | --------------------------------- |
| JS lint                      | ESLint (flat)    | `eslint.config.cjs`                     | addon `*.js` (vendored excluded)  |
| CSS lint                     | Stylelint        | `.stylelintrc.cjs` + `.stylelintignore` | addon `*.css` (vendored excluded) |
| Markdown lint                | markdownlint-cli | `.markdownlint.json`                    | tracked `*.md`                    |
| Format (JS/CSS/MD/JSON/HTML) | Prettier         | _defaults_ (no `.prettierrc`)           | `make fmt` glob                   |
| Python lint                  | Ruff             | `[tool.ruff]` in `pyproject.toml`       | `PY_ALL`                          |
| Python format                | Black            | `[tool.black]` in `pyproject.toml`      | `PY_ALL`                          |
| Python types                 | mypy             | `mypy.ini`                              | `PY_SRC`                          |
| Python security              | Bandit           | `.bandit` (INI, via `--ini`)            | `PY_SRC`                          |

`PY_SRC` / `PY_ALL` are defined in the `Makefile`: the addon source we maintain
(broader than `PY_TEST_SUITES`), with vendored code excluded via the tool configs.

## Running it

```bash
make install-dev          # one-time: pin'd ruff/black/mypy/bandit into a venv
make lint                 # ESLint + Stylelint + markdownlint
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

## `precommit` vs `precommit-fix`

Both end with the **same** `$(VERIFY_GATE)` (`fmt-check lint quality-py check`),
defined once in the `Makefile` so they cannot drift:

- `make precommit` — **verify only.** Exactly what CI runs (`make precommit SKIP=1`).
- `make precommit-fix` — **fix then verify.** Auto-fixes first (`fmt`, `lint-fix`,
  `fmt-py`), then runs the identical gate. So **a green `precommit-fix` means a green
  CI** — if it passes, all lint/format/type/security and tests pass. It can also
  commit/push (`MSG=…` / `YOLO=1`); because it runs the full gate first, it won't push
  something CI would reject.

To add a new check to the gate, edit `VERIFY_GATE` once — it applies to both paths
and to CI.

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
