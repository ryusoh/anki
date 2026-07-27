# auto_itaigi — design spec (SDD) for issue #404

| Field  | Value                                                                  |
| ------ | ---------------------------------------------------------------------- |
| Issue  | #404 `feat: auto itaigi`                                               |
| Status | Design complete, verified against live API 2026-07-27; no code written |
| Model  | `auto_wiktionary/` (port) + `zdict`'s `itaigi.py` (API reference)      |
| Method | TDD (red → green), see §9 for the ordered steps                        |

New add-on `auto_itaigi/`: an editor toolbar button that looks up the selected
text (or Front field) on **itaigi.tw** (Taiwanese Hokkien dictionary) and
populates the Back field with three lines:

1. Tâi-lô romanization, e.g. `han-tsî/han-tsû`
2. Mandarin equivalents, e.g. `華語：蕃薯 甘薯 地瓜`
3. `[sound:itaigi_<slug>.mp3]` — a downloaded pronunciation MP3

## 1. Scope and diff prediction (acceptance criterion)

Source changes **only** inside a new directory `auto_itaigi/`:

```
auto_itaigi/
├── __init__.py          # editor button + flow wiring (thin; aqt-only)
├── utils.py             # all domain logic (pure, testable)
├── proxy_fallback.py    # vendored BYTE-IDENTICAL copy from auto_wiktionary/
├── icon.png             # copy of auto_wiktionary/icon.png (placeholder)
├── manifest.json        # {"package": "auto_itaigi", "name": "Auto iTaigi"}
├── meta.json            # copy auto_wiktionary/meta.json, change "name" only
└── tests/               # test_parse.py, test_fetch.py, test_audio.py,
                         # test_merge.py, test_init.py
```

- `requirements.txt` **MUST NOT** change — implementation is stdlib-only
  (`json`, `urllib.request`, `urllib.parse`, `re`, `unicodedata`). No
  `requests`, no `beautifulsoup4` (the itaigi API returns JSON, not HTML).
- No edits to any other add-on, `Makefile`, `pyproject.toml`, or root
  `conftest.py`. Verify with `git status` / `git diff --stat` at the end:
  everything outside `auto_itaigi/` MUST have zero diff.
- Root `tests/test_proxy_fallback_sync.py` pins all vendored
  `proxy_fallback.py` copies in sync. Copying `auto_wiktionary/proxy_fallback.py`
  verbatim keeps it green; if that test enumerates copies explicitly, follow
  its existing pattern — re-run it to confirm (`python3 -m pytest tests/test_proxy_fallback_sync.py -q`).

## 2. Parity with auto_wiktionary — ported / cut surface

| auto_wiktionary surface                                                        | Status in auto_itaigi                                                                                                                                        |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Editor button via `gui_hooks.editor_did_init_buttons`                          | **Ported** — identical wiring, new command name `autoItaigi`                                                                                                 |
| Selection → Front-field fallback, `editor.saveNow` flush                       | **Ported** — identical                                                                                                                                       |
| Case-insensitive `front`/`back` field lookup                                   | **Ported** — identical                                                                                                                                       |
| stdlib `urllib` + `urlopen_with_proxy_fallback`, 5s timeout, custom User-Agent | **Ported** — UA string `AnkiAutoItaigi/1.0`                                                                                                                  |
| Error contract (`""` not-found / `"Error: …"`), `tooltip` feedback             | **Ported** — not-found is detected in JSON instead of via HTTP 404, see §4                                                                                   |
| Merge into Back (empty → replace, else prepend + `<br>`)                       | **Ported** — simplified, see §6                                                                                                                              |
| Conditional `note.flush()` (skip in addMode), `loadNoteKeepingFocus()`         | **Ported** — identical                                                                                                                                       |
| Language detection (`detect_language`)                                         | **Cut** — query is always Hanji; single endpoint                                                                                                             |
| BeautifulSoup HTML parsing, section filtering                                  | **Cut** — response is JSON, parsed with stdlib `json`                                                                                                        |
| Kanji-redirect detection/follow                                                | **Cut** — no equivalent concept in itaigi                                                                                                                    |
| opensearch "Did you mean" candidates                                           | **Partial** — general suggestions are still ignored, but an exact-match `其他建議` entry (`文本資料 == query`) is used when the main `列表` is empty, see §5 |
| **Audio MP3 download + `[sound:]` line**                                       | **New** — auto_wiktionary strips audio; designed fresh in §7                                                                                                 |

