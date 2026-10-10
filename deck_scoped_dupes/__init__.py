# -*- coding: utf-8 -*-

"""
Anki Add-on: Deck-Scoped Duplicates

Anki flags a note as a duplicate whenever another note of the same notetype
shares its first field — across the whole collection. With one deck per
language (or topic), a Japanese word written with Chinese characters collides
with the same characters in a Taiwanese or Wu deck, and the warning is noise.

This add-on scopes the duplicate check to decks: a note is only a duplicate
when the matching note has a card in the SAME deck.

- While adding cards, the "same deck" is the deck picked in the Add dialog's
  deck chooser (tracked via gui_hooks).
- For an existing note (e.g. the browser editor's red dupe frame), "same
  deck" means the two notes share at least one deck.
- A "Find Duplicates in This Deck" action in the browser's Notes menu lists
  the within-deck duplicates of the deck named in the current search.

Only DUPLICATE results are ever downgraded to NORMAL; every other
fields_check result (empty, cloze problems, real same-deck dupes) passes
through untouched. Set "include_subdecks": true in the add-on config to treat
a deck and its subdecks as one scope.
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


def _all_decks(col):
    return [(d.id, d.name) for d in col.decks.all_names_and_ids()]


def _scope_dids(col, note):
    """Decks the dupe check is scoped to, or None to keep Anki's behavior."""
    if not note.id:
        if _add_cards_deck_id is None:
            return None
        dids = {_add_cards_deck_id}
    else:
        dids = set(core.decks_of_note(col.db, note.id))
        if not dids:
            return None
    return core.expand_subdecks(dids, _all_decks(col), _include_subdecks())


def _scoped_fields_check(note):
    state = _original_fields_check(note)
    if state != core.STATE_DUPLICATE:
        return state
    col = note.col
    dids = _scope_dids(col, note)
    if not dids:
        return state
    first = note.fields[0] if note.fields else ""
    if core.has_dupe_in_decks(col.db, note.id or 0, note.mid, first, dids):
        return state
    return core.STATE_NORMAL


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
    placeholders = ",".join("?" for _ in dids)
    rows = col.db.all(
        "SELECT DISTINCT n.id, n.mid, n.flds FROM notes n"
        " JOIN cards c ON c.nid = n.id"
        f" WHERE c.did IN ({placeholders})",
        *dids,
    )
    nids = [nid for _val, group in core.dupe_groups(rows) for nid in group]
    if not nids:
        tooltip("No duplicates found in this deck.")
        return
    browser.search_for("nid:" + ",".join(str(nid) for nid in nids))


_patch_note()
gui_hooks.add_cards_did_init.append(on_add_cards_did_init)
gui_hooks.add_cards_did_change_deck.append(on_add_cards_did_change_deck)
gui_hooks.browser_menus_did_init.append(on_browser_menus_did_init)
