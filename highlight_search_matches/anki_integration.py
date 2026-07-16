# Browser table highlighting has been removed as Anki 23.10+ uses native Qt
# rendering (QItemDelegate) which doesn't support HTML in cells.
# The editor highlighting (in editor_integration.py) still works correctly.
#
# What lives here instead: filtering search results. Anki's search matches
# raw field HTML with entities kept, so searching "BSP" false-positives on
# every note containing "&nbsp;". We drop those noise rows from the results.

from aqt.gui_hooks import browser_did_search

from .core import extract_search_terms, note_has_real_match

# Anki search wildcards. A term containing one can legitimately match text we
# cannot verify with a literal check, so we never filter such searches.
_WILDCARD_CHARS = ("*", "_")


def on_browser_did_search_filter(search_context) -> None:
    """Drop result rows whose note only matches inside HTML entities/tags."""
    try:
        ids = search_context.ids
        if not ids:
            return
        terms = extract_search_terms(search_context.search)
        if not terms:
            return
        if any(char in term for term in terms for char in _WILDCARD_CHARS):
            return

        browser = search_context.browser
        col = browser.col
        notes_mode = bool(browser.table.is_notes_mode())

        match_by_note_id: dict[int, bool] = {}
        kept = []
        for item_id in ids:
            note = col.get_note(item_id) if notes_mode else col.get_card(item_id).note()
            if note.id not in match_by_note_id:
                match_by_note_id[note.id] = note_has_real_match(list(note.fields), terms)
            if match_by_note_id[note.id]:
                kept.append(item_id)
        if len(kept) != len(ids):
            search_context.ids = kept
    except Exception as e:
        # Filtering is best-effort; never break the browser search.
        print(f"[hsm] search result filter error: {e}")


def init_addon():
    browser_did_search.append(on_browser_did_search_filter)
