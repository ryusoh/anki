import html
import os
import re

from aqt import gui_hooks
from aqt.editor import Editor

from .utils import (
    fetch_itaigi_json,
    format_itaigi_result,
    lookup_itaigi,
    merge_itaigi_result,
    parse_itaigi_json,
    save_audio_to_media,
)

ADDON_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(ADDON_DIR, "icon.png")


def _clean_html_text(html_text: str) -> str:
    """Strip HTML tags and entities to get the raw search text."""
    if not html_text:
        return ""
    text = re.sub(r"<br\s*/?>", " ", html_text)
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = " ".join(text.split())
    return text


def _apply_itaigi(editor: Editor, text_to_search: str) -> None:
    """Fetch the iTaigi entry (or MOEDiCT / ChhoeTaigi fallbacks) and prepend it to the Back field."""
    from aqt.utils import tooltip

    text = _clean_html_text(text_to_search)
    if not text:
        tooltip("No text found to search iTaigi.")
        return

    parsed = lookup_itaigi(text)
    if parsed is None:
        tooltip(f"Word '{text}' not found in iTaigi or fallbacks.")
        return

    tailo, mandarin, fallback_audio_url = parsed

    if editor.note is None:
        return

    back_idx = -1
    for i, name in enumerate(editor.note.keys()):
        if name.lower() == "back":
            back_idx = i
            break

    if back_idx == -1:
        tooltip("No 'Back' field found in this note type.")
        return

    audio_filename = save_audio_to_media(
        tailo, fallback_url=fallback_audio_url
    )
    new_html = format_itaigi_result(tailo, mandarin, audio_filename)
    if new_html is None:
        tooltip(f"No iTaigi result to add for '{text}'.")
        return

    current_back = editor.note.fields[back_idx]
    editor.note.fields[back_idx] = merge_itaigi_result(current_back, new_html)

    if not editor.addMode:
        try:
            editor.note.flush()
        except Exception as e:
            print(f"Error flushing note: {e}")
    try:
        editor.loadNoteKeepingFocus()
    except Exception as e:
        print(f"Error loading note: {e}")

    tooltip(f"Added '{text}' from iTaigi to Back field.")


def on_auto_itaigi(editor: Editor) -> None:
    """Button handler: get selected text or Front field, then fetch."""
    if editor.note is None:
        return

    editor.web.evalWithCallback(
        "window.getSelection().toString()",
        lambda sel: _on_selection_result(editor, sel),
    )


def _on_selection_result(editor: Editor, sel: str) -> None:
    if sel and sel.strip():
        editor.saveNow(lambda: _apply_itaigi(editor, sel))
    else:
        editor.saveNow(lambda: _use_front_field(editor))


def _use_front_field(editor: Editor) -> None:
    from aqt.utils import tooltip

    if editor.note is None:
        return

    front_idx = -1
    for i, name in enumerate(editor.note.keys()):
        if name.lower() == "front":
            front_idx = i
            break

    if front_idx == -1:
        tooltip("No 'Front' field found to use as default.")
        return

    front_text = editor.note.fields[front_idx]
    _apply_itaigi(editor, front_text)


def on_editor_did_init_buttons(buttons: list, editor: Editor) -> None:
    btn = editor.addButton(
        ICON_PATH,
        "autoItaigi",
        on_auto_itaigi,
        tip="Auto iTaigi: fetch Taiwanese Hokkien entry for selected text or Front field and append to Back field",
    )
    buttons.append(btn)


gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