## 3. The itaigi API (verified live 2026-07-27)

Lookup endpoint (GET, JSON; no auth, no required headers, no documented rate
limit; verified with plain curl):

```
https://itaigi.tw/平臺項目列表/揣列表?關鍵字=<word>
```

Captured real response for `番薯` (verbatim, formatted — **this is the test
fixture**, see §9 step 2):

```json
{
  "列表": [
    {
      "外語項目編號": "75162",
      "外語資料": "蕃薯",
      "新詞文本": [
        {
          "新詞文本項目編號": "75163",
          "文本資料": "蕃薯",
          "音標資料": "han-tsî/han-tsû",
          "貢獻者": "台文華文線頂辭典",
          "按呢講好": 34,
          "按呢無好": 20,
          "按呢講的外語列表": [
            { "外語項目編號": 75162, "外語資料": "蕃薯" },
            { "外語項目編號": 75159, "外語資料": "甘薯" },
            { "外語項目編號": 9448, "外語資料": "地瓜" }
          ]
        },
        {
          "新詞文本項目編號": "96764",
          "文本資料": "金薯",
          "音標資料": "kim-tsî/kim-tsû",
          "按呢講的外語列表": [{ "外語項目編號": 75162, "外語資料": "蕃薯" }]
        }
      ]
    }
  ],
  "其他建議": [
    { "文本資料": "炕窯", "音標資料": "khòng-iô" },
    { "文本資料": "炰蕃薯", "音標資料": "pû-han-tsî/pû-huan-tsû" }
  ]
}
```

Field semantics (confirmed against `i3thuan5/itaigi` frontend source and zdict):

- `列表[0].新詞文本` — Taiwanese entries for the query. **Order is not stable**
  (zdict issue-452 sorts before comparing). Each entry has:
  - `文本資料` — Hanji form of the Taiwanese word.
  - `音標資料` — Tâi-lô romanization; dialect variants **already joined by `/`**
    (e.g. `han-tsî/han-tsû`). NFC precomposed tone marks.
  - `按呢講好` / `按呢無好` — up/down votes (may be absent).
  - `按呢講的外語列表` — Mandarin equivalents as `{外語資料: "…"}` objects.
- **Not-found** is HTTP 200 with `{"列表": [], "其他建議": []}` — there is no 404. Verified live with a nonsense keyword.
- The detail endpoint (`平臺項目/看詳細內容?平臺項目編號=…`) contains provenance
  metadata only — **no MP3 URL exists in any API JSON**. Audio comes from a
  separate TTS service, §7.

### URL-encoding gotcha (MUST)

`urllib.request` refuses non-ASCII URLs (`UnicodeEncodeError` from
`http.client`) — the path itself contains Chinese characters, so quoting only
the query word is **not** enough. Build the URL as:

```python
from urllib.parse import quote, urlencode

def itaigi_lookup_url(word: str) -> str:
    path = quote("平臺項目列表/揣列表")  # quote keeps "/" safe by default
    return f"https://itaigi.tw/{path}?{urlencode({'關鍵字': word})}"
```

A test MUST pin that the produced URL contains `%`-escapes and no raw
non-ASCII bytes (`itaigi_lookup_url("番薯").isascii()` is `True`).

## 4. Fetch contract (`utils.py`)

Mirror `fetch_wiktionary_html`'s contract exactly:

```python
def fetch_itaigi_json(word: str) -> str:
    """Return the raw response body (str).

    - HTTP 404 (should not happen, but keep parity) -> ""
    - other HTTPError                              -> "Error: {code}"
    - URLError / network failure                   -> "Error: Network connection failed."
    - anything else                                -> "Error: {e}"
    """
```

- Request: `urllib.request.Request(itaigi_lookup_url(word), headers={"User-Agent": "AnkiAutoItaigi/1.0 (https://github.com/ryusoh/anki)"})`
- Transport: `urlopen_with_proxy_fallback(req, timeout=5)` from the vendored
  `proxy_fallback.py`. One attempt, no retries.
- Decode: `response.read().decode("utf-8")`.
- Not-found is **not** decided here — it is decided by the parser (empty
  `列表`), §5. A 200 with an empty list returns the body; the flow layer
  tooltips "not found".

## 5. Parser (`utils.py`) — reference implementation

This is the trickiest logic; implement it essentially as written (adjust only
to satisfy lint). Expected values in §8 come from the fixture, not from this
code, so tests can genuinely disagree with it.

