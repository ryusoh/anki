---
description: Debug an auto_wiktionary word-fetch failure for a specific word (Japanese or English) — fetch the live Wiktionary page, trace the parse/redirect pipeline, TDD a fix with a real-HTML fixture. Use when a word lookup errors, returns nothing, or shows a bad redirect.
argument-hint: "<word that failed>"
---

# Debug an auto_wiktionary fetch failure

The word to debug is `$ARGUMENTS`.

Work the pipeline in the order the code runs it. Do not guess the page
format — pull the real HTML first.

1. **Detect the language and fetch the live page.** The add-on routes
   Japanese text to ja.wiktionary and everything else to en.wiktionary
   (`detect_language` in `auto_wiktionary/utils.py`). Use the add-on's own
   detector so you're debugging the same branch the code takes — the root
   `conftest.py` stubs `aqt`/`anki`, so importing it first makes the
   package importable outside pytest:

   ```sh
   LANG=$(.venv/bin/python3 -c "import conftest; from auto_wiktionary.utils import detect_language; print(detect_language('$ARGUMENTS'))")
   curl -s -L "https://${LANG}.wiktionary.org/w/api.php?action=parse&page=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' '$ARGUMENTS')&prop=text&format=json&formatversion=2" | python3 -c "import json,sys; print(json.load(sys.stdin).get('parse',{}).get('text','NOT FOUND')[:3000])"
   ```

   `NOT FOUND` (or an empty `parse`) means the word genuinely has no page —
   the add-on's "not found / Did you mean" path is working as designed; stop
   there and tell the user.

2. **Trace the code path.** Read `auto_wiktionary/utils.py` and
   `auto_wiktionary/__init__.py`. The flow is: `clean_html_text` →
   `detect_language` → `fetch_wiktionary_html` → `detect_kanji_redirect`
   (follows kanji-notation/`参照` redirects — ja only) → `parse_wiktionary_html`
   → `inject_redirect_pronunciation`. Compare the live HTML against what each
   regex/selector expects. Failure families differ by language:
   - **ja**: usually a _new wrinkle_ in redirect-notice markup. Already
     pinned in `auto_wiktionary/tests/test_kanji_redirect.py`:
     `Xの漢字表記。`, `X　参照`, `「X」を参照。`, `"X"参照`, `<ul>` vs `<ol>`,
     multi-reading lists, qualifier prefixes like `(麻雀) 「X」を参照。`.
   - **en**: usually page-structure changes breaking `parse_wiktionary_html`
     (section filtering in `_filter_language_sections` / `_remove_unwanted_tags`)
     or the fetch itself — redirect detection does not apply to English.

3. **Reproduce the exact bad value.** Run the failing stage against the live
   HTML and print what it produces (again, `import conftest` first):

   ```sh
   .venv/bin/python3 -c "
   import conftest
   from auto_wiktionary.utils import detect_kanji_redirect, parse_wiktionary_html
   html = open('/tmp/page.html').read()  # save the step-1 output here
   print(detect_kanji_redirect(html))    # ja: is the extracted reading corrupted?
   print(parse_wiktionary_html(html, lang='$LANG')[:500])
   "
   ```

   A corrupted reading (e.g. `(麻雀) 「テンパイ` for 聴牌) is the smoking
   gun — it 404s and surfaces as "Could not fetch redirected reading …".
   For en words, an empty/wrong `parse_wiktionary_html` output is the tell.

4. **Fix test-first (this is a hard repo rule — changed behaviour needs a
   failing test).** Add fixtures to the test file matching the failure family
   — redirect extraction → `auto_wiktionary/tests/test_kanji_redirect.py`;
   parse/API behaviour → `auto_wiktionary/tests/test_wiktionary_api.py`.
   Follow the existing house style: a comment noting the _new wrinkle_, a
   trimmed real-HTML fixture, a unit test for the broken stage, and a
   full-flow test asserting the junk text (e.g. `を参照`) is gone and the
   real definition is present. Confirm the new tests are **red** before
   touching `utils.py`.

5. **Minimal fix in `auto_wiktionary/utils.py`** — extend the existing
   regex/pattern, don't fork the logic. Confirm the new tests go green and
   the whole suite stays green.

6. **Verify with the repo gate, from the repo root:**

   ```sh
   make test-addon ADDON=auto_wiktionary
   make typecheck-addon ADDON=auto_wiktionary
   ```

7. **Report plainly**: root cause (one line), the fix, pasted test/gate
   output, and remind the user to reload the add-on in Anki and retry the
   word — mocked tests can't prove real-Anki behaviour.
