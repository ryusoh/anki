# -*- coding: utf-8 -*-

"""
Anki Add-on: Deck-Scoped Duplicates

Anki flags a note as a duplicate only against notes of the SAME notetype,
but across the whole collection. With one deck per language (or topic), a
Japanese word written with Chinese characters collides with the same
characters in a Taiwanese or Wu deck, and the warning is noise — while a
genuine duplicate made under a different notetype in the same deck is
missed entirely.

This add-on scopes the duplicate check to decks and across notetypes: a
note is a duplicate when a note sharing its first field has a card in the
SAME deck, whatever notetype that note uses.

- While adding cards, the "same deck" is the deck picked in the Add dialog's
  deck chooser (tracked via gui_hooks).
- For an existing note (e.g. the browser editor's red dupe frame), "same
  deck" means the two notes share at least one deck.
- A "Find Duplicates in This Deck" action in the browser's Notes menu lists
  the within-deck duplicates of the deck named in the current search.

Only the NORMAL/DUPLICATE verdicts are ever changed (empty and cloze
problems pass through untouched): DUPLICATE is downgraded when no matching
note shares a deck, NORMAL is upgraded when a cross-notetype match — or a
case variant in a deck listed in "case_insensitive_decks" — shares one.
Config: "include_subdecks" treats a deck and its subdecks as one scope
(default false); "cross_notetype_dupes" disables the cross-notetype
matching when set to false (default true); "case_insensitive_decks" lists
deck names whose comparisons ignore letter case, subdecks included
(default ["金融"] — case differences stay meaningful in the English deck).
"""

from __future__ import annotations

from anki.notes import Note  # type: ignore
from aqt import gui_hooks  # type: ignore

from . import core

_SENTINEL = "_deck_scoped_dupes_patched"

# Deck picked in the open AddCards dialog; None until one is opened.
_add_cards_deck_id = None

_original_fields_check = None


def _config():
    from aqt import mw

    if mw is None:
        return {}
    conf = mw.addonManager.getConfig(__name__)
    return conf if isinstance(conf, dict) else {}


def _include_subdecks():
    return bool(_config().get("include_subdecks", False))


def _cross_notetype():
    return bool(_config().get("cross_notetype_dupes", True))


def _case_insensitive(col, anchor_dids):
    """True when an anchor deck (or its parent) is in case_insensitive_decks."""
    names = _config().get("case_insensitive_decks")
    if not isinstance(names, list):
        return False
    return core.any_deck_named(anchor_dids, _all_decks(col), [str(n) for n in names])


def _all_decks(col):
    return [(d.id, d.name) for d in col.decks.all_names_and_ids()]


def _scope_dids(col, note):
    """(anchor_dids, scope_dids), or (None, None) to keep Anki's behavior.

    The anchor is the pre-expansion deck set: the Add dialog's deck for a new
    note, the note's own card decks for an existing one. It decides whether
    the case-insensitive deck list applies.
    """
    if not note.id:
        if _add_cards_deck_id is None:
            return None, None
        anchor = {_add_cards_deck_id}
    else:
        anchor = set(core.decks_of_note(col.db, note.id))
        if not anchor:
            return None, None
    return anchor, core.expand_subdecks(anchor, _all_decks(col), _include_subdecks())


def _scoped_fields_check(note):
    state = _original_fields_check(note)
    if state not in (core.STATE_NORMAL, core.STATE_DUPLICATE):
        return state
    col = note.col
    anchor, dids = _scope_dids(col, note)
    if not dids:
        return state
    case_insensitive = _case_insensitive(col, anchor)
    first = note.fields[0] if note.fields else ""
    dupe_mids = core.find_deck_dupes(
        col.db, note.id or 0, first, dids, case_insensitive=case_insensitive
    )
    same_notetype = note.mid in dupe_mids
    cross_notetype = _cross_notetype() and bool(dupe_mids - {note.mid})
    if state == core.STATE_DUPLICATE:
        return state if (same_notetype or cross_notetype) else core.STATE_NORMAL
    # backend's check is same-notetype and case-sensitive: a cross-notetype
    # match, or a case variant in a case-insensitive deck, is a dupe Anki
    # itself can never see
    upgrade = cross_notetype or (case_insensitive and same_notetype)
    return core.STATE_DUPLICATE if upgrade else state


def _patch_note():
    global _original_fields_check
    if hasattr(Note, _SENTINEL):
        return
    _original_fields_check = Note.fields_check
    Note.fields_check = _scoped_fields_check
    Note.duplicate_or_empty = _scoped_fields_check
    Note.dupeOrEmpty = _scoped_fields_check
    setattr(Note, _SENTINEL, True)


def on_add_cards_did_init(addcards):
    global _add_cards_deck_id
    _add_cards_deck_id = addcards.deck_chooser.selected_deck_id


def on_add_cards_did_change_deck(deck_id):
    global _add_cards_deck_id
    _add_cards_deck_id = deck_id


def on_browser_menus_did_init(browser):
    from aqt.qt import qconnect

    action = browser.form.menu_Notes.addAction("Find Duplicates in This Deck")
    qconnect(action.triggered, lambda: find_dupes_in_current_deck(browser))


def find_dupes_in_current_deck(browser):
    from aqt.utils import tooltip

    col = browser.mw.col
    deck_name = core.parse_deck_filter(browser.current_search())
    if deck_name is None:
        tooltip("Add a deck: filter (or click a deck in the sidebar) first.")
        return
    deck = col.decks.current() if deck_name == "current" else col.decks.by_name(deck_name)
    if deck is None:
        tooltip(f"Deck not found: {deck_name}")
        return
    dids = core.expand_subdecks({deck["id"]}, _all_decks(col), _include_subdecks())
    case_insensitive = _case_insensitive(col, {deck["id"]})
    placeholders = ",".join("?" for _ in dids)
    rows = col.db.all(
        "SELECT DISTINCT n.id, n.mid, n.flds FROM notes n"
        " JOIN cards c ON c.nid = n.id"
        f" WHERE c.did IN ({placeholders})",
        *dids,
    )
    nids = [
        nid
        for _val, group in core.dupe_groups(
            rows,
            per_notetype=not _cross_notetype(),
            case_insensitive=case_insensitive,
        )
        for nid in group
    ]
    if not nids:
        tooltip("No duplicates found in this deck.")
        return
    browser.search_for("nid:" + ",".join(str(nid) for nid in nids))


_patch_note()
gui_hooks.add_cards_did_init.append(on_add_cards_did_init)
gui_hooks.add_cards_did_change_deck.append(on_add_cards_did_change_deck)
gui_hooks.browser_menus_did_init.append(on_browser_menus_did_init)
