import os
from aqt import gui_hooks
from aqt.editor import Editor
from aqt.utils import tooltip

from .utils import clean_html_text, detect_language, fetch_wiktionary_html, parse_wiktionary_html, merge_definition

ADDON_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(ADDON_DIR, "icon.png")

def _apply_wiktionary(editor, text_to_search):
    """
    Fetch the Wiktionary definition and append it to the Back field.
    """
    text = clean_html_text(text_to_search)
    if not text:
        tooltip("No text found to search Wiktionary.")
        return

    lang = detect_language(text)

    # Try fetching definition
    html_res = fetch_wiktionary_html(text, lang)
    if not html_res:
        tooltip(f"Word '{text}' not found in {lang}.wiktionary.")
        return
    elif html_res.startswith("Error:"):
        tooltip(f"Wiktionary API {html_res}")
        return

    parsed_definition = parse_wiktionary_html(html_res, lang)

    if not parsed_definition:
        tooltip(f"Could not parse definition for '{text}'.")
        return

    # Append to Back field
    if editor.note is None:
        return

    # Find the "Back" field index
    back_idx = -1
    for i, name in enumerate(editor.note.keys()):
        if name.lower() == "back":
            back_idx = i
            break

    if back_idx == -1:
        tooltip("No 'Back' field found in this note type.")
        return

    current_back = editor.note.fields[back_idx]

    # Prepend with newlines
    new_back = merge_definition(current_back, parsed_definition)

    editor.note.fields[back_idx] = new_back

    # Save changes
    if not editor.addMode:
        try:
            editor.note.flush()
        except Exception:
            pass
    try:
        editor.loadNoteKeepingFocus()
    except Exception:
        pass

    tooltip(f"Added definition for '{text}' to Back field.")


def on_auto_wiktionary(editor: Editor) -> None:
    """Button handler: Get selected text or Front field, then fetch."""
    if editor.note is None:
        return

    # First, let's try to get selected text.
    # We evaluate JS to get the current selection HTML.
    editor.web.evalWithCallback(
        "window.getSelection().toString()",
        lambda sel: _on_selection_result(editor, sel)
    )

def _on_selection_result(editor: Editor, sel: str) -> None:
    if sel and sel.strip():
        # User selected some text, use it.
        # We need to ensure the current note fields are saved from webview first
        editor.saveNow(lambda: _apply_wiktionary(editor, sel))
    else:
        # No selection, use the Front field content.
        # Ensure note is saved from webview
        editor.saveNow(lambda: _use_front_field(editor))

def _use_front_field(editor: Editor) -> None:
    if editor.note is None:
        return

    # Find the "Front" field index
    front_idx = -1
    for i, name in enumerate(editor.note.keys()):
        if name.lower() == "front":
            front_idx = i
            break

    if front_idx == -1:
        tooltip("No 'Front' field found to use as default.")
        return

    front_text = editor.note.fields[front_idx]
    _apply_wiktionary(editor, front_text)

def on_editor_did_init_buttons(buttons: list, editor: Editor) -> None:
    btn = editor.addButton(
        ICON_PATH,
        "autoWiktionary",
        on_auto_wiktionary,
        tip="Auto Wiktionary: fetch definition for selected text or Front field and append to Back field",
    )
    buttons.append(btn)


gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
