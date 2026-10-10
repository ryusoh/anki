# -*- coding: utf-8 -*-
"""Pure logic for deck-scoped duplicate detection.

The comparison helpers mirror Anki 25.02.5's backend semantics
(rslib/src/text.rs strip_html_preserving_media_filenames and
rslib/src/notes/mod.rs note_fields_check): NFC-normalize, replace media tags
with their filenames, strip HTML, decode entities. field_checksum matches
pylib anki/utils.py (first 8 hex digits of the sha1 hex digest) so its result
can be compared against the notes.csum column directly.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from typing import Iterable, List, Optional, Sequence, Set, Tuple

# anki notes_pb2.NoteFieldsCheckResponse.State — hard-coded so the module
# imports cleanly under the test harness, which mocks the ``anki`` package.
STATE_NORMAL = 0
STATE_DUPLICATE = 2

# Mirrors HTML_MEDIA_TAGS in rslib/src/text.rs: capture the src/data filename
# of img/audio/video/object/source tags (double-quoted, single-quoted, or
# unquoted).
_MEDIA_TAG_RE = re.compile(
    r"<\s*\b(?:img|audio|video|object|source)\b"
    r"(?:[^>]|\"[^\"]+?\"|'[^']+?')+?"
    r"\b(?:src|data)\b="
    r"""(?:"([^"]+?)"[^>]*>|'([^']+?)'[^>]*>|([^ >]+?)(?:\s[^>]*>|>))""",
    re.IGNORECASE | re.DOTALL,
)

# Mirrors HTML in rslib/src/text.rs: comments, style/script blocks, then tags.
_HTML_RE = re.compile(
    r"(<!--.*?-->)|(<style.*?>.*?</style>)|(<script.*?>.*?</script>)|(<.*?>)",
    re.IGNORECASE | re.DOTALL,
)


def _media_filename(match: "re.Match[str]") -> str:
    fname = next(g for g in match.groups() if g is not None)
    return f" {fname} "


def strip_for_compare(text: str, case_insensitive: bool = False) -> str:
    """Reduce a field to the string Anki's dupe check compares on.

    case_insensitive applies Unicode casefolding on top — an add-on layer
    Anki itself never does (its backend compares case-sensitively)."""
    text = unicodedata.normalize("NFC", text)
    text = _MEDIA_TAG_RE.sub(_media_filename, text)
    text = _HTML_RE.sub("", text)
    if "&" in text:
        text = html.unescape(text).replace("\xa0", " ")
    if case_insensitive:
        text = text.casefold()
    return text


def field_checksum(text: str) -> int:
    """Checksum of an already-stripped field; matches notes.csum."""
    return int(hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:8], 16)


def first_field(flds: str) -> str:
    """First field of a notes.flds blob (fields are \x1f-separated)."""
    return flds.split("\x1f")[0]


_DECK_TERM_RE = re.compile(r'(?<![\w"-])deck:(?:"([^"]+)"|([^\s"]+))')


def parse_deck_filter(search: str) -> Optional[str]:
    """First non-negated deck: term in a browser search string, if any."""
    match = _DECK_TERM_RE.search(search)
    if not match:
        return None
    return next(g for g in match.groups() if g is not None)


def expand_subdecks(
    dids: Iterable[int],
    all_decks: Sequence[Tuple[int, str]],
    include_subdecks: bool,
) -> Set[int]:
    """Deck id set, optionally grown to cover each deck's descendants.

    ``all_decks`` is a sequence of (id, name) with '::'-separated names.
    """
    dids = set(dids)
    if not include_subdecks:
        return dids
    roots = [name for did, name in all_decks if did in dids]
    out = set(dids)
    for did, name in all_decks:
        if any(name == root or name.startswith(root + "::") for root in roots):
            out.add(did)
    return out


def any_deck_named(
    dids: Iterable[int],
    all_decks: Sequence[Tuple[int, str]],
    names: Sequence[str],
) -> bool:
    """True if any of ``dids`` is one of ``names`` or a subdeck of one.

    ``all_decks`` is a sequence of (id, name) with '::'-separated names.
    """
    if not names:
        return False
    for did, name in all_decks:
        if did in dids and any(
            name == listed or name.startswith(listed + "::") for listed in names
        ):
            return True
    return False


def dupe_groups(
    rows: Iterable[Tuple[int, int, str]],
    per_notetype: bool = True,
    case_insensitive: bool = False,
) -> List[Tuple[str, List[int]]]:
    """Group (nid, mid, flds) rows sharing a stripped first field.

    With per_notetype (the default, mirroring col.find_dupes) only same-
    notetype notes group together; pass False to also surface cross-notetype
    dupes. Empty stripped fields never count as dupes.
    """
    vals: dict = {}
    for nid, mid, flds in rows:
        val = strip_for_compare(first_field(flds), case_insensitive)
        if not val.strip():
            continue
        key = (mid, val) if per_notetype else val
        vals.setdefault(key, []).append(nid)
    return [(key[1] if per_notetype else key, nids) for key, nids in vals.items() if len(nids) > 1]


def decks_of_note(db, note_id: int) -> List[int]:
    """Deck ids of every card belonging to the note."""
    rows = db.all("SELECT DISTINCT did FROM cards WHERE nid = ?", note_id)
    return [row[0] for row in rows]


def find_deck_dupes(
    db,
    note_id: int,
    first_field_html: str,
    dids: Iterable[int],
    case_insensitive: bool = False,
) -> Set[int]:
    """Notetype ids of notes duplicating this one's first field that have a
    card in one of the scope decks — same notetype or not.

    Case-insensitive mode cannot use the case-sensitive csum hash as a
    prefilter, so it extracts first fields in SQL and compares in Python.
    """
    target = strip_for_compare(first_field_html, case_insensitive)
    dids = set(dids)
    if not target.strip() or not dids:
        return set()
    placeholders = ",".join("?" for _ in dids)
    in_scope = "EXISTS (SELECT 1 FROM cards c" f" WHERE c.nid = n.id AND c.did IN ({placeholders}))"
    if case_insensitive:
        rows = db.all(
            "SELECT n.id, n.mid,"
            " substr(n.flds, 1, instr(n.flds || char(31), char(31)) - 1)"
            f" FROM notes n WHERE n.id != ? AND {in_scope}",
            note_id,
            *dids,
        )
    else:
        rows = db.all(
            "SELECT n.id, n.mid, n.flds FROM notes n"
            f" WHERE n.csum = ? AND n.id != ? AND {in_scope}",
            field_checksum(target),
            note_id,
            *dids,
        )
    return {
        row[1] for row in rows if strip_for_compare(first_field(row[2]), case_insensitive) == target
    }
