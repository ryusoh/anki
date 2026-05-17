import re
import os
from aqt import gui_hooks
from aqt.editor import Editor
from aqt.utils import tooltip

from .utils import clean_html_text, fetch_image_results, build_image_html

ADDON_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(ADDON_DIR, "icon.png")

# Cache: query -> {"urls": [...], "index": int}
_image_cache = {}

_AUTO_IMAGE_MARKER = 'class="auto-image"'
_AUTO_IMAGE_PATTERN = re.compile(r'<div class="auto-image">.*?</div>')


def _apply_image(editor, text_to_search):
    """Fetch an image result and append/replace it in the Back field."""
    text = clean_html_text(text_to_search)
    if not text:
        tooltip("No text found to search images.")
        return

    # Get or use cached results
    if text in _image_cache:
        cache = _image_cache[text]
        cache["index"] = (cache["index"] + 1) % len(cache["urls"])
    else:
        urls = fetch_image_results(text)
        if not urls:
            tooltip(f"No image found for '{text}'.")
            return
        _image_cache[text] = {"urls": urls, "index": 0}

    cache = _image_cache[text]
    image_url = cache["urls"][cache["index"]]
    img_html = build_image_html(image_url)

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

    current_back = editor.note.fields[back_idx]

    wrapped_img = f'<div class="auto-image">{img_html}</div>'

    # If there's already an auto-image div, replace it
    if _AUTO_IMAGE_PATTERN.search(current_back):
        editor.note.fields[back_idx] = _AUTO_IMAGE_PATTERN.sub(wrapped_img, current_back)
    else:
        clean_back = current_back.strip()
        if clean_back and clean_back not in ('', '<br>', '<br/>', '<br />', '<div><br></div>'):
            editor.note.fields[back_idx] = f"{current_back}{wrapped_img}"
        else:
            editor.note.fields[back_idx] = wrapped_img

    if not editor.addMode:
        try:
            editor.note.flush()
        except Exception as e:
            print(f"Error flushing note: {e}")
    try:
        editor.loadNoteKeepingFocus()
    except Exception as e:
        print(f"Error loading note: {e}")

    idx = cache["index"] + 1
    total = len(cache["urls"])
    tooltip(f"Image {idx}/{total} for '{text}'.")


def on_auto_image(editor: Editor) -> None:
    """Button handler: Get selected text or Front field, then fetch image."""
    if editor.note is None:
        return

    editor.web.evalWithCallback(
        "window.getSelection().toString()",
        lambda sel: _on_selection_result(editor, sel)
    )


def _on_selection_result(editor: Editor, sel: str) -> None:
    if sel and sel.strip():
        editor.saveNow(lambda: _apply_image(editor, sel))
    else:
        editor.saveNow(lambda: _use_front_field(editor))


def _use_front_field(editor: Editor) -> None:
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
    _apply_image(editor, front_text)


def on_editor_did_init_buttons(buttons: list, editor: Editor) -> None:
    btn = editor.addButton(
        ICON_PATH,
        "autoImage",
        on_auto_image,
        tip="Auto Image: fetch Google Image for selected text or Front field and append to Back field",
    )
    buttons.append(btn)


gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
