---
name: new-addon
description: Scaffold and build a new Anki addon the house way — read the addon guide, TDD the logic, pass the full gate. Use when the user wants a new addon or a new editor button/hook feature.
argument-hint: "<what the addon should do>"
---

# New Anki addon

Build the addon described in `{{args}}` following this repo's conventions:

1. **Read `docs/creating-an-addon.md` first, in full.** It covers layout
   (`__init__.py`, `manifest.json`, `tests/`), hook/monkeypatch patterns, the
   Anki-bundles-Python-3.9 floor, mocked-`aqt` tests, and verify commands. Skim
   a comparable existing addon (`auto_wiktionary/` for editor buttons,
   `no_leech_suspend/` for hooks) before writing code.
2. **If the addon reads or writes note field HTML**, follow "Field HTML
   reality" in `docs/creating-an-addon.md`: dump real stored bytes with
   `python3 tools/dump_field.py '<front text>'` and build the transform against
   those. Untouched fields must come back byte-identical.
3. **Build test-first (`/tdd`).** Keep pure logic in its own module with corner
   cases pinned in `<addon>/tests/`, and keep the `aqt` wiring thin.
4. **Register in CI gate:** append `<addon>` to `PY_SRC` in `Makefile` and to
   `root_packages` and `modules` under `[tool.importlinter]` in
   `pyproject.toml`. Add a per-file-ignore entry in `pyproject.toml` only for
   legacy linting issues.
5. **Verify from the repo root:** `make precommit SKIP=1`. Since mocked tests
   cannot prove real-Anki behavior, the user restarts Anki and exercises the
   feature before committing.
