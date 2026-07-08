"""Editor button that reflows hard-wrapped PDF paste into normal paragraphs.

Applies to the currently focused field, falling back to the Back field.
Dictionary-format fields (line-per-item word lists) are left untouched by
the core heuristic — see core.py.
"""

# Anki bundles Python 3.9: `int | None` annotations only exist there as
# strings, so postponed evaluation is required for the module to import.
from __future__ import annotations

from aqt import gui_hooks
from aqt.editor import Editor
from aqt.utils import tooltip

from .core import reflow_field_html


def _target_field_index(editor: Editor) -> int | None:
    idx = getattr(editor, "currentField", None)
    if isinstance(idx, int):
        return idx
    for i, name in enumerate(editor.note.keys()):
        if name.lower() == "back":
            return i
    return None


def _apply_reflow(editor: Editor) -> None:
    if editor.note is None:
        return

    idx = _target_field_index(editor)
    if idx is None:
        tooltip("No field focused and no 'Back' field found.")
        return

    original = editor.note.fields[idx]
    reflowed = reflow_field_html(original)
    if reflowed == original:
        tooltip("Nothing to reflow.")
        return

    editor.note.fields[idx] = reflowed

    if not editor.addMode:
        try:
            editor.note.flush()
        except Exception as e:
            print(f"Error flushing note: {e}")
    try:
        editor.loadNoteKeepingFocus()
    except Exception as e:
        print(f"Error loading note: {e}")

    tooltip("Reflowed hard-wrapped paragraph.")


def on_reflow_paragraphs(editor: Editor) -> None:
    """Button handler: save pending edits, then reflow the target field."""
    if editor.note is None:
        return
    editor.saveNow(lambda: _apply_reflow(editor))


def on_editor_did_init_buttons(buttons: list, editor: Editor) -> None:
    btn = editor.addButton(
        None,
        "reflowParagraphs",
        on_reflow_paragraphs,
        tip="Reflow Paragraphs: join hard-wrapped PDF lines in the focused field (or Back)",
        label="¶",
    )
    buttons.append(btn)


gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
