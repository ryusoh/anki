# Design spec: `field_snapshot_undo` addon (recover deleted MathJax via field revision ring)

| Field       | Value                                                                                                                                                  |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Status      | **Design complete, no code written** (2026-07-14). Update this row when a step ships.                                                                  |
| Goal        | Cmd+Opt+Z restores the current editor field to its previous saved revision — recovering a deleted MathJax formula that native Cmd+Z cannot bring back. |
| Background  | [anki-editor-mathjax-undo.md](anki-editor-mathjax-undo.md) — read §6 and "Workarounds §4" first; this spec implements that workaround.                 |
| Implementer | A smaller model doing TDD. Read `docs/creating-an-addon.md` BEFORE scaffolding.                                                                        |
| Diff scope  | New files under `field_snapshot_undo/` only, plus the Status row + checkboxes of THIS file. Zero edits to any other existing file (§8).                |

RFC 2119 keywords (MUST / MUST NOT / SHOULD / MAY) are used throughout.

## §1 Problem recap (one paragraph)

Anki's rich-text field relies on the browser's native undo stack, but deleting
a rendered `<anki-mathjax>` happens **programmatically** (a `MutationObserver`
calls `frameElement.remove()`), which native undo cannot replay — the formula
is unrecoverable with Cmd+Z. However, every field revision reaches Python ~600
ms after each edit, so a Python-side ring of recent revisions plus a restore
shortcut gives targeted recovery, including in the Add window. All Anki-side
claims are already verified and cited in
[anki-editor-mathjax-undo.md](anki-editor-mathjax-undo.md); do not re-research
them.

## §2 Scope — ported / cut (cuts need user sign-off before extending)

| Capability                                                           | Status                                                        |
| -------------------------------------------------------------------- | ------------------------------------------------------------- |
| Step current field back one saved revision per shortcut press        | **In scope**                                                  |
| Works in Add window (note not yet in collection)                     | **In scope**                                                  |
| Repeated presses walk further back (until ring exhausted)            | **In scope**                                                  |
| MathJax-specific targeting ("jump to last revision containing `\(`") | **Cut** — plain step-back already recovers it in 1–2 presses  |
| JS keystroke guard on delete (workaround §5 of the research doc)     | **Cut** — unstable `anki/RichTextInput` API, separate project |
| History surviving note switch or app restart                         | **Cut** — matches the built-in CodeMirror history's lifetime  |
| Config UI / config.json                                              | **Cut** — constants in module                                 |

## §3 Module layout

```
field_snapshot_undo/
  __init__.py      # hook wiring + restore handler (imports aqt — thin)
  ring.py          # pure logic, no aqt imports (fully unit-testable)
  manifest.json    # copy the pattern from strip_html_tags/manifest.json
  tests/
    test_ring.py   # pure-logic tests
    test_hooks.py  # mocked-aqt wiring tests (copy the sys.modules mock header
                   # from strip_html_tags/tests/test_strip_selection.py)
```

## §4 Ring semantics (`ring.py`) — reference implementation

Keys are `(note_id, field_idx)`. Constants: `RING_CAP = 25` revisions per key,
`STORE_CAP = 50` keys (LRU). The store is a module-level
`collections.OrderedDict`.

```python
from collections import OrderedDict

RING_CAP = 25
STORE_CAP = 50


def push(store, key, value, ring_cap=RING_CAP, store_cap=STORE_CAP):
    """Record value as the newest revision for key. Dedupes against the top
    entry ONLY (deduping against the whole ring would lose A->B->A middles).
    LRU-evicts whole keys beyond store_cap."""
    ring = store.get(key)
    if ring is None:
        store[key] = [value]
    else:
        if ring[-1] != value:
            ring.append(value)
            del ring[:-ring_cap]
        store.move_to_end(key)
    while len(store) > store_cap:
        store.popitem(last=False)


def step_back(store, key, current):
    """Return the revision to restore given the field's current text, or None.

    Case A — current == top and an older entry exists: pop the top, return the
      new top (repeated presses walk backwards).
    Case B — current != top: the current text was never snapshotted (the user
      pressed the shortcut inside the 600 ms debounce window); return the top
      WITHOUT popping.
    Case C — current == top and it is the only entry: nothing older; None.
    """
    ring = store.get(key)
    if not ring:
        return None
    if ring[-1] != current:
        return ring[-1]
    if len(ring) >= 2:
        ring.pop()
        return ring[-1]
    return None
```

