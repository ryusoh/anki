# Strip HTML Tags Button — Anki Editor Addon
# Strips HTML tags from selected text, or whole field if nothing selected.
#
# How it works:
#   1. JS checks document.getSelection().toString() for selected text
#   2. If selected: sends selected text to Python via pycmd
#      → Python finds matching HTML in field data, strips only that portion
#   3. If no selection: Python strips the entire current field

import html as html_module
import os
import re

from aqt import gui_hooks
from aqt.editor import Editor

ADDON_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(ADDON_DIR, "icon.png")

# JS: get selection text and send to Python, or request whole-field strip
GET_SELECTION_JS = """
(function() {
    var sel = document.getSelection();
    var text = sel ? sel.toString() : '';
    if (text.length > 0) {
        // Send selected text to Python for smart partial stripping
        pycmd('stripHtmlSel:' + text);
    } else {
        // No selection — strip whole field
        pycmd('stripHtmlAll');
    }
})();
"""


def _render_text(html_str):
    """Convert HTML to plain text by removing tags and unescaping entities."""
    # Insert a space for block-level tags so text doesn't merge across blocks
    block_re = r'</?(?:p|div|br|hr|li|ul|ol|tr|td|th|blockquote|h[1-6]|pre|table|thead|tbody|tfoot|dl|dt|dd)\b[^>]*>'
    text = re.sub(block_re, ' ', html_str, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = html_module.unescape(text)
    # Collapse runs of whitespace
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _find_mismatches(sel_normalized, rendered_normalized):
    idx = rendered_normalized.find(sel_normalized)
    if idx == -1:
        import sys

        print("====== STRIP_HTML_DEBUG: Mismatch ======", file=sys.stderr)
        print(f"sel_normalized: [{sel_normalized}]", file=sys.stderr)
        print(f"rendered: [{rendered_normalized}]", file=sys.stderr)
        for i in range(min(len(sel_normalized), len(rendered_normalized))):
            if i < len(rendered_normalized) and sel_normalized[i] != rendered_normalized[i]:
                print(
                    f"Mismatch at index {i}: selected='{sel_normalized[i]}' ({ord(sel_normalized[i])}), rendered='{rendered_normalized[i]}' ({ord(rendered_normalized[i])})",
                    file=sys.stderr,
                )
                start_c = max(0, i - 10)
                end_c_sel = min(len(sel_normalized), i + 10)
                end_c_ren = min(len(rendered_normalized), i + 10)
                print(f"Context sel: {sel_normalized[start_c:end_c_sel]}", file=sys.stderr)
                print(f"Context ren: {rendered_normalized[start_c:end_c_ren]}", file=sys.stderr)
                break
        print("========================================", file=sys.stderr)
        return None
    return idx


def _is_only_tags_between(s, start_idx, end_idx):
    if start_idx >= end_idx:
        return True
    slice_str = s[start_idx:end_idx]
    rendered_slice = re.sub(r'<[^>]+>', '', slice_str)
    rendered_slice = html_module.unescape(rendered_slice)
    return not bool(re.sub(r'[\s\xa0\u2000-\u200a\u200b\u200c\u200d\ufeff]+', '', rendered_slice))


def _expand_left(html_str, html_start):
    safe_html_start = html_start
    needs_block_wrapper = False
    while safe_html_start > 0:
        prev_tag_open = html_str.rfind('<', 0, safe_html_start)
        if prev_tag_open == -1:
            break

        if _is_only_tags_between(html_str, prev_tag_open, html_start):
            tag_content = html_str[prev_tag_open : html_str.find('>', prev_tag_open) + 1]
            match = re.match(r'<\s*([a-zA-Z0-9]+)', tag_content)
            if match:
                tag_name = match.group(1).lower()
                if tag_name in ['li', 'td', 'th', 'tr', 'ul', 'ol', 'div']:
                    break
                if tag_name in ['p', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    needs_block_wrapper = True
                    safe_html_start = prev_tag_open
                    break
            safe_html_start = prev_tag_open
        else:
            break
    return safe_html_start, needs_block_wrapper


def _expand_right(html_str, html_end, needs_block_wrapper):
    safe_html_end = html_end
    while safe_html_end < len(html_str):
        next_tag_close = html_str.find('>', safe_html_end)
        if next_tag_close == -1:
            break

        if _is_only_tags_between(html_str, html_end, next_tag_close + 1):
            tag_content = html_str[safe_html_end : next_tag_close + 1]
            match = re.search(r'<\s*/?\s*([a-zA-Z0-9]+)', tag_content)
            if match:
                tag_name = match.group(1).lower()
                if not tag_content.startswith('</'):
                    if tag_name in [
                        'li',
                        'td',
                        'th',
                        'tr',
                        'ul',
                        'ol',
                        'div',
                        'p',
                        'blockquote',
                        'h1',
                        'h2',
                        'h3',
                        'h4',
                        'h5',
                        'h6',
                    ]:
                        break
                if tag_name in ['li', 'td', 'th', 'tr', 'ul', 'ol', 'div']:
                    break
                if tag_name in ['p', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    needs_block_wrapper = True
                    safe_html_end = next_tag_close + 1
                    break
                if tag_name in ['br', 'hr']:
                    safe_html_end = next_tag_close + 1
                    continue
            safe_html_end = next_tag_close + 1
        else:
            break
    return safe_html_end, needs_block_wrapper


def _map_html_to_text(html_str):
    BLOCK_TAGS = {
        'p',
        'div',
        'br',
        'hr',
        'li',
        'ul',
        'ol',
        'tr',
        'td',
        'th',
        'blockquote',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'pre',
        'table',
        'thead',
        'tbody',
        'tfoot',
        'dl',
        'dt',
        'dd',
    }

    text_pos = 0
    text_to_html = {}
    in_tag = False
    tag_buf = ''
    i = 0
    rendered_chars = []

    while i < len(html_str):
        if html_str[i] == '<':
            in_tag = True
            tag_buf = ''
            i += 1
            continue
        elif html_str[i] == '>':
            in_tag = False
            tag_match = re.match(r'/?\s*([a-zA-Z0-9]+)', tag_buf)
            if tag_match and tag_match.group(1).lower() in BLOCK_TAGS:
                if rendered_chars and not re.match(r'[\s\xa0]', rendered_chars[-1]):
                    text_to_html[text_pos] = i + 1
                    rendered_chars.append(' ')
                    text_pos += 1
            i += 1
            continue

        if in_tag:
            tag_buf += html_str[i]
            i += 1
            continue

        if html_str[i] == '&':
            end_idx = html_str.find(';', i)
            if end_idx != -1 and end_idx - i < 10:
                entity = html_str[i : end_idx + 1]
                unescaped = html_module.unescape(entity)
                for unescaped_char in unescaped:
                    if unescaped_char not in ['\u200b', '\u200c', '\u200d', '\ufeff']:
                        text_to_html[text_pos] = i
                        rendered_chars.append(unescaped_char)
                        text_pos += 1
                i = end_idx + 1
                continue

        if html_str[i] not in ['\u200b', '\u200c', '\u200d', '\ufeff']:
            text_to_html[text_pos] = i
            rendered_chars.append(html_str[i])
            text_pos += 1
        i += 1

    return text_to_html, rendered_chars


def _normalize_rendered_chars(rendered_chars):
    rendered = ''.join(rendered_chars)
    norm_pos = 0
    norm_to_text = {}
    norm_chars = []

    in_whitespace = False
    for t_pos, ch in enumerate(rendered):
        if re.match(r'[\s\xa0\u2000-\u200a]', ch):
            if not in_whitespace:
                norm_to_text[norm_pos] = t_pos
                norm_chars.append(' ')
                norm_pos += 1
                in_whitespace = True
        else:
            in_whitespace = False
            norm_to_text[norm_pos] = t_pos
            norm_chars.append(ch)
            norm_pos += 1

    return ''.join(norm_chars), norm_to_text


def _strip_selection(html_str, selected_text):
    """Strip HTML tags only from the portion of html_str that renders as selected_text.

    Returns the modified HTML, or None if the selection can't be mapped.
    """
    # 1. Remove zero-width spaces and other invisible formatting characters
    sel_normalized = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', selected_text)
    # 2. Normalize ALL unicode spaces (including &nbsp; \xa0 and EN SPACE \u2002) to standard space
    sel_normalized = re.sub(r'[\s\xa0\u2000-\u200a]+', ' ', sel_normalized).strip()

    if not sel_normalized:
        return None

    text_to_html, rendered_chars = _map_html_to_text(html_str)
    rendered_normalized, norm_to_text = _normalize_rendered_chars(rendered_chars)

    idx = _find_mismatches(sel_normalized, rendered_normalized)
    if idx is None:
        return None

    start_norm_pos = idx
    end_norm_pos = idx + len(sel_normalized) - 1

    start_text_pos = norm_to_text.get(start_norm_pos)
    end_text_pos = norm_to_text.get(end_norm_pos)

    if start_text_pos is None or end_text_pos is None:
        return None

    html_start = text_to_html.get(start_text_pos)
    last_html_start = text_to_html.get(end_text_pos)

    if html_start is None or last_html_start is None:
        return None

    html_end = last_html_start
    if html_str[html_end] == '&':
        end_idx = html_str.find(';', html_end)
        if end_idx != -1 and end_idx - html_end < 10:
            html_end = end_idx + 1
        else:
            html_end += 1
    else:
        html_end += 1

    # --- SMART TAG EXPANSION WITH BLOCK REPLACEMENT ---
    safe_html_start, needs_block_wrapper = _expand_left(html_str, html_start)
    safe_html_end, needs_block_wrapper = _expand_right(html_str, html_end, needs_block_wrapper)

    html_slice = html_str[safe_html_start:safe_html_end]
    stripped = re.sub(r'<[^>]+>', '', html_slice)
    stripped = html_module.unescape(stripped)

    # Wrap in <div> ONLY if we removed a block wrapper so it doesn't merge with adjacent blocks
    if needs_block_wrapper:
        stripped = f"<div>{stripped}</div>"

    return html_str[:safe_html_start] + stripped + html_str[safe_html_end:]


def _strip_field(editor, new_html=None):
    """Set field content and reload."""
    if editor.note is None or editor.currentField is None:
        return
    idx = editor.currentField
    if idx < 0 or idx >= len(editor.note.fields):
        return

    if new_html is None:
        # Strip whole field
        html_str = editor.note.fields[idx]
        new_html = _render_text(html_str)
        if new_html == html_str:
            return

    editor.note.fields[idx] = new_html
    if not editor.addMode:
        try:
            editor.note.flush()
        except Exception as e:
            import sys

            print(f"Error flushing note in strip_html_tags: {e}", file=sys.stderr)
    try:
        editor.loadNoteKeepingFocus()
    except Exception as e:
        import sys

        print(f"Error loading note in strip_html_tags: {e}", file=sys.stderr)


def on_strip_html(editor: Editor) -> None:
    """Button handler: run JS to detect selection."""
    editor.web.eval(GET_SELECTION_JS)


def on_js_message(handled, message, context):
    """Handle pycmd from JS."""
    if not isinstance(message, str):
        return handled

    if message == 'stripHtmlAll':
        # No selection — strip whole field
        if isinstance(context, Editor):
            _strip_field(context)
        return (True, None)

    if message.startswith('stripHtmlSel:'):
        # Selection — try smart partial strip, fall back to whole field
        selected_text = message[len('stripHtmlSel:') :]
        if isinstance(context, Editor) and context.note and context.currentField is not None:
            idx = context.currentField
            if 0 <= idx < len(context.note.fields):
                html_str = context.note.fields[idx]
                result = _strip_selection(html_str, selected_text)
                if result is not None:
                    _strip_field(context, result)
                else:
                    # Couldn't map selection — strip whole field
                    _strip_field(context)
        return (True, None)

    return handled


def on_editor_did_init_buttons(buttons: list, editor: Editor) -> None:
    btn = editor.addButton(
        ICON_PATH,
        "stripHtmlTags",
        on_strip_html,
        tip="Strip HTML tags (selection or whole field)",
    )
    buttons.append(btn)


gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
gui_hooks.webview_did_receive_js_message.append(on_js_message)
