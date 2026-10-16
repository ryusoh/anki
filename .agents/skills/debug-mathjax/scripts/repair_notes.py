#!/usr/bin/env python3
"""Apply _convert_dollar_to_mathjax to one or more notes via AnkiConnect.

Fetches each note's fields, runs the converter (same code the in-app button
runs), and writes back ONLY the fields whose content actually changed.

Usage:
    python3 .agents/skills/debug-mathjax/scripts/repair_notes.py <note-id> [...]
    python3 .agents/skills/debug-mathjax/scripts/repair_notes.py --dry-run <note-id> [...]

Requires Anki running with AnkiConnect on http://localhost:8765.

Hands-off corruptions (e.g. whitespace-flanked span-placeholder segments)
convert to themselves — the script reports them as "unchanged"; those cards
still need the manual byte-level repair from the debug report.
"""

import json
import sys
import urllib.request
from pathlib import Path

ANKICONNECT = "http://localhost:8765"

_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT))

import conftest  # noqa: F401, E402  # stubs aqt/anki for the import below
from auto_mathjax import _convert_dollar_to_mathjax  # noqa: E402


def invoke(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKICONNECT, data=payload)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("error"):
        raise RuntimeError(f"AnkiConnect {action}: {data['error']}")
    return data["result"]


def main(argv):
    dry_run = "--dry-run" in argv
    note_ids = [a for a in argv if a != "--dry-run"]
    if not note_ids:
        print(__doc__)
        return 2

    infos = invoke("notesInfo", notes=[int(n) for n in note_ids])
    changed_any = False
    for info in infos:
        nid = info["noteId"]
        fields = info["fields"]
        updates = {}
        for name, f in fields.items():
            old = f["value"]
            new = _convert_dollar_to_mathjax(old)
            if new != old:
                updates[name] = new
                print(f"note {nid} field '{name}' ({len(old)} -> {len(new)} chars):")
                print(f"  - {old!r}")
                print(f"  + {new!r}")
        if not updates:
            print(f"note {nid}: unchanged (hands-off corruption or already clean)")
            continue
        changed_any = True
        if dry_run:
            print(f"note {nid}: DRY-RUN, not written")
        else:
            invoke("updateNoteFields", note={"id": nid, "fields": updates})
            print(f"note {nid}: updated {len(updates)} field(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