This is the trickiest logic in the addon — implementers MUST keep Case B
(it is what makes the shortcut work before the debounced save has fired,
see §6 restore flow and §7 rows 4–5).

## §5 Hook wiring (`__init__.py`)

All hook names and signatures are verified at Anki 25.02.5 in
`qt/tools/genhooks_gui.py` (citation anchors in the research doc §"Workarounds
§4"). Wire exactly these:

- `gui_hooks.editor_did_load_note(editor)` → push every field:
  `for i, val in enumerate(editor.note.fields): push(STORE, (editor.note.id, i), val)`.
  Skip when `editor.note is None`.
- `gui_hooks.editor_did_fire_typing_timer(note)` → same loop over
  `note.fields` (the note already holds the NEW text when this fires — pushing
  after the fact is correct because the ring keeps the older entries).
- `gui_hooks.editor_did_unfocus_field(changed, note, current_field_idx)` →
  push just that field, then `return changed` unmodified (it is a **filter** —
  it MUST return the bool).
- `gui_hooks.editor_did_init_shortcuts(shortcuts, editor)` → append
  `("Ctrl+Alt+Z", lambda: on_restore(editor))`. Qt maps `Ctrl` to Cmd on
  macOS, so this is Cmd+Opt+Z and does not shadow native Cmd+Z.

Restore flow (`on_restore`): call `editor.saveNow(callback, keepFocus=True)`
and do the work in the callback, so any text still inside the 600 ms debounce
window is flushed into `editor.note.fields` first (`Editor.saveNow` exists in
`qt/aqt/editor.py` at 25.02.5 — locate by name, not line). In the callback:

```python
def _restore(editor):
    note = editor.note
    idx = editor.currentField
    if note is None or idx is None or not (0 <= idx < len(note.fields)):
        tooltip("Click into a field first")
        return
    prev = step_back(STORE, (note.id, idx), note.fields[idx])
    if prev is None:
        tooltip("No earlier revision for this field")
        return
    note.fields[idx] = prev
    if not editor.addMode:
        try:
            note.flush()
        except Exception as e:
            print(f"field_snapshot_undo: flush failed: {e}", file=sys.stderr)
    editor.loadNoteKeepingFocus()
```

`tooltip` comes from `aqt.utils`. The `addMode`-guarded flush +
`loadNoteKeepingFocus()` mirrors `_strip_field` in
`strip_html_tags/__init__.py` — copy that idiom, do not invent a new one.
`loadNoteKeepingFocus()` re-fires `editor_did_load_note`, which re-pushes the
restored value; the top-dedupe in `push` makes that a no-op by design.

## §6 Behavior matrix (hand-computed — these become test expectations)

Note id 42, field 0. `F = '\\(x^2\\)'` (stored MathJax source).

| #   | Action                                                                                                                              | Ring for (42,0) after               | Field text after    |
| --- | ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------- |
| 1   | Load note, field = `a F b`                                                                                                          | `['a F b']`                         | `a F b`             |
| 2   | Delete formula; 600 ms timer fires with `a  b`                                                                                      | `['a F b', 'a  b']`                 | `a  b`              |
| 3   | Cmd+Opt+Z (Case A: pop + restore)                                                                                                   | `['a F b']`                         | `a F b`             |
| 4   | Cmd+Opt+Z again (Case C)                                                                                                            | `['a F b']`                         | unchanged + tooltip |
| 5   | Delete formula, press shortcut BEFORE timer (saveNow flushes `a  b` into note; hooks never pushed it → Case B: restore without pop) | `['a F b']`                         | `a F b`             |
| 6   | Type `a F b c`, timer; type `a F b c d`, timer                                                                                      | `['a F b', 'a F b c', 'a F b c d']` | `a F b c d`         |
| 7   | Shortcut ×2 from row 6                                                                                                              | `['a F b']`                         | `a F b`             |
| 8   | Push 30 distinct revisions                                                                                                          | ring length capped at 25            | —                   |

Add-window note: `note.id == 0`, so all in-progress Add notes share key
`(0, idx)` — acceptable (one Add window edits one note at a time; ring reseeds
on every `editor_did_load_note`).

## §7 DO-NOT list (reasons attached)

- **Do NOT run pytest from inside the addon dir** — the root `conftest.py`
  provides the `aqt`/`anki` mocks; per-addon runs fail with
  `ModuleNotFoundError` (AGENTS.md).
- **Do NOT key the store by the editor object** — it leaks Qt references
  across window closes. `(note_id, field_idx)` + LRU cap only.
- **Do NOT dedupe against the whole ring** — only against the top entry;
  otherwise the sequence A→B→A silently drops B and row 7 breaks.
- **Do NOT call `note.flush()` in `addMode`** — the note has no row in the
  collection yet; flush raises. Guard exactly as `strip_html_tags` does.
- **Do NOT restore without `saveNow`** — skipping it breaks matrix row 5
  (the pre-delete text would be overwritten by the pending debounced save
  right after you restore).
- **Do NOT edit any existing addon, `conftest.py`, `Makefile`, or the research
  doc** — the predicted diff (§8) is an acceptance criterion.
- **Do NOT verify with `make -n precommit-fix`** — it is not a dry run and the
  Makefile refuses it (AGENTS.md).

## §8 Red-green plan (each step ends with its verify command, run from repo root)

1. Read `docs/creating-an-addon.md`; scaffold `field_snapshot_undo/` with
   `manifest.json` and empty modules. Verify: `python3 -m pytest field_snapshot_undo/tests/ -q` collects 0 tests, no errors.
2. RED: write `tests/test_ring.py` covering every §6 row that touches the ring
   (rows 1–8 as pure `push`/`step_back` calls) plus STORE_CAP LRU eviction.
   Watch it fail. GREEN: implement `ring.py` (§4). Verify:
   `python3 -m pytest field_snapshot_undo/tests/test_ring.py -q`.
3. RED: write `tests/test_hooks.py` with the mocked-`aqt` header copied from
   `strip_html_tags/tests/test_strip_selection.py`; simulate: load-note
   seeding, typing-timer push, unfocus filter returning `changed`, restore
   Cases A/B/C via a `MagicMock` editor (assert `loadNoteKeepingFocus`
   called / not called, `flush` skipped when `addMode=True`). GREEN:
   implement `__init__.py` (§5). Verify:
   `python3 -m pytest field_snapshot_undo/tests/ -q`.
4. Gates: `make test-py SUITE=field_snapshot_undo/tests` (must also pass under
   `.venv/bin/python3` — it is the interpreter `make` uses), then
   `make quality-py`, then `make fmt-check`.
5. Update the Status row and tick §9 boxes in THIS file with what was actually
   verified; run `make fmt` (Prettier owns markdown formatting). Verify:
   `python3 -m pytest tests/test_docs_index.py -q`.

## §9 Acceptance criteria

- [ ] All new tests green from the repo root under BOTH `python3` and
      `.venv/bin/python3`.
- [ ] `git diff --stat` shows only `field_snapshot_undo/**` plus this spec's
      Status row/checkboxes. Zero other files.
- [ ] `make quality-py` and `make fmt-check` green.
- [ ] NOT machine-verifiable (root conftest mocks `aqt` — the suite cannot see
      real-Anki behavior): the user restarts Anki, deletes a rendered formula,
      presses Cmd+Opt+Z, and the formula returns. State this explicitly as
      unverified in the final report if not manually confirmed.

## §10 Open questions / verify during implementation

- Whether `editor_did_fire_typing_timer` fires in the Add window at 25.02.5
  was not traced. The design does not depend on it: `editor_did_unfocus_field`
  and the `saveNow` flush (Case B) cover Add-window recovery even if the timer
  hook never fires there.
- Whether consecutive collection-level undo entries coalesce is irrelevant
  here (this addon never touches the collection undo stack).