```python
from __future__ import annotations

import json


def _extract_entry(entry: dict) -> tuple[str, list[str]]:
    """Extract (tailo, mandarin_words) from a single entry."""
    tailo = (entry.get("音標資料") or "").strip()
    mandarin: list[str] = []
    for item in entry.get("按呢講的外語列表") or []:
        w = (item.get("外語資料") or "").strip()
        if w and w not in mandarin:
            mandarin.append(w)
    return tailo, mandarin


def parse_itaigi_json(body: str, query: str) -> tuple[str, list[str]] | None:
    """Parse a 揣列表 response body.

    Returns (tailo, mandarin_words) for the chosen entry, or None when the
    word is not found (empty 列表 / empty 新詞文本 / unparseable JSON).
    `tailo` may be "" and `mandarin_words` may be [] — that is not not-found.

    When the main 列表 is empty but 其他建議 contains an entry whose 文本資料
    exactly matches the query, that suggestion is treated as the result. This
    mirrors the website behavior for words like 腿庫.
    """
    try:
        data = json.loads(body)
    except ValueError:
        return None

    results = data.get("列表") or []
    if results:
        texts = results[0].get("新詞文本") or []
        if texts:

            def votes(entry: dict) -> int:
                return entry.get("按呢講好") or 0

            exact = [t for t in texts if t.get("文本資料") == query]
            chosen = max(exact or texts, key=votes)
            return _extract_entry(chosen)

    # Fallback: some queries (e.g. 腿庫) return the entry only under 其他建議.
    suggestions = data.get("其他建議") or []
    for suggestion in suggestions:
        if suggestion.get("文本資料") == query:
            return _extract_entry(suggestion)

    return None
```

Entry-selection rule (MUST): among `新詞文本`, prefer entries whose
`文本資料` equals the query; within that subset (or all entries when no exact
match), pick the highest `按呢講好` (`max` keeps the first on ties). For the
番薯 fixture: no entry has `文本資料 == "番薯"` （蕃薯 ≠ 番薯）, so the
highest-voted entry `75163` wins → `han-tsî/han-tsû`, `["蕃薯", "甘薯", "地瓜"]`.

## 6. Formatting and merge (`utils.py`)

```python
def format_itaigi_result(tailo: str, mandarin: list[str], sound_name: str | None) -> str | None:
    """Build the Back-field HTML. Returns None when there is nothing to show."""
    lines: list[str] = []
    if tailo:
        lines.append(tailo)
    if mandarin:
        lines.append("華語：" + " ".join(mandarin))
    if sound_name:
        lines.append(f"[sound:{sound_name}]")
    return "<br>".join(lines) if lines else None


_EMPTY_BACKS = frozenset(("", "<br>", "<br/>", "<br />", "<div><br></div>"))


def merge_itaigi_result(current_back: str, new_html: str) -> str:
    """Empty-ish Back -> replace; otherwise prepend with <br> (prepend, like auto_wiktionary)."""
    if current_back.strip().lower() in _EMPTY_BACKS:
        return new_html
    return f"{new_html}<br>{current_back}"
```

Line breaks MUST be `<br>` — literal `\n` is whitespace in field HTML (see
`docs/creating-an-addon.md` "Field HTML reality"). `[sound:name.mp3]` is plain
text in the field; Anki renders it as a play button.

For the 番薯 fixture with audio this produces exactly:

```
han-tsî/han-tsû<br>華語：蕃薯 甘薯 地瓜<br>[sound:itaigi_han-tsi.mp3]
```

(The issue's example `華語：甘薯 番薯 地瓜 甘藷` is an older snapshot of the
crowd-sourced data; the live API returns `蕃薯 甘薯 地瓜`. Tests pin the
fixture, never live values — see DO-NOT §11.)

## 7. Audio (`utils.py` + one `mw` touchpoint)

The itaigi website plays studio recordings via a static id table, and falls
back to TTS. **Only the TTS path is implemented** (Path A needs a
thousand-entry mapping table vendored from the frontend repo — cut for KISS):

```
https://hapsing.itaigi.tw/bangtsam?taibun=<encoded romanization>
```

Verified live 2026-07-27: `taibun=han-ts%C3%AE` → HTTP 200, 3 033-byte valid
MPEG layer III file. `Content-Type` is `application/octet-stream` — do not
trust the header; validate by magic bytes (MP3 frames start with `ID3` or
`\xff\xfb`/`\xff\xf3`/`\xff\xf2`).

