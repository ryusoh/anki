---
name: new-addon
description: Scaffold and build a new Anki addon the house way — read the addon guide, TDD the logic, pass the full gate. Use when the user wants a new addon or a new editor button/hook feature.
argument-hint: "<what the addon should do>"
---

# New Anki addon

Build the addon described in `{{args}}` following this repo's conventions.
The knowledge lives in the repo — read it, don't guess:

1. **Read `docs/creating-an-addon.md` first, in full.** It is the single
   source of truth for layout (`__init__.py`, `manifest.json`, `tests/`),
   hook/monkeypatch patterns, the Anki-bundles-Python-3.9 rules, the
   mocked-`aqt` test pattern, and the verify commands. Skim a comparable
   existing addon (e.g. `auto_wiktionary/` for editor buttons,
   `no_leech_suspend/` for hooks) before writing anything.

2. **If the addon reads or writes note field HTML**, follow the guide's
   "Field HTML reality" section to the letter: dump real stored bytes with
   `python3 tools/dump_field.py '<front text>'` and develop the transform
   against those — never against an imagined format. Untouched fields must
   come back byte-identical.

3. **Build test-first** — run `/tdd` for the loop and its rules. Pure logic
   goes in its own module with the corner cases pinned in `<addon>/tests/`;
   the `aqt` wiring stays thin.

4. **Verify from the repo root**: `python3 -m pytest <addon>/tests/ -q`,
   re-run under `.venv/bin/python3`, then `make quality-py`. Remember the
   mocked suite cannot prove real-Anki behavior — the user restarts Anki and
   exercises the feature before anything is committed.
