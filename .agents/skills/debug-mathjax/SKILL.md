---
name: debug-mathjax
description: Debug an auto_mathjax failure — $ conversion wrapping wrong, or MathJax showing red "invalid text" for a command. Classify conversion vs rendering, reproduce on the real field HTML, TDD a fix. Use when a card's math renders wrong or a button click converts wrong.
argument-hint: "<card snippet, LaTeX command, or symptom>"
---

# Debug an auto_mathjax failure

The problem to debug is `{{args}}`.

Pull the real stored bytes and classify before touching code.

1. **Get the real stored field HTML:**

   ```sh
   python3 tools/dump_field.py --contains '<some text from the card>'
   ```

2. **Classify: conversion bug or rendering bug.** In the dumped HTML, find the
   failing formula:
   - **Rendering bug** — the formula is _already wrapped_
     (`<anki-mathjax>…</anki-mathjax>` or `\(…\)` / `\[…\]`) but shows as red
     "invalid text" in Anki. Almost always: the command is missing from Anki's
     bundled MathJax (no `esint`, so `\oiint`, `\oiiint`, `\ointclockwise` fail
     while amsMath's `\oint`, `\iint`, `\iiint` work). The house fix lives in
     `CUSTOM_MACROS` + `_inject_macro_defs` in `auto_mathjax/__init__.py`
     (precedents: `lambdabar` via `\unicode`, `oiint`/`oiiint` via
     `\mathop{\bigcirc\mkern-14mu\iint}` overlay).
   - **Conversion bug** — raw `$…$` / bare LaTeX left unwrapped, or prose
     wrongly wrapped. The bug lives in the `_convert_dollar_to_mathjax`
     pipeline: `LINE_SPLIT_RE` segmentation, `DOLLAR_PAIR_RE`,
     `_looks_like_math_content` (cashtag/currency guards),
     `_looks_like_bare_latex` + `BARE_LATEX_COMMAND_RE` (whitelist gaps — e.g.
     a bare `\iint` line needs `iint` listed; standalone `\oint`/`\oiint`/
     `\oiiint` symbols in prose use `STANDALONE_SYMBOL_RE`, whereas
     operand-taking `\oint_C` takes a different branch),
     `_wrap_embedded_latex` (CJK lines are deliberately skipped).

3. **Reproduce in Python** against the dumped HTML (import root `conftest`
   first to stub `aqt`/`anki`):

   ```sh
   .venv/bin/python3 -c "
   import conftest
   from auto_mathjax import _convert_dollar_to_mathjax
   print(repr(_convert_dollar_to_mathjax(open('/tmp/field.html').read())))
   "
   ```

   Note: `pytest -k` filters by substring — `-k oiint` skips `test_oiiint_*`
   (`oiint` is not a substring of `oiiint`). Run the whole suite to be sure.

4. **Fix test-first.** Add tests to `auto_mathjax/tests/test_convert.py` next
   to the nearest neighbor (macro preamble tests under "Macro injection",
   conversion tests by category). Mirror the existing style
   (`_convert_dollar_to_mathjax(html)` in, assert exact substrings out, plus an
   idempotent-on-rerun test for macro preambles) and confirm red before editing
   `__init__.py`.

5. **Minimal fix, then verify from the repo root:**

   ```sh
   make test-addon ADDON=auto_mathjax
   make typecheck-addon ADDON=auto_mathjax
   ```

6. **Apply the fix to the affected card(s).** Repairs and conversions run only
   at conversion time, so stored corruption stays broken until rewritten. Use
   the bundled AnkiConnect script (Anki running with AnkiConnect on
   `localhost:8765`) — `--dry-run` first to review diffs, apply, then re-run
   without `--dry-run` to confirm every note reports "unchanged" (in-vivo
   idempotency):

   ```sh
   python3 .agents/skills/debug-mathjax/scripts/repair_notes.py --dry-run <note-id> [...]
   python3 .agents/skills/debug-mathjax/scripts/repair_notes.py <note-id> [...]
   ```

   Note IDs come from the step-1 dump header (`=== note <id>: N fields ===`).
   Pass every note diagnosed in the session; the script writes back only
   changed fields. Hands-off corruption classes (whitespace-flanked
   span-placeholder segments, one-off reconstructions) convert to themselves
   and report "unchanged" — those cards need a manual byte-level repair with
   the exact intended bytes stated in the report.

7. **Report with rendering caveats.** Mocked tests cannot observe the rendered
   page, so leave visual judgment to the user. For emulated glyphs (overlay
   macros like `\mkern-14mu`), state the tuning knob for the user to eyeball.
   List which notes the repair script updated and which need a manual pass.
   Remind the user to reload the add-on; for cards outside the AnkiConnect
   repair, re-click the autoMathJax button since macro preambles are injected
   at conversion time.
