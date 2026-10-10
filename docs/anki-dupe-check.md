# Anki duplicate-check internals (verified against 25.02.5)

How Anki decides a note's first field is a duplicate, where the verdict
surfaces in the Qt UI, and the collection-schema facts needed to reproduce
the check in add-on code. Everything below was read from the pinned 25.02.5
source and cross-checked against a real collection — re-verify line numbers
if the installed version moved (`deck_scoped_dupes/` builds on all of this).

## The pipeline

`Note.fields_check()` (`pylib/anki/notes.py`) →
`col._backend.note_fields_check(...)` — the decision is made in **Rust**
(`rslib/src/notes/mod.rs: note_fields_check`), not Python. The legacy
aliases `duplicate_or_empty` / `dupeOrEmpty` point at the same method.
State enum (`proto/anki/notes.proto`, `NoteFieldsCheckResponse.State`):

```
NORMAL = 0   EMPTY = 1   DUPLICATE = 2
MISSING_CLOZE = 3   NOTETYPE_NOT_CLOZE = 4   FIELD_NOT_CLOZE = 5
```

The backend's duplicate verdict (`is_duplicate`) is:

1. NFC-normalize the first field (when the `NormalizeNoteText` config is on,
   the default), then `strip_html_preserving_media_filenames`.
2. Empty after trim → EMPTY (cloze checks precede the dupe check otherwise).
3. Compute `field_checksum` of the stripped text and look up notes **with
   the same notetype id** sharing that checksum; DUPLICATE iff any other
   note's stripped first field is exactly equal.

So stock Anki dupes are: per-notetype, case-**sensitive**, collection-wide
(no deck scoping). `col.find_dupes(field_name, search)` in
`pylib/anki/collection.py` is the browser dialog's version — it groups by
`strip_html_media(field)` and _is_ scoped by its `search` argument (typing
`deck:X` in the Find Duplicates dialog's search box works out of the box).

## strip_html_preserving_media_filenames semantics

`rslib/src/text.rs`, in order:

1. Media tags (`<img|audio|video|object|source ... src|data=...>`) →
   `filename` (a space, the src/data value, a space).
2. Remove `<!-- comments -->`, `<style>…</style>`, `<script>…</script>`,
   then all remaining `<…>` tags (no space inserted — adjacent tags merge
   words).
3. Decode HTML entities; `&nbsp;`/U+00A0 becomes a plain space.
4. `[sound:x.mp3]` refs are NOT special-cased — they survive verbatim.

Python mirror: `deck_scoped_dupes/core.py: strip_for_compare`.

## Collection schema facts (modern, 25.02)

- `notes(id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data)` —
  `flds` is U+001F-joined, `csum` is `int(sha1(stripped_first_field)[:8 hex], 16)`
  (mirrors `pylib anki/utils.py field_checksum`; verified to match stored
  values on a real collection). First field in SQL:
  `substr(flds, 1, instr(flds || char(31), char(31)) - 1)`.
- `cards(id, nid, did, ord, …)` — deck membership is per **card**, so a
  note can sit in several decks: `SELECT DISTINCT did FROM cards WHERE nid=?`.
- `decks(id, name, …)` and `notetypes(id, name, …)` are real tables — the
  `col` row's JSON blobs are gone. Deck names use **U+001F** as the `::`
  separator in the table; the Python API (`col.decks.all_names_and_ids()`)
  returns `::`-joined names.
- Ad-hoc queries: `python3 tools/query_collection.py 'SELECT …'` snapshots
  the collection (WAL included) and registers the `unicase` collation for
  you — don't hand-roll the copy boilerplate.

## Where the verdict surfaces in Qt

- **Editor dupe frame**: `qt/aqt/editor.py` — `loadNote` calls
  `note.fields_check()` and `_update_duplicate_display` paints field 0 when
  the state is DUPLICATE; the typing timer re-checks via
  `_check_and_update_duplicate_display_async` (background `QueryOp`). Runs
  in both AddCards and the browser editor.
- **AddCards**: `_note_can_be_added` never blocks on DUPLICATE (only EMPTY
  and cloze problems) — dupes are allowed, just flagged. The target deck is
  `addcards.deck_chooser.selected_deck_id`; track it with
  `gui_hooks.add_cards_did_init(addcards)` and
  `add_cards_did_change_deck(deck_id)`.
- **Browser**: menus built before `gui_hooks.browser_menus_did_init(browser)`;
  the Notes menu is `browser.form.menu_Notes`. Current search text:
  `browser.current_search()`; replace results: `browser.search_for("nid:…")`.
  Find Duplicates dialog: `qt/aqt/browser/find_duplicates.py`.

Hook signatures are generated — see `qt/tools/genhooks_gui.py` (the
`qt/aqt/gui_hooks.py` module is a stub re-exporting `_aqt.hooks`).
