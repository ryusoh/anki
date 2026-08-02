from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request

from .proxy_fallback import urlopen_with_proxy_fallback

_chhoetaigi_cache: dict[str, tuple[str, list[str]]] | None = None


def _extract_entry(entry: dict) -> tuple[str, list[str]]:
    """Extract (tailo, mandarin_words) from a single 新詞文本 or 其他建議 entry."""
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


def format_itaigi_result(
    tailo: str, mandarin: list[str], sound_name: str | None
) -> str | None:
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
    """Empty-ish Back -> replace; otherwise prepend with <br>."""
    if current_back.strip().lower() in _EMPTY_BACKS:
        return new_html
    return f"{new_html}<br>{current_back}"


def itaigi_lookup_url(word: str) -> str:
    """Build a fully ASCII itaigi 揣列表 lookup URL."""
    path = quote("平臺項目列表/揣列表")
    return f"https://itaigi.tw/{path}?{urlencode({'關鍵字': word})}"


def hapsing_url(tailo: str) -> str:
    """Build the hapsing TTS URL for a tailo string."""
    taibun = tailo.replace("/", " 。 ", 1)
    return f"https://hapsing.itaigi.tw/bangtsam?taibun={quote(taibun)}"


def media_filename(tailo: str) -> str:
    """itaigi_<ascii-slug of first variant>.mp3."""
    first = tailo.split("/")[0]
    ascii_form = (
        unicodedata.normalize("NFKD", first).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9-]+", "-", ascii_form.lower()).strip("-")
    return f"itaigi_{slug or 'audio'}.mp3"


def download_audio(tailo: str, fallback_url: str | None = None) -> bytes | None:
    """Return MP3 bytes, or None on any failure."""
    urls = [hapsing_url(tailo)]
    if fallback_url:
        urls.append(fallback_url)

    for url in urls:
        try:
            req = Request(
                url,
                headers={
                    "User-Agent": "AnkiAutoItaigi/1.0 (https://github.com/ryusoh/anki)"
                },
            )
            with urlopen_with_proxy_fallback(req, timeout=10) as resp:
                data = resp.read()
            if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
                return data
        except Exception:
            continue
    return None


def save_audio_to_media(
    tailo: str, fallback_url: str | None = None
) -> str | None:
    """Download + store. Returns the media filename for [sound:], or None."""
    data = download_audio(tailo, fallback_url=fallback_url)
    if data is None:
        return None
    fname = media_filename(tailo)
    try:
        from aqt import mw  # function-local: aqt.mw is None at import time

        mw.col.media.write_data(fname, data)
    except Exception:
        return None
    return fname


def fetch_itaigi_json(word: str) -> str:
    """Return the raw response body (str).

    - HTTP 404 (should not happen, but keep parity) -> ""
    - other HTTPError                              -> "Error: {code}"
    - URLError / network failure                   -> "Error: Network connection failed."
    - anything else                                -> "Error: {e}"
    """
    req = Request(
        itaigi_lookup_url(word),
        headers={
            "User-Agent": "AnkiAutoItaigi/1.0 (https://github.com/ryusoh/anki)"
        },
    )
    try:
        with urlopen_with_proxy_fallback(req, timeout=5) as response:
            return response.read().decode("utf-8")
    except HTTPError as e:
        if e.code == 404:
            return ""
        return f"Error: {e.code}"
    except URLError:
        return "Error: Network connection failed."
    except Exception as e:
        return f"Error: {e}"


def fetch_moedict_entry(
    word: str,
) -> tuple[str, list[str], str | None] | None:
    """Fallback 1: Fetch entry from g0v MOEDiCT Minnan API (https://www.moedict.tw/t/{word}.json)."""
    url = f"https://www.moedict.tw/t/{quote(word)}.json"
    req = Request(
        url,
        headers={
            "User-Agent": "AnkiAutoItaigi/1.0 (https://github.com/ryusoh/anki)"
        },
    )
    try:
        with urlopen_with_proxy_fallback(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    heteronyms = data.get("h") or []
    if not heteronyms:
        return None
    h0 = heteronyms[0]
    tailo = (h0.get("T") or "").strip()
    audio_id = str(h0.get("_") or "").strip()
    audio_url = (
        f"https://r2-assets.moedict.tw/audio/t/{audio_id}.mp3"
        if audio_id
        else None
    )

    defs = h0.get("d") or []
    mandarin: list[str] = []
    for d in defs:
        f = d.get("f", "")
        cleaned = re.sub(r"[`~]", "", f).strip()
        if cleaned and cleaned not in mandarin:
            mandarin.append(cleaned)
    if not tailo and not mandarin:
        return None
    return tailo, mandarin, audio_url


def fetch_chhoetaigi_entry(word: str) -> tuple[str, list[str]] | None:
    """Fallback 2: Fetch entry from ChhoeTaigi iTaigi dataset (cached in memory)."""
    global _chhoetaigi_cache
    if _chhoetaigi_cache is None:
        url = "https://raw.githubusercontent.com/ChhoeTaigi/ChhoeTaigiDatabase/master/ChhoeTaigiDatabase/ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
        req = Request(
            url,
            headers={
                "User-Agent": "AnkiAutoItaigi/1.0 (https://github.com/ryusoh/anki)"
            },
        )
        try:
            with urlopen_with_proxy_fallback(req, timeout=10) as resp:
                content = resp.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))
            cache: dict[str, tuple[list[str], list[str]]] = {}
            for row in reader:
                hoabun = (row.get("HoaBun") or "").strip()
                kip = (row.get("KipUnicode") or "").strip()
                taibun = (row.get("HanLoTaibunKip") or "").strip()
                if not hoabun:
                    continue
                if hoabun not in cache:
                    cache[hoabun] = ([], [])
                tailos, taibuns = cache[hoabun]
                if kip and kip not in tailos:
                    tailos.append(kip)
                if taibun and taibun not in taibuns:
                    taibuns.append(taibun)
            _chhoetaigi_cache = {
                k: ("/".join(v[0]), v[1]) for k, v in cache.items()
            }
        except Exception:
            _chhoetaigi_cache = {}

    return _chhoetaigi_cache.get(word)


def lookup_itaigi(word: str) -> tuple[str, list[str], str | None] | None:
    """Lookup Taiwanese Hokkien entry with 3-tier fallback chain:
    1. iTaigi API (https://itaigi.tw)
    2. MOEDiCT API (https://www.moedict.tw)
    3. ChhoeTaigi Dataset (GitHub raw CSV)

    Returns (tailo, mandarin_words, fallback_audio_url) or None.
    """
    # Tier 1: iTaigi API
    body = fetch_itaigi_json(word)
    if body and not body.startswith("Error:"):
        parsed = parse_itaigi_json(body, word)
        if parsed is not None:
            tailo, mandarin = parsed
            return tailo, mandarin, None

    # Tier 2: MOEDiCT API
    moe_res = fetch_moedict_entry(word)
    if moe_res is not None:
        return moe_res

    # Tier 3: ChhoeTaigi Dataset
    chhoe_res = fetch_chhoetaigi_entry(word)
    if chhoe_res is not None:
        tailo, mandarin = chhoe_res
        return tailo, mandarin, None

    return None

