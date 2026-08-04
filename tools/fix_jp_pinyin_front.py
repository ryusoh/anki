"""Collapse language sentence-card fronts to the target line, moving the rest to the back.

In the 言語 decks (日語, 粤語, ...), sentence cards carry a multi-line front: a
Chinese line, the target-language sentence with spaces between words, then a
拼音練習/發音/音標 practice block. This script rewrites each such note via
AnkiConnect so the front is only the target sentence (spaces stripped) and
everything else moves to the top of the back field, above the [sound:] line.

Usage (from the repo root, Anki with AnkiConnect running):

    python3 tools/fix_jp_pinyin_front.py                 # dry run: print planned changes
    python3 tools/fix_jp_pinyin_front.py --apply         # write via AnkiConnect
    python3 tools/fix_jp_pinyin_front.py --query 'deck:言語::粤語 front:*拼音練習*'
"""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.request

ANKICONNECT_URL = "http://127.0.0.1:8765"
DEFAULT_QUERY = "deck:言語::日語 front:*拼音練習*"
MARKER = "拼音練習"

# A "line" in these fields is a leaf <div> (no nested <div> inside). Wrapper
# <div>s only group lines, so they never match this pattern.
LEAF_DIV_RE = re.compile(r"<div\b[^>]*>((?:(?!</?div\b).)*?)</div>", re.DOTALL)
BR_RE = re.compile(r"<br\s*/?>")
RT_RE = re.compile(r"<rt\b[^>]*>.*?</rt>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def _plain_text(fragment: str) -> str:
    """Text of an HTML fragment, without ruby readings (rt) or tags."""
    return html.unescape(TAG_RE.sub("", RT_RE.sub("", fragment)))


def _strip_spacing(text: str) -> str:
    return text.replace(" ", "").replace("\xa0", "").strip()


def _transform_divs(front: str, back: str) -> tuple[str, str] | None:
    lines = list(LEAF_DIV_RE.finditer(front))
    for i, line in enumerate(lines):
        if MARKER in line.group(0):
            if i == 0:
                return None
            jp_line = lines[i - 1]
            break
    else:
        return None
    sentence = _strip_spacing(_plain_text(jp_line.group(1)))
    if not sentence:
        return None
    rest = front[: jp_line.start()] + front[jp_line.end() :]
    return sentence, rest + back


def _transform_br(front: str, back: str) -> tuple[str, str] | None:
    """Variant for fronts that separate lines with <br> instead of <div>."""
    lines = BR_RE.split(front)
    for i, line in enumerate(lines):
        if MARKER in line:
            if i == 0:
                return None
            sentence = _strip_spacing(_plain_text(lines[i - 1]))
            if not sentence:
                return None
            rest = "<br>".join(lines[: i - 1] + lines[i:])
            return sentence, rest + back
    return None


def transform(front: str, back: str) -> tuple[str, str] | None:
    """Return (new_front, new_back) for a practice-block card, else None.

    new_front is the target-language line (the line right before the 拼音練習
    block) with word-spacing stripped; new_back is the rest of the old front
    prepended above the old back's [sound:] line. A back that already embeds a
    copy of the practice block is left untouched (only the front changes).
    """
    if MARKER not in front:
        return None
    result = _transform_divs(front, back) or _transform_br(front, back)
    if result is not None and MARKER in back:
        return result[0], back
    return result


def plan_updates(notes: list[dict]) -> list[dict]:
    """Map notesInfo results to updateNoteFields payloads; skip untouched notes."""
    updates = []
    for note in notes:
        ordered = sorted(note["fields"].items(), key=lambda kv: kv[1]["order"])
        if len(ordered) < 2:
            continue
        front_name, front = ordered[0][0], ordered[0][1]["value"]
        back_name, back = ordered[1][0], ordered[1][1]["value"]
        result = transform(front, back)
        if result is None:
            continue
        new_front, new_back = result
        updates.append(
            {"id": note["noteId"], "fields": {front_name: new_front, back_name: new_back}}
        )
    return updates


def ankiconnect_invoke(action: str, params: dict | None = None):
    payload = {"action": action, "version": 6}
    if params is not None:
        payload["params"] = params
    req = urllib.request.Request(
        ANKICONNECT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30.0) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    if res.get("error"):
        raise RuntimeError(f"AnkiConnect error on {action}: {res['error']}")
    return res.get("result")


def run(invoke, query: str, apply: bool) -> dict:
    """Find, plan, and optionally write the front collapse; return a summary."""
    note_ids = invoke("findNotes", {"query": query})
    updates = []
    # notesInfo in chunks: a single 6000-note request can exceed payload limits.
    for i in range(0, len(note_ids), 500):
        updates.extend(plan_updates(invoke("notesInfo", {"notes": note_ids[i : i + 500]})))
    for update in updates:
        print(f"--- note {update['id']} ---")
        for name, value in update["fields"].items():
            print(f"[{name}] {value}")
        print()
    written = 0
    if apply:
        for update in updates:
            invoke("updateNoteFields", {"note": update})
            written += 1
    return {"matched": len(note_ids), "planned": len(updates), "written": written}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Anki search query")
    args = parser.parse_args()
    summary = run(ankiconnect_invoke, args.query, args.apply)
    print(
        f"Summary: {summary['matched']} notes matched, {summary['planned']} planned, "
        f"{summary['written']} written."
    )


if __name__ == "__main__":
    main()
