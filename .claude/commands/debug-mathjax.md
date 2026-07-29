---
description: Debug an auto_mathjax failure — $ conversion wrapping wrong, or MathJax showing red "invalid text" for a command. Classify conversion vs rendering, reproduce on the real field HTML, TDD a fix. Use when a card's math renders wrong or a button click converts wrong.
argument-hint: "<card snippet, LaTeX command, or symptom>"
---

# Debug an auto_mathjax failure

The problem to debug is `$ARGUMENTS`.

Do not guess the field format or the MathJax feature set — pull the real
bytes and classify before touching code.

1. **Get the real stored field HTML.** Never debug against an imagined
   format:

   ```sh
   python3 tools/dump_field.py --contains '<some text from the card>'
   ```

2. **Classify: conversion bug or rendering bug.** This decides everything
   downstream. In the dumped HTML, find the failing formula:
   - **Rendering bug** — the formula is _already wrapped_
     (`<anki-mathjax>…</anki-mathjax>` or `\(…\)` / `\[…\]`) but shows as
     red "invalid text" in Anki. MathJax itself rejects the content. Almost
     always: the command isn't in Anki's bundled MathJax (no esint — so
     `\oiint`, `\oiiint`, `\ointclockwise` etc. fail while amsMath's
     `\oint`, `\iint`, `\iiint` work). The house fix is **not** conversion
     code — it's `CUSTOM_MACROS` + `_inject_macro_defs` in
     `auto_mathjax/__init__.py` (precedents: `lambdabar` via `\unicode`,
     `oiint`/`oiiint` via `\mathop{\bigcirc\mkern-14mu\iint}` overlay).
   - **Conversion bug** — raw `$…$` / bare LaTeX not wrapped, or prose
     wrongly wrapped. The bug lives in the `_convert_dollar_to_mathjax`
     pipeline: `LINE_SPLIT_RE` segmentation, `DOLLAR_PAIR_RE`,
     `_looks_like_math_content` (cashtag/currency guards),
     `_looks_like_bare_latex` + `BARE_LATEX_COMMAND_RE` (whitelist gaps —
     e.g. a bare `\oint` line isn't wrapped because `oint` isn't listed),
     `_wrap_embedded_latex` (CJK lines are deliberately skipped).

3. **Reproduce in Python** against the dumped HTML. Import the root
   `conftest` first — it stubs `aqt`/`anki`, without which importing the
   add-on package outside pytest fails:

   ```sh
   .venv/bin/python3 -c "
   import conftest
   from auto_mathjax import _convert_dollar_to_mathjax
   print(repr(_convert_dollar_to_mathjax(open('/tmp/field.html').read())))
   "
   ```

   Gotcha: `pytest -k` filters by substring — `-k oiint` does **not**
   select `test_oiiint_*` (`oiint` is not a substring of `oiiint`). Run the
   whole suite instead of trusting a narrow filter.

4. **Fix test-first (hard repo rule).** Add tests to
   `auto_mathjax/tests/test_convert.py` next to the nearest neighbor —
   macro preamble tests live in the "Macro injection" section, conversion
   tests are grouped by category. Mirror the existing style
   (`_convert_dollar_to_mathjax(html)` in, assert on exact substrings out,
   plus an idempotent-on-rerun test for macro preambles). Confirm the new
   tests are **red** before touching `__init__.py`.

5. **Minimal fix, then verify from the repo root:**

   ```sh
   make test-addon ADDON=auto_mathjax
   make typecheck-addon ADDON=auto_mathjax
   ```

6. **Report with the rendering caveats.** Mocked tests cannot see the
   rendered page — never claim a glyph "looks right". For emulated glyphs
   (overlay macros like `\mkern-14mu`), state the tuning knob and ask the
   user to eyeball it. Remind the user: reload the add-on, then re-click
   the autoMathJax button on the affected field — macro preambles are only
   injected at conversion time, so existing cards need one button pass.
