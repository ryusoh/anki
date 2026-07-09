# Auto Markdown — Anki Editor Addon
# Button in the editor that converts markdown-formatted text in
# Front and Back fields to rendered HTML (headings, bold, code, lists, etc.).

from __future__ import annotations

from aqt import gui_hooks  # type: ignore
from aqt.editor import Editor  # type: ignore
from aqt.utils import tooltip  # type: ignore

from .core import convert_markdown_field


def _apply_markdown(editor: Editor) -> None:
    """Read Front and Back fields, convert markdown, write back."""
    if editor.note is None:
        return

    keys = editor.note.keys()
    changed = False

    for i, name in enumerate(keys):
        if name.lower() in ("front", "back"):
            original = editor.note.fields[i]
            converted = convert_markdown_field(original)
            if converted != original:
                editor.note.fields[i] = converted
                changed = True

    if not changed:
        tooltip("No markdown to convert.")
        return

    if not editor.addMode:
        try:
            editor.note.flush()
        except Exception as e:
            print(f"Error flushing note in auto_markdown: {e}")
    try:
        editor.loadNoteKeepingFocus()
    except Exception as e:
        print(f"Error loading note in auto_markdown: {e}")

    tooltip("Converted markdown to HTML.")


def on_auto_markdown(editor: Editor) -> None:
    """Button handler: save pending edits, then convert markdown."""
    if editor.note is None:
        return
    editor.saveNow(lambda: _apply_markdown(editor))


def on_editor_did_init_buttons(buttons: list, editor: Editor) -> None:
    btn = editor.addButton(
        None,
        "autoMarkdown",
        on_auto_markdown,
        tip="Auto Markdown: convert markdown syntax to HTML in Front and Back fields",
        label="Md",
    )
    buttons.append(btn)


gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
