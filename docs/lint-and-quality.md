# Lint & quality gate

This repo enforces formatting, linting, type, and security checks on **first-party
code only**. Third-party Anki addons installed from AnkiWeb (`awesome_tts`,
`review_heatmap`, `enhance_main_window`, `custom_background`, and the tiny
single-file addons) are **excluded in every tool config** — we do not enforce our
style on code we did not author.

## Toolchain

| Layer                        | Tool             | Config                                  | Scope                             |
| ---------------------------- | ---------------- | --------------------------------------- | --------------------------------- |
| JS lint                      | ESLint (flat)    | `eslint.config.cjs`                     | first-party `*.js` (ignores list) |
| CSS lint                     | Stylelint        | `.stylelintrc.cjs` + `.stylelintignore` | first-party `*.css`               |
| Markdown lint                | markdownlint-cli | `.markdownlint.json`                    | tracked `*.md`                    |
| Format (JS/CSS/MD/JSON/HTML) | Prettier         | _defaults_ (no `.prettierrc`)           | `make fmt` glob                   |
| Python lint                  | Ruff             | `[tool.ruff]` in `pyproject.toml`       | `PY_ALL`                          |
| Python format                | Black            | `[tool.black]` in `pyproject.toml`      | `PY_ALL`                          |
| Python types                 | mypy             | `mypy.ini`                              | `PY_SRC`                          |
| Python security              | Bandit           | `.bandit` (INI, via `--ini`)            | `PY_SRC`                          |

`PY_SRC` / `PY_ALL` are defined in the `Makefile` and mirror `PY_TEST_SUITES`.

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

## CI

`.github/workflows/ci.yml` runs `make precommit SKIP=1` on push/PR to `main`:
`npm ci` + `pip install -r requirements-dev.txt`, then the full gate. `SKIP=1`
drops the interactive fetch/R2 prompts and disables auto-fixing — CI verifies, it
does not mutate.
