---
description: Debug an auto_markdown conversion failure — fenced code block formatting, line breaks, HTML/tag wrapping (<code>, <span>, <div>), MathJax passthrough, tables, list items, or idempotency bugs. Extract the real stored field HTML, classify the failure stage, TDD a fix with a real-HTML fixture. Use when a card's markdown field fails to render properly or breaks formatting.
argument-hint: "<card snippet, raw HTML, or symptom>"
---

# Debug an auto_markdown conversion failure

The problem to debug is `$ARGUMENTS`.

Pull the real stored field HTML and classify the failure category before
touching code.

1. **Get the real stored field HTML:**

   ```sh
   python3 tools/dump_field.py --contains '<some text from the card>'
   # long fields truncate in terminal output — write full bytes to files:
   python3 tools/dump_field.py --contains '<some text>' --out /tmp/fields
   ```

2. **Classify the failure category in `auto_markdown/core.py`:**
   - **Code Block & Tag Wrapping** — code fence lines or inner lines wrapped in
     HTML tags (`<code>`, `<span>`, `<div>`), nested `<code>` tags inside
     `<pre>`, glued fences (`</ul>```assembly`, ` ```<ol>… `, or
     separated by `&nbsp;` entities instead of whitespace), or missing language
     identifiers (`_parse_code_blocks`, `_split_glued_code_fences`,
     `_CODE_FENCE_RE`, `_STRIP_CODE_TAGS_RE`).
   - **Leaf `<div>` Line Normalization** — multi-line fields stored as
     `<div>line</div>` runs instead of `<br>` separators where block markers
     were unrecognized (`_normalize_top_level_leaf_div_runs`,
     `_has_block_markdown`).
   - **Inline Formatting & MathJax Passthrough** — backticks, bold `**`,
     italic `*`, or MathJax expressions (`\(...\)`, `\[...\]`,
     `<anki-mathjax>`) mangled or double-wrapped (`_convert_inline`,
     `_MATHJAX_BLOCKS_RE`, `_CODE_RE`).
   - **List / Table / Blockquote Grouping & Spacing** — `<ul>`/`<ol>` line
     assembly, table cell alignment parsing (`_parse_tables`), blockquote
     styling (`_assemble`), or redundant `<br>` spacing (`_clean_spacings`).
   - **Legacy HTML Upgrade & Idempotency** — unstyled `<pre>`, `<table>`, or
     `<blockquote>` elements failing to upgrade, or double conversion altering
     rendered HTML (`_upgrade_existing_*`).

3. **Reproduce in Python** against the dumped HTML (import `conftest` first to
   stub `aqt`/`anki`):

   ```sh
   .venv/bin/python3 -c "
   import conftest
   from auto_markdown.core import convert_markdown_field
   html = open('/tmp/field.html').read()
   print('OUT:\n', convert_markdown_field(html))
   "
   ```

4. **Fix test-first (`/tdd`).** Add tests to
   `auto_markdown/tests/test_convert.py` in the matching category section with
   a realistic HTML fixture and confirm they fail before editing
   `auto_markdown/core.py`. When the bug already reached a stored field, add a
   second test converting the **broken intermediate the buggy code wrote** —
   users re-trigger conversion on that exact state, so a loosened check must
   handle a prior partial pass cleanly.

5. **Minimal fix in `auto_markdown/core.py`.** Extend the pipeline helpers and
   confirm all tests go green.

6. **Harden against the whole collection** — sweep the fixed transform over
   every field and review the diffs before shipping:

   ```sh
   python3 tools/sweep_transform.py auto_markdown.core:convert_markdown_field --limit 20
   ```

   Fix every `!! NOT IDEMPOTENT` or `!! transform raised` line via step 4, and
   spot-review printed diffs so only intended changes appear (compare against a
   pre-change sweep when unsure).

7. **Verify from the repo root:**

   ```sh
   make test-addon ADDON=auto_markdown
   make typecheck-addon ADDON=auto_markdown
   make precommit SKIP=1
   ```

8. **Repair the tested stored field after the safe dry run.** Once the sweep
   and gates are green, repair the card that demonstrated the bug (whether
   mangled or left unconverted):
   - Convert the dumped pristine source with the fixed code, review the exact
     old/new HTML diff, and keep the dumped original for rollback.
   - Write only the dumped note ID and field index through AnkiConnect
     `updateNoteFields` (leave other fields untouched unless asked), then
     verify with `notesInfo` and a fresh dump (see "Repairing a mangled field"
     in `docs/creating-an-addon.md`; Anki must be running).
   - If AnkiConnect is unavailable or the write cannot be verified, report
     plainly that the stored card was left unrepaired.

9. **Report plainly:** one-line root cause, the fix, pasted verification
   output, whether the tested card was repaired, and a reminder to reload the
   add-on in Anki.
