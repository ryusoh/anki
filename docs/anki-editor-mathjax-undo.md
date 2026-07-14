# Why Cmd+Z can't restore a deleted MathJax element in the Anki editor

The question: in the Anki desktop editor (25.02.5, macOS, Qt6 webview), deleting
a rendered MathJax element (the `<anki-mathjax>` custom element shown as an SVG)
cannot be undone with Cmd+Z — nothing comes back — while deleting plain text
undoes fine. Why, and what are the workarounds?

All source citations below are pinned to the `25.02.5` tag of
[ankitects/anki](https://github.com/ankitects/anki) unless noted.

## Short answer

The editor field is a plain `contenteditable` element that relies on the
browser's **native** undo stack — Anki implements no undo stack of its own for
the rich-text input. A rendered MathJax element is wrapped in an `<anki-frame>`
whose deletion is not performed by the browser's editing machinery at all: when
Backspace eats one of the frame's handle characters, a `MutationObserver`
callback removes the whole frame **programmatically** (`frameElement.remove()`).
Chromium's native undo history only records user-agent edits; DOM mutations made
by script are invisible to it (and invalidate entries that reference the removed
nodes). So Cmd+Z restores, at most, an invisible hair-space — the formula is
gone. This is a known upstream bug, open since 2022, still unfixed on `main` as
of 2026-07. Workarounds: the editor's own MathJax-preview toggle, the per-field
HTML editor's independent CodeMirror history, collection-level Edit→Undo after
the 600 ms autosave, or an addon that snapshots field text via `gui_hooks`.

## Evidence, claim by claim

### 1. The rich-text field uses the browser's native undo stack; Anki has none of its own

- The editing surface is `<anki-editable contenteditable="true">`
  ([ts/editable/ContentEditable.svelte#L43](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/ContentEditable.svelte#L43)).
  Grepping `ts/editor` + `ts/editable` at 25.02.5 for "undo" finds no undo
  implementation for the rich-text input.
- Anki acknowledges this in a comment where it clears the plain-text editor's
  CodeMirror history on note switch: "It should be refactored once we work on
  our own Undo stack"
  ([ts/editor/NoteEditor.svelte#L228](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/NoteEditor.svelte#L228)).

### 2. A rendered MathJax is a decorated custom element inside an `<anki-frame>`

- Stored field text `\(...\)` / `\[...\]` is converted to
  `<anki-mathjax>` markup on load, and back to delimiters on save — the
  "decorated element" contract
  ([ts/editable/decorated.ts#L4-L9](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/decorated.ts#L4-L9),
  [ts/editable/mathjax-element.ts#L32-L59](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/mathjax-element.ts#L32-L59)).
- On `connectedCallback`, `decorate()` wraps the element in an `<anki-frame>`
  (`range.surroundContents(frame)`), empties its `innerHTML`, mounts a Svelte
  component that renders the SVG, and sets `contentEditable="false"`
  ([mathjax-element.ts#L99-L141](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/mathjax-element.ts#L99-L141),
  [frame-element.ts#L245-L255](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/frame-element.ts#L245-L255)).
- The frame's start/end handles each contain a hair space (` `) so the
  caret can sit next to the non-editable element
  ([frame-handle.ts#L22-L29](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/frame-handle.ts#L22-L29)).

### 3. "Deleting" the MathJax is done by script, not by the browser's editor

Backspace/Delete at the frame boundary only deletes a handle (or its hair
space). A `MutationObserver` watching each frame then reacts: if a handle was
removed and it wasn't partially selected, it removes the **entire frame**
programmatically —

- `frameElement.remove()` on handle removal
  ([frame-element.ts#L46-L61](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/frame-element.ts#L46-L61),
  the deletion itself at
  [#L59](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/frame-element.ts#L59));
  also `frameElement.remove()` whenever the framed element disappears
  ([#L22](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/frame-element.ts#L22)).
- The MathJax popup's trash button is likewise plain script:
  `mathjaxElement?.remove()`
  ([ts/editor/mathjax-overlay/MathjaxOverlay.svelte#L260](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/mathjax-overlay/MathjaxOverlay.svelte#L260)).

### 4. Script mutations are invisible to (and corrupt) the native undo history

Browsers record only user-agent editing operations in the `contenteditable`
undo stack. The W3C UndoManager explainer states the platform gap directly:
"doing so breaks user agent's native undo and redo because the user agent
cannot undo DOM modifications made by scripts"
([rniwa.github.io/undo-api](https://rniwa.github.io/undo-api/)). So the browser
records the hair-space deletion, the script removes the frame, and undo has
nothing meaningful to reapply. Two more programmatic rewrites make the stack
even less reliable around MathJax:

- the DOM mirror re-populates the field by removing and re-appending every
  child when its store subscription resumes (e.g. after blur)
  ([ts/lib/sveltelib/dom-mirror.ts#L66-L81](https://github.com/ankitects/anki/blob/25.02.5/ts/lib/sveltelib/dom-mirror.ts#L66-L81)),
  orphaning any undo entries that referenced the old nodes;
- every (re)insertion of an `<anki-mathjax>` re-runs `decorate()` with further
  DOM surgery (see claim 2), so even when the browser does manage to re-insert
  a deleted frame, the follow-up mutations desync subsequent undo steps —
  the corrupted-stack symptoms described in
  [issue #2429](https://github.com/ankitects/anki/issues/2429).

### 5. Upstream status: known, open, unfixed

- [#1941 "MathJax deletion can not be undone"](https://github.com/ankitects/anki/issues/1941)
  — open since 2022-07, label `editor`.
- [#2429 "MathJax popup breaks undo / redo flow"](https://github.com/ankitects/anki/issues/2429)
  — open since 2023-03; maintainer dae, 2023-08: "Contributions are welcome. A
  workaround you can use for now is to click the cog icon and turn off the
  visual editor."
- [#2642 "Can't undo pasting mathjax element"](https://github.com/ankitects/anki/issues/2642)
  and [#3800](https://github.com/ankitects/anki/issues/3800) (2025, marked a
  duplicate of #2429) — both open.
- No PR fixes this: a PR search for editor undo finds only unrelated fixes
  (CodeMirror undo [#1640](https://github.com/ankitects/anki/pull/1640), list
  undo [#4213](https://github.com/ankitects/anki/pull/4213)). On `main`
  (2026-07) the identical `frameElement.remove()` logic is still present at
  [ts/lib/editable/frame-element.ts](https://github.com/ankitects/anki/blob/main/ts/lib/editable/frame-element.ts)
  (files moved from `ts/editable/` to `ts/lib/editable/` after 25.02).

### 6. How field content reaches Python (matters for workarounds)

- The webview debounces field changes 600 ms, then sends
  `key:<field>:<nid>:<html>`
  ([NoteEditor.svelte#L293-L303](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/NoteEditor.svelte#L293-L303));
  blur sends the same payload immediately.
- Python's bridge handler writes `self.note.fields[ord]` and — except in the
  Add window (`addMode`) — calls `_save_current_note()`, which runs the
  undoable `update_note` collection op
  ([qt/aqt/editor.py#L399-L431](https://github.com/ankitects/anki/blob/25.02.5/qt/aqt/editor.py#L399-L431),
  [#L623-L630](https://github.com/ankitects/anki/blob/25.02.5/qt/aqt/editor.py#L623-L630),
  [qt/aqt/operations/note.py#L25-L26](https://github.com/ankitects/anki/blob/25.02.5/qt/aqt/operations/note.py#L25-L26)).
  `col.update_note(skip_undo_entry=False)` creates a collection undo entry
  ([pylib/anki/collection.py#L506-L508](https://github.com/ankitects/anki/blob/25.02.5/pylib/anki/collection.py#L506-L508)).

## Workarounds, ranked

### 1. Turn off MathJax preview (prevention; zero code; maintainer-endorsed)

Editor toolbar cog → untick "MathJax preview" (`tr.editingMathjaxPreview`,
[OptionsButton.svelte#L58-L61](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/editor-toolbar/OptionsButton.svelte#L58-L61)).
This flips the collection config `renderMathjax`
([qt/aqt/editor.py#L1394-L1400](https://github.com/ankitects/anki/blob/25.02.5/qt/aqt/editor.py#L1394-L1400));
with it off, `toUndecorated()` returns the stored text unchanged
([mathjax-element.ts#L46-L49](https://github.com/ankitects/anki/blob/25.02.5/ts/editable/mathjax-element.ts#L46-L49)),
so formulas stay as editable `\(...\)` text and deletion/undo is ordinary text
editing. Cost: no rendered preview while editing.

### 2. Recover via the per-field HTML editor's CodeMirror history (after the fact)

Toggle the field's HTML editor (`</>` badge, Ctrl+Shift+X —
[PlainTextBadge.svelte#L20](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/PlainTextBadge.svelte#L20)),
click inside it, press Cmd+Z. The plain-text input is always mounted (only
visually collapsed,
[NoteEditor.svelte#L756-L771](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/NoteEditor.svelte#L756-L771))
and receives every content revision via `editor.setValue(value)`
([code-mirror.ts#L110-L114](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/code-mirror.ts#L110-L114)),
so CodeMirror's own undo history contains the pre-deletion HTML. It is cleared
only when a different note loads
([NoteEditor.svelte#L226-L232](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/NoteEditor.svelte#L226-L232)).
Works even in the Add window. Same trick reported by users in
[#1941](https://github.com/ankitects/anki/issues/1941).

### 3. Collection-level undo (Browse / Edit Current only)

Once the 600 ms autosave (or a blur) has fired, the deletion is an "Update
Note" collection op (claim 6), so the Browse window's Edit→Undo
([qt/aqt/browser/browser.py#L285](https://github.com/ankitects/anki/blob/25.02.5/qt/aqt/browser/browser.py#L285),
backed by `aqt.operations.collection.undo`) restores the note, and the editor
reloads it. Caveats: use the menu item — Cmd+Z with focus inside the field goes
to the webview, not the menu; in the Add window nothing is saved to the
collection, so there is nothing to undo; undoing rolls back the whole note (all
fields), not just the one edit.

### 4. Addon-level snapshot/restore (Python hooks — all verified at 25.02.5)

Feasible with stock hooks (signatures from
[qt/tools/genhooks_gui.py](https://github.com/ankitects/anki/blob/25.02.5/qt/tools/genhooks_gui.py)):

- `editor_did_load_note(editor: aqt.editor.Editor)` — seed the snapshot ring.
- `editor_did_fire_typing_timer(note: anki.notes.Note)` — fires after each
  600 ms save; `note.fields` already holds the _new_ text, so keep a ring of
  the last N revisions per `(note_id, field)` and push before overwriting.
- `editor_did_unfocus_field(changed: bool, note, current_field_idx: int)` —
  same, on blur; returning `True` makes Anki reload the note, which is the
  sanctioned way to push a restored value back into the webview.
- Restore path: set `note.fields[idx]` to the last snapshot containing
  `<anki-mathjax` (or just the previous revision) and call
  `editor.loadNoteKeepingFocus()`; bind it via `editor_did_init_shortcuts`.

This is the only workaround that gives targeted "resurrect my formula"
recovery in the Add window without touching JS.

### 5. JS-level interception in the editor webview

Two delivery mechanisms:

- `webview_will_set_content(web_content, context)` + `mw.addonManager.setWebExports()`
  — note the editor page's CSP allows scripts **only** from
  `/_anki/` and `/_addons/` (no inline scripts):
  [qt/aqt/mediasrv.py#L749-L760](https://github.com/ankitects/anki/blob/25.02.5/qt/aqt/mediasrv.py#L749-L760).
- `editor.web.eval(js)` (`AnkiWebView.eval`,
  [qt/aqt/webview.py#L727-L731](https://github.com/ankitects/anki/blob/25.02.5/qt/aqt/webview.py#L727-L731))
  — `QWebEnginePage.runJavaScript` is not blocked by the page CSP; Anki itself
  drives the editor this way (e.g. `saveNow`).

What the injected JS can hook: the rich-text input exposes a Svelte lifecycle
API to addons via `require("anki/RichTextInput")`
([RichTextInput.svelte#L48-L53](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/rich-text-input/RichTextInput.svelte#L48-L53)).
`lifecycle.onMount((api) => ...)` gives each field's `api.inputHandler`, whose
`beforeInput` handler list receives the raw `beforeinput` event
([ts/lib/sveltelib/input-handler.ts#L40-L46](https://github.com/ankitects/anki/blob/25.02.5/ts/lib/sveltelib/input-handler.ts#L40-L46);
`HandlerList.on(handler)` returns an un-hook callback,
[handler-list.ts#L90-L96](https://github.com/ankitects/anki/blob/25.02.5/ts/lib/sveltelib/handler-list.ts#L90-L96)).
A handler can check `event.inputType` (`deleteContentBackward` /
`deleteContentForward`) and whether `event.getTargetRanges()` / the selection
touches an `anki-frame` / `anki-mathjax` node, then `event.preventDefault()` to
require a confirming second keypress — or record the frame's outerHTML in a
per-field JS undo ring before letting the delete through. Note the
contenteditable lives inside an **open** shadow root per field
([RichTextInput.svelte#L101-L103](https://github.com/ankitects/anki/blob/25.02.5/ts/editor/rich-text-input/RichTextInput.svelte#L101-L103)),
so `document.querySelector` won't reach it directly — go through the
RichTextInput API (`api.element` resolves to the `anki-editable` element).

## Recommendation

For pure prevention, workaround 1 (disable MathJax preview) is the
maintainer-suggested zero-cost option. For recovery as-it-happens, teach users
workaround 2 (Ctrl+Shift+X, Cmd+Z inside the HTML editor) — it needs no code
and already works in every editor window. If building tooling, workaround 4
(Python snapshot ring on `editor_did_fire_typing_timer` /
`editor_did_unfocus_field`, restore via `loadNoteKeepingFocus`) is the most
robust: it uses only stable public hooks and works in the Add window;
workaround 5 is strictly an enhancement (guarding the delete keystroke) and
carries more upkeep risk because `anki/RichTextInput` internals are not a
stability-guaranteed API.

## Open questions / not verified

- **Not reproduced live**: the analysis is source-based; I did not step through
  Chromium's `UndoStack` in the Qt webview to watch the entry get orphaned.
  The observable symptom (undo restores nothing) matches the mechanism and the
  upstream reports, including a 25.02-specific report in
  [#1941](https://github.com/ankitects/anki/issues/1941) (comment of
  2025-02-21).
- **Undo-entry coalescing**: whether the Rust backend merges consecutive
  "Update Note" ops from the typing timer (affecting how far Edit→Undo steps
  back) was not verified — `rslib` undo internals weren't inspected.
- **Redo asymmetries** in #2429 (why some sequences partially undo) were not
  traced individually; claim 4's mechanisms plausibly cover them but each GIF
  in that issue wasn't reproduced.
- Whether `editor_did_fire_typing_timer` can observe the pre-deletion text
  directly (it cannot — the note is already mutated when it fires), so a
  snapshot addon must keep history itself; the exact ring-depth/UX is design
  work, not verified behavior.
