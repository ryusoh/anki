"""Sweep a field-transform function across every note in the real collection.

A transform verified only against the card the user reported is not done:
other notes hold differently-shaped HTML, and a heuristic that fixes one
card can silently mangle another (see docs/creating-an-addon.md, "Field
HTML reality"). This tool runs the transform over EVERY note field (on a
temp copy of the collection, like tools/dump_field.py), prints a diff for
each field that would change, and re-applies the transform to each result
to catch idempotency bugs — so the full blast radius is reviewed before
the code ever runs inside Anki.

Usage (from the repo root):

    python3 tools/sweep_transform.py auto_mathjax:_convert_dollar_to_mathjax
    python3 tools/sweep_transform.py <module>:<function> --contains 'Quick'
    python3 tools/sweep_transform.py <module>:<function> --limit 10

`aqt`/`anki` are mocked before the addon module is imported, so any addon's
pure transform function can be loaded outside Anki.
"""

from __future__ import annotations

import argparse
import difflib
import importlib
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # tools/
sys.path.insert(0, os.path.dirname(sys.path[0]))  # repo root (addon modules)

from dump_field import default_collection, split_fields  # noqa: E402

# Break field HTML after these so diffs show one logical line per row.
SEGMENT_BREAK_RE = re.compile(r"(?<=</div>)|(?<=<br>)|(?<=<br/>)")


@dataclass
class FieldChange:
    idx: int
    old: str
    new: str | None  # None when the transform raised
    error: str | None = None
    idempotent: bool = True


def load_transform(spec: str):
    """Load a transform callable from a 'module:function' spec.

    Mocks aqt/anki first so addon modules import outside Anki.
    """
    if ":" not in spec:
        raise SystemExit(f"Expected 'module:function', got {spec!r}")
    module_name, func_name = spec.split(":", 1)

    from unittest.mock import MagicMock

    for name in ("aqt", "aqt.editor", "aqt.gui_hooks", "aqt.utils", "anki", "anki.hooks"):
        sys.modules.setdefault(name, MagicMock())

    module = importlib.import_module(module_name)
    try:
        return getattr(module, func_name)
    except AttributeError:
        raise SystemExit(f"{module_name} has no attribute {func_name!r}") from None


def sweep_notes(con: sqlite3.Connection, transform, contains: str | None = None) -> list:
    """Apply `transform` to every field of every note; return changed notes.

    Returns (note_id, [FieldChange, ...]) pairs — only notes where at least
    one field would change or the transform raised.
    """
    results = []
    for nid, flds in con.execute("SELECT id, flds FROM notes ORDER BY id"):
        fields = split_fields(flds)
        if contains is not None and not any(contains in f for f in fields):
            continue
        changes = []
        for i, field in enumerate(fields):
            try:
                new = transform(field)
            except Exception as e:  # a crash on weird real HTML is a finding
                changes.append(FieldChange(i, field, None, error=repr(e)))
                continue
            if new == field:
                continue
            try:
                stable = transform(new) == new
            except Exception:
                stable = False
            changes.append(FieldChange(i, field, new, idempotent=stable))
        if changes:
            results.append((nid, changes))
    return results


def _segments(html: str) -> list:
    return [s for s in SEGMENT_BREAK_RE.split(html) if s]


def format_change(nid: int, change: FieldChange) -> str:
    """Render one field change as a unified diff block."""
    lines = [f"=== note {nid}, field {change.idx} ==="]
    if change.error is not None:
        lines.append(f"!! transform raised: {change.error}")
        return "\n".join(lines)
    diff = difflib.unified_diff(
        _segments(change.old), _segments(change.new or ""), lineterm="", n=0
    )
    lines.extend(line for line in diff if not line.startswith(("---", "+++", "@@")))
    if not change.idempotent:
        lines.append("!! NOT IDEMPOTENT: transform(transform(field)) != transform(field)")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "transform", help="transform spec, e.g. auto_mathjax:_convert_dollar_to_mathjax"
    )
    parser.add_argument(
        "--contains", default=None, help="only sweep notes where any field contains this text"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max changed notes to print (summary still counts all)",
    )
    parser.add_argument(
        "--collection", default=None, help="path to collection.anki2 (default: newest profile)"
    )
    args = parser.parse_args()

    transform = load_transform(args.transform)
    collection = args.collection or default_collection()

    # Copy first: the live database is locked while Anki is running.
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copyfile(collection, tmp_path)
        con = sqlite3.connect(tmp_path)
        try:
            total = con.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            results = sweep_notes(con, transform, args.contains)
        finally:
            con.close()
    finally:
        os.unlink(tmp_path)

    for nid, changes in results[: args.limit]:
        for change in changes:
            print(format_change(nid, change))
            print()
    if args.limit is not None and len(results) > args.limit:
        print(f"... {len(results) - args.limit} more changed notes not shown (raise --limit)")

    errors = sum(1 for _, cs in results for c in cs if c.error)
    unstable = sum(1 for _, cs in results for c in cs if not c.idempotent)
    print(
        f"Summary: {total} notes scanned, {len(results)} would change, "
        f"{errors} errors, {unstable} idempotency violations."
    )


if __name__ == "__main__":
    main()
