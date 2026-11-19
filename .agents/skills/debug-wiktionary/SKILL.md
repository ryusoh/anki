---
name: debug-wiktionary
description: Debug an auto_wiktionary word-fetch failure for a specific word (Japanese or English) — fetch the live Wiktionary page, trace the parse/redirect pipeline, TDD a fix with a real-HTML fixture. Use when a word lookup errors, returns nothing, or shows a bad redirect.
argument-hint: "<word that failed>"
---

# Debug an auto_wiktionary fetch failure

The word to debug is `{{args}}`.

Work the pipeline in execution order and pull the real HTML first.

1. **Detect the language and fetch the live page.** The add-on routes Japanese
   text to `ja.wiktionary` and everything else to `en.wiktionary`
   (`detect_language` in `auto_wiktionary/utils.py`). Import root `conftest`
   first to stub `aqt`/`anki`:

   ```sh
   LANG=$(.venv/bin/python3 -c "import conftest; from auto_wiktionary.utils import detect_language; print(detect_language('{{args}}'))")
   curl -s -L "https://${LANG}.wiktionary.org/w/api.php?action=parse&page=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' '{{args}}')&prop=text&format=json&formatversion=2" | python3 -c "import json,sys; print(json.load(sys.stdin).get('parse',{}).get('text','NOT FOUND')[:3000])"
   ```

   `NOT FOUND` (or an empty `parse`) means the word genuinely has no page — the
   "not found / Did you mean" path is working as designed; stop and tell the
   user.

2. **Trace the code path.** Read `auto_wiktionary/utils.py` and
   `auto_wiktionary/__init__.py`. The flow is: `clean_html_text` →
   `detect_language` → `fetch_wiktionary_html` → `detect_kanji_redirect`
   (kanji-notation/`参照` redirects — `ja` only) → `parse_wiktionary_html` →
   `inject_redirect_pronunciation`. Failure families differ by language:
   - **ja:** usually a new wrinkle in redirect-notice markup. Already pinned in
     `auto_wiktionary/tests/test_kanji_redirect.py`: `Xの漢字表記。`,
     `X　参照`, `「X」を参照。`, `"X"参照`, `<ul>` vs `<ol>`, multi-reading
     lists, qualifier prefixes like `(麻雀) 「X」を参照。`.
   - **en:** usually page-structure changes breaking `parse_wiktionary_html`
     (`_filter_language_sections` / `_remove_unwanted_tags`) or the fetch
     itself (redirect detection applies only to `ja`).

3. **Reproduce the exact bad value** against the live HTML (`import conftest`
   first):

   ```sh
   .venv/bin/python3 -c "
   import conftest
   from auto_wiktionary.utils import detect_kanji_redirect, parse_wiktionary_html
   html = open('/tmp/page.html').read()  # save the step-1 output here
   print(detect_kanji_redirect(html))    # ja: is the extracted reading corrupted?
   print(parse_wiktionary_html(html, lang='$LANG')[:500])
   "
   ```

   A corrupted reading (e.g. `(麻雀) 「テンパイ` for 聴牌) 404s and surfaces as
   "Could not fetch redirected reading …". For `en` words, empty/wrong
   `parse_wiktionary_html` output is the tell.

4. **Fix test-first.** Add fixtures to the test file matching the failure
   family — redirect extraction → `auto_wiktionary/tests/test_kanji_redirect.py`;
   parse/API behaviour → `auto_wiktionary/tests/test_wiktionary_api.py`. Match
   the house style: a comment noting the new wrinkle, a trimmed real-HTML
   fixture, a unit test for the broken stage, and a full-flow test asserting
   the junk text (e.g. `を参照`) is gone and the real definition is present.
   Confirm red before editing `utils.py`.

5. **Minimal fix in `auto_wiktionary/utils.py`** — extend the existing
   regex/pattern cleanly and confirm the full suite goes green.

6. **Verify from the repo root:**

   ```sh
   make test-addon ADDON=auto_wiktionary
   make typecheck-addon ADDON=auto_wiktionary
   ```

7. **Report plainly:** one-line root cause, the fix, pasted test/gate output,
   and a reminder to reload the add-on in Anki and retry the word (mocked tests
   cannot prove real-Anki behaviour).
