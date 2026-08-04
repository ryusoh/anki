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
import http.client
import json
import re
import time
import urllib.error
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
SOUND_RE = re.compile(r"\[sound:[^\[\]]+\]")
# Markup that already puts a [sound:] ref on its own rendered line.
LINE_BOUNDARY_BEFORE_RE = re.compile(r"(?:<br\s*/?>|</(?:div|p|li|tr|h[1-6])>)\s*$")
LINE_BOUNDARY_AFTER_RE = re.compile(r"^\s*(?:<br\s*/?>|</?(?:div|p|li|tr|h[1-6])\b)")
# Field-tail junk: explicit breaks/whitespace, and wrapper divs whose entire
# content is breaks/whitespace/empty inline tags (they render as blank lines).
TRAILING_JUNK_RE = re.compile(r"(?:\s|&nbsp;|<br\s*/?>)+$")
# An empty div in tail position (only closers/junk may follow it); stripping it
# repeatedly unwraps nests like <div><div><div><br></div></div></div>.
EMPTY_DIV_TAIL_RE = re.compile(
    r"<div\b[^>]*>(?:\s|&nbsp;|<br\s*/?>|<i></i>|<b></b>)*</div>"
    r"(?=(?:\s|&nbsp;|<br\s*/?>|</div>)*$)"
)


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


def fix_glued_sound(text: str) -> str:
    """Put every [sound:] ref on its own rendered line.

    A ref is "glued" when text or an inline tag (</b>, </span>, ...) sits right
    before or after it; <br>/block-tag boundaries and field edges already give
    it a line of its own. Glued refs get a <br> inserted on the offending side.
    """
    out, last = [], 0
    for m in SOUND_RE.finditer(text):
        before, after = text[last : m.start()], text[m.end() :]
        ref = m.group(0)
        if before.strip() and not LINE_BOUNDARY_BEFORE_RE.search(before):
            out.append(before.rstrip())
            ref = "<br>" + ref
        elif not before.strip() and out and out[-1].endswith("<br>"):
            pass  # the previous ref already ended the line; drop the gap
        else:
            out.append(before)
        if after and not LINE_BOUNDARY_AFTER_RE.match(after):
            ref = ref + "<br>"
        out.append(ref)
        last = m.end()
    out.append(text[last:])
    return "".join(out)


def strip_trailing_blank_lines(text: str) -> str:
    """Drop blank lines (breaks, whitespace, empty wrapper divs) at a field's end."""
    prev = None
    while prev != text:
        prev = text
        text = EMPTY_DIV_TAIL_RE.sub("", text)
        text = TRAILING_JUNK_RE.sub("", text)
    return text


def tidy_field(text: str) -> str:
    return strip_trailing_blank_lines(fix_glued_sound(text))


def plan_tidy(notes: list[dict]) -> list[dict]:
    """Map notesInfo results to updateNoteFields payloads for field tidying.

    Every field of every note is checked; only fields that change are included.
    """
    updates = []
    for note in notes:
        fields = {}
        for name, field in sorted(note["fields"].items(), key=lambda kv: kv[1]["order"]):
            new = tidy_field(field["value"])
            if new != field["value"]:
                fields[name] = new
        if fields:
            updates.append({"id": note["noteId"], "fields": fields})
    return updates


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


def ankiconnect_invoke(action: str, params: dict | None = None, retries: int = 3):
    """Send one AnkiConnect action; retry transient connection drops with backoff."""
    payload = {"action": action, "version": 6}
    if params is not None:
        payload["params"] = params
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                ANKICONNECT_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            break
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError):
            if attempt == retries:
                raise
            time.sleep(0.5 * (attempt + 1))
    if res.get("error"):
        raise RuntimeError(f"AnkiConnect error on {action}: {res['error']}")
    return res.get("result")


def run(invoke, query: str, apply: bool, plan=plan_updates) -> dict:
    """Find notes, plan changes, print them, optionally write; return a summary."""
    note_ids = invoke("findNotes", {"query": query})
    updates = []
    # notesInfo in chunks: a single 6000-note request can exceed payload limits.
    for i in range(0, len(note_ids), 500):
        updates.extend(plan(invoke("notesInfo", {"notes": note_ids[i : i + 500]})))
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
            if written % 500 == 0:
                print(f"progress: {written}/{len(updates)} written", flush=True)
    return {"matched": len(note_ids), "planned": len(updates), "written": written}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Anki search query")
    parser.add_argument(
        "--tidy",
        action="store_true",
        help="tidy fields (unglue [sound:] refs, strip trailing blank lines) "
        "instead of collapsing fronts",
    )
    args = parser.parse_args()
    plan = plan_tidy if args.tidy else plan_updates
    summary = run(ankiconnect_invoke, args.query, args.apply, plan)
    print(
        f"Summary: {summary['matched']} notes matched, {summary['planned']} planned, "
        f"{summary['written']} written."
    )


if __name__ == "__main__":
    main()