Reference implementation:

```python
import re
import unicodedata
from urllib.parse import quote
from urllib.request import Request

from .proxy_fallback import urlopen_with_proxy_fallback


def hapsing_url(tailo: str) -> str:
    # The itaigi frontend replaces the FIRST "/" with " 。 " before encoding;
    # a single variant also works. Mirror the frontend.
    taibun = tailo.replace("/", " 。 ", 1)
    return f"https://hapsing.itaigi.tw/bangtsam?taibun={quote(taibun)}"


def media_filename(tailo: str) -> str:
    """itaigi_<ascii-slug of first variant>.mp3 — han-tsî/han-tsû -> itaigi_han-tsi.mp3"""
    first = tailo.split("/")[0]
    ascii_form = unicodedata.normalize("NFKD", first).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9-]+", "-", ascii_form.lower()).strip("-")
    return f"itaigi_{slug or 'audio'}.mp3"


def download_audio(tailo: str) -> bytes | None:
    """Return MP3 bytes, or None on any failure (caller MUST treat None as 'skip audio line')."""
    try:
        req = Request(hapsing_url(tailo), headers={"User-Agent": "AnkiAutoItaigi/1.0 (https://github.com/ryusoh/anki)"})
        with urlopen_with_proxy_fallback(req, timeout=10) as resp:
            data = resp.read()
    except Exception:
        return None
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return data
    return None
```

Writing into the collection (the only `mw` access in the add-on — MUST be a
function-local lookup, never module-level, per AGENTS.md):

```python
def save_audio_to_media(tailo: str) -> str | None:
    """Download + store. Returns the media filename for [sound:], or None."""
    data = download_audio(tailo)
    if data is None:
        return None
    fname = media_filename(tailo)
    try:
        from aqt import mw  # function-local: aqt.mw is None at import time

        mw.col.media.write_data(fname, data)
    except Exception:
        return None
    return fname
```

Audio failure MUST NOT abort the text write — the flow writes lines 1–2 and
tooltips that audio failed.

## 8. Behavior matrix (worked examples — these become the tests)

All expected values are hand-derived from the §3 fixture / the rules above, not
from running the implementation.

| #   | Input                                                                                   | Expected                                                                                        |
| --- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 1   | fixture body (§3), query `番薯`                                                         | `("han-tsî/han-tsû", ["蕃薯", "甘薯", "地瓜"])` — no exact `文本資料` match, highest votes wins |
| 2   | synthetic: two entries, exact `文本資料 == query` has **fewer** votes                   | exact-match entry chosen (selection rule, not votes-only)                                       |
| 3   | synthetic: `按呢講的外語列表` with duplicate `外語資料` values                          | duplicates removed, first-occurrence order kept                                                 |
| 4   | synthetic: entry without `按呢講的外語列表` key                                         | `("tailo", [])` — no crash, no 華語 line                                                        |
| 5   | synthetic: entry with missing/empty `音標資料`                                          | `("", [...])` — line 1 and audio skipped downstream                                             |
| 6   | `{"列表": [], "其他建議": []}`                                                          | `None`                                                                                          |
| 7   | `{"列表": [{"新詞文本": []}]}`                                                          | `None`                                                                                          |
| 8   | `"not json"`                                                                            | `None`                                                                                          |
| 9   | `format_itaigi_result("han-tsî/han-tsû", ["蕃薯","甘薯","地瓜"], "itaigi_han-tsi.mp3")` | `han-tsî/han-tsû<br>華語：蕃薯 甘薯 地瓜<br>[sound:itaigi_han-tsi.mp3]`                         |
| 10  | `format_itaigi_result("", [], None)`                                                    | `None`                                                                                          |
| 11  | `format_itaigi_result("han-tsî", [], None)`                                             | `han-tsî` (no 華語： prefix with empty list)                                                    |
| 12  | `media_filename("han-tsî/han-tsû")`                                                     | `itaigi_han-tsi.mp3`                                                                            |
| 13  | `media_filename("pû-han-tsî/pû-huan-tsû")`                                              | `itaigi_pu-han-tsi.mp3`                                                                         |
| 14  | `media_filename("///")` → empty slug                                                    | `itaigi_audio.mp3`                                                                              |
| 15  | `hapsing_url("han-tsî/han-tsû")`                                                        | first `/` → `。`, fully percent-encoded, ASCII-only URL                                         |
| 16  | `merge_itaigi_result("", html)` / `("<br>", html)` / `("<div><br></div>", html)`        | `html` (replace)                                                                                |
| 17  | `merge_itaigi_result("existing", html)`                                                 | `html + "<br>existing"` (prepend)                                                               |
| 18  | `download_audio` returning non-MP3 bytes (e.g. `<html>…`)                               | `None` (magic-byte sniff rejects)                                                               |
| 19  | `itaigi_lookup_url("番薯").isascii()`                                                   | `True` (URL-encoding gotcha, §3)                                                                |
| 20  | `{"列表": [], "其他建議": [{"文本資料": "腿庫", "音標資料": "thuí-khòo", …}]}`          | `("thuí-khòo", ["蹄膀", "肘子"])` — exact-match suggestion used when main list is empty         |

