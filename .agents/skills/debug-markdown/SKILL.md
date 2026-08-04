---
name: debug-markdown
description: Debug an auto_markdown conversion failure — fenced code block formatting, line breaks, HTML/tag wrapping (<code>, <span>, <div>), MathJax passthrough, tables, list items, or idempotency bugs. Extract the real stored field HTML, classify the failure stage, TDD a fix with a real-HTML fixture. Use when a card's markdown field fails to render properly or breaks formatting.
argument-hint: "<card snippet, raw HTML, or symptom>"
---

# Debug an auto_markdown conversion failure

The problem to debug is `{{args}}`.

Do not guess the field format — pull the real field HTML and classify the
failure category before touching code.

1. **Get the real stored field HTML.** Never debug against an imagined format:

   ```sh
   python3 tools/dump_field.py --contains '<some text from the card>'
   ```

2. **Classify the failure category in `auto_markdown/core.py`:**
   - **Code Block & Tag Wrapping** — code fence lines or inner lines wrapped in
     HTML tags (`<code>`, `<span>`, `<div>`), nested `<code>` tags inside
     `<pre>`, glued fences (`</ul>```assembly`), or missing language
     identifiers (`_parse_code_blocks`, `_split_glued_code_fences`,
     `_STRIP_CODE_TAGS_RE`).
   - **Leaf `<div>` Line Normalization** — multi-line fields stored as
     `<div>line</div>` runs instead of `<br>` separators where block markers
     were not recognized (`_normalize_top_level_leaf_div_runs`,
     `_has_block_markdown`).
   - **Inline Formatting & MathJax Passthrough** — backticks, bold `**`,
     italic `*`, or MathJax expressions (`\(...\)`, `\[...\]`, `<anki-mathjax>`)
     mangled or double-wrapped (`_convert_inline`, `_MATHJAX_BLOCKS_RE`,
     `_CODE_RE`).
   - **List / Table / Blockquote Grouping & Spacing** — `<ul>`/`<ol>` line
     assembly, table cell alignment parsing (`_parse_tables`), blockquote
     styling (`_assemble`), or redundant `<br>` spacing (`_clean_spacings`).
   - **Legacy HTML Upgrade & Idempotency** — unstyled `<pre>`, `<table>`, or
     `<blockquote>` elements failing to upgrade, or double conversion altering
     rendered HTML (`_upgrade_existing_*`).

3. **Reproduce in Python** against the dumped HTML. Import `conftest` first to
   stub `aqt`/`anki` so the package imports outside pytest:

   ```sh
   .venv/bin/python3 -c "
   import conftest
   from auto_markdown.core import convert_markdown_field
   html = open('/tmp/field.html').read()
   print('OUT:\n', convert_markdown_field(html))
   "
   ```

4. **Fix test-first leveraging the `tdd` skill (repo hard rule).** Add tests to
   `auto_markdown/tests/test_convert.py` in the matching category section with
   a realistic HTML fixture. Confirm the test fails (**red**) before editing
   `auto_markdown/core.py`.

5. **Minimal fix in `auto_markdown/core.py`.** Extend the pipeline helpers, and
   ensure all tests pass (**green**).

6. **Verify with the repo gate from repo root:**

   ```sh
   make test-addon ADDON=auto_markdown
   make typecheck-addon ADDON=auto_markdown
   ```

7. **Sync commands and verify workflow files:**

   ```sh
   make fmt
   python3 tools/sync_commands.py
   make sync-check
   make precommit SKIP=1
   ```

8. **Report plainly**: root cause (one line), the fix, pasted verification
   output, and remind the user to reload the add-on in Anki and re-trigger
   `auto_markdown` on the field.
