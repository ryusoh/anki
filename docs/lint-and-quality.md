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

## Environment gotcha

System `python3` is Homebrew and **externally-managed (PEP 668)** — a bare
`pip3 install ruff` fails. Install dev tools into a venv (`make install-dev`, or
`pip install -r requirements-dev.txt`). Versions are **pinned** in
`requirements-dev.txt` so local and CI produce identical formatting; bumping black
or ruff can change formatting and turn the build red, so bump deliberately.

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