End-to-end flow expectations (mocked fetch + mocked media):

- 番薯 fixture + audio OK → Back becomes the §6 three-line string; tooltip
  `Added '番薯' from itaigi to Back field.` (exact wording is the
  implementer's choice; tests assert the field, not the tooltip text).
- Not-found (`列表` empty) → Back unchanged, tooltip shown, **no** media call.
- Audio `None` → Back gets lines 1–2 only; no exception propagates.
- No `Back` field in note type → tooltip, nothing written.

## 9. Ordered TDD steps (red → green, one slice at a time)

Run everything **from the repo root** (root `conftest.py` mocks `aqt`/`anki` —
running pytest inside `auto_itaigi/` fails to import them). Use
`python3 -m pytest auto_itaigi/tests/ -q` for the tight loop, re-verify with
`.venv/bin/python3 -m pytest auto_itaigi/tests/ -q` before finishing.

1. **Scaffold.** Create `auto_itaigi/` with `manifest.json`, `meta.json`
   (copy `auto_wiktionary/meta.json`, set `"name": "Auto iTaigi"`), vendored
   `proxy_fallback.py` (byte-identical copy), `icon.png` (copy of
   `auto_wiktionary/icon.png`), empty `__init__.py`, `utils.py`. Verify:
   `python3 -m pytest tests/test_proxy_fallback_sync.py -q` stays green.
2. **Parser.** `tests/test_parse.py`: embed the §3 fixture as a module-level
   constant; write cases 1–8 of §8 (red) → implement `parse_itaigi_json`
   (green).
3. **Formatting/merge.** `tests/test_merge.py`: cases 9–11, 16–17 (red) →
   implement `format_itaigi_result`, `merge_itaigi_result` (green).
4. **URLs + filename.** `tests/test_audio.py` part 1: cases 12–15, 19 (red) →
   implement `itaigi_lookup_url`, `hapsing_url`, `media_filename` (green).
5. **Fetch.** `tests/test_fetch.py`: mock `auto_itaigi.utils.urlopen_with_proxy_fallback`
   (patch at the module namespace, like auto_wiktionary patches
   `urllib.request.urlopen`) returning a `MagicMock` response whose
   `read()` returns the fixture bytes; assert body passthrough, the 404→`""`,
   HTTPError→`"Error: 500"`, URLError→`"Error: Network connection failed."`
   contract (red) → implement `fetch_itaigi_json` (green). No live-network
   test — keep the suite hermetic.
6. **Audio download.** `tests/test_audio.py` part 2: mock the transport to
   return 3 033 bytes starting with `\xff\xfb` → returns bytes; return
   `<html>…` → `None`; raise `OSError` → `None` (case 18). For
   `save_audio_to_media`, mock `aqt.mw` (root conftest already makes `aqt` a
   `MagicMock`; set `mw.col.media.write_data` explicitly) and assert
   `write_data("itaigi_han-tsi.mp3", <bytes>)` called and the filename
   returned; `write_data` raising → `None` (red → green).
7. **Flow wiring.** `__init__.py` + `tests/test_init.py`, mirroring
   `auto_wiktionary/tests/test_init.py`'s pattern (re-mock `aqt.*` in
   `sys.modules` before importing `auto_itaigi`; `MagicMock` editor with
   `note.keys.return_value = ["Front", "Back"]`, `note.fields = ["", ""]`;
   patch `auto_itaigi.fetch_itaigi_json` / `auto_itaigi.save_audio_to_media`
   at the package namespace). Cover the four end-to-end expectations in §8.
   `__init__.py` structure (thin; MUST stay close to auto_wiktionary's):
   - `on_editor_did_init_buttons` → `editor.addButton(ICON_PATH, "autoItaigi", on_auto_itaigi, tip=…)`, append to `buttons`, register on
     `gui_hooks.editor_did_init_buttons`.
   - `on_auto_itaigi(editor)` → `evalWithCallback("window.getSelection().toString()", …)`; empty selection → Front field; always
     `editor.saveNow(callback)` first.
   - `_apply_itaigi(editor, text)`: `clean_html_text` equivalent (strip tags —
     a 5-line local helper with `re.sub(r"<[^>]+>", "", …)` + `html.unescape`
     is enough; do not import from auto_wiktionary — add-ons are
     self-contained per import-linter) → fetch → parse → tooltip+return when
     falsy/`Error:`/None → `save_audio_to_media(tailo)` →
     `format_itaigi_result` → `merge_itaigi_result` → write `fields[back_idx]`
     → `flush()` only when `not editor.addMode` →
     `editor.loadNoteKeepingFocus()` → `tooltip`.
8. **Gate.** `make test-py SUITE=auto_itaigi/tests`, then
   `.venv/bin/python3 -m pytest auto_itaigi/tests/ -q`, then
   `make quality-py` (ruff/black/mypy/bandit/xenon — `from __future__ import annotations`
   first in every module per FA102; `parse_itaigi_json`'s `X | None` syntax is
   fine **only** with that import, Anki 25.02 bundles Python 3.9), then
   `make precommit SKIP=1` fully green.

Known intermediate state: after steps 2–6 the add-on button does nothing
(`__init__.py` still empty) — expected; do not stop there.

## 10. What the mocked suite cannot prove

Per `.agents/skills/tdd` and AGENTS.md: green tests prove logic against mocked
`aqt`, not real Anki. After implementation the user restarts Anki and, in the
editor, selects `番薯` and clicks the button — expecting the §6 three-line
Back and a playable `[sound:]` button. The spec author verified the API and
MP3 endpoints live (§3, §7); the Anki-side wiring is human-verified only.

## 11. DO-NOT list (each with its reason)

- **Do not add `requests`/`beautifulsoup4`** — stdlib `json` suffices;
  `requirements.txt` stays untouched (§1).
- **Do not pass raw Chinese into a `urllib` URL** — `http.client` raises
  `UnicodeEncodeError`; quote path and query (§3, case 19).
- **Do not hard-code live API values in tests beyond the §3 fixture** — the
  data is crowd-sourced and drifts (the issue's own example no longer matches
  the live response). No live-network tests; the suite is hermetic.
- **Do not implement the studio-recording (rackcdn/SoundsMapping) audio
  path** — it requires vendoring a thousand-entry table from the frontend
  repo; the TTS endpoint always works (§7).
- **Do not trust the audio `Content-Type` header** — it is
  `application/octet-stream`; sniff MP3 magic bytes instead (§7, case 18).
- **Do not let audio failure abort the text write** — a TTS outage must not
  lose the lookup result (§7, §8).
- **Do not bind `mw` at module level** — `aqt.mw` is `None` at import time in
  real Anki; function-local lookup only (AGENTS.md, §7).
- **Do not import from `auto_wiktionary`** — add-ons are self-contained;
  `make imports-py` fails on new cross-addon imports. Copy the 5-line HTML
  cleaner instead (§9 step 7).
- **Do not modify the vendored `proxy_fallback.py`** — the sync test pins it
  byte-identical across add-ons.
- **Do not write literal `\n` as line separators in field HTML** — only `<br>`
  renders as a line break in Anki fields (§6).
- **Do not edit anything outside `auto_itaigi/`** — diff-scope acceptance
  criterion (§1).

## 12. Sources

- Issue #404 `feat: auto itaigi` (refs: g0v/itaigi, zdict/zdict).
- Active itaigi repo: `i3thuan5/itaigi` — `tsiantuan/src/後端.jsx` (endpoint
  definitions), `tsiantuan/src/GuanKiann/HuatIm/HapSing.jsx` (TTS audio).
- `zdict/zdict` — `zdict/dictionaries/itaigi.py` (same lookup endpoint,
  empty-`列表` not-found convention, unstable entry order).
- Live `curl` verification 2026-07-27: lookup for `番薯`, nonsense-keyword
  not-found shape, `hapsing.itaigi.tw` MP3 bytes.
- `auto_wiktionary/` — structural model (button wiring, error contract, merge,
  test patterns).
