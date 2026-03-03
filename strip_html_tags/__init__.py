# Strip HTML Tags Button — Anki Editor Addon
# Adds a toolbar button to strip all HTML tags from selected text.

import os
from aqt import gui_hooks
from aqt.editor import Editor

ADDON_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(ADDON_DIR, "icon.png")

STRIP_JS = r"""
(function() {
    var focusedField = document.activeElement;
    if (!focusedField) return;

    var editable = null;
    var root = null;

    if (focusedField.shadowRoot) {
        editable = focusedField.shadowRoot.querySelector('anki-editable');
        root = focusedField.shadowRoot;
    }
    if (!editable) {
        var container = focusedField.closest('.editor-field');
        if (container && container.shadowRoot) {
            editable = container.shadowRoot.querySelector('anki-editable');
            root = container.shadowRoot;
        }
    }
    if (!editable) {
        if (focusedField.tagName &&
            focusedField.tagName.toLowerCase() === 'anki-editable') {
            editable = focusedField;
            root = focusedField.getRootNode();
        }
    }
    if (!editable) {
        var fields = document.querySelectorAll('[contenteditable="true"]');
        if (fields.length > 0) {
            for (var i = 0; i < fields.length; i++) {
                if (fields[i].contains(document.activeElement) ||
                    fields[i] === document.activeElement) {
                    editable = fields[i];
                    root = document;
                    break;
                }
            }
            if (!editable) {
                editable = fields[0];
                root = document;
            }
        }
    }
    if (!editable) return;

    var sel = null;
    if (root && root.getSelection) {
        sel = root.getSelection();
    } else if (window.getSelection) {
        sel = window.getSelection();
    }

    if (sel && sel.rangeCount > 0 && !sel.isCollapsed) {
        var range = sel.getRangeAt(0);
        var fragment = range.cloneContents();
        var div = document.createElement('div');
        div.appendChild(fragment);
        var plainText = div.textContent || div.innerText || '';
        range.deleteContents();
        range.insertNode(document.createTextNode(plainText));
        sel.collapseToEnd();
    } else {
        var html = editable.innerHTML;
        var parser = new DOMParser();
        var doc = parser.parseFromString(html, 'text/html');
        var text = doc.body.textContent || '';
        editable.innerHTML = text;
    }

    editable.dispatchEvent(new Event('input', { bubbles: true }));
})();
"""


def on_strip_html(editor):
    editor.web.eval(STRIP_JS)


def on_editor_did_init_buttons(buttons, editor):
    btn = editor.addButton(
        ICON_PATH,
        "stripHtmlTags",
        on_strip_html,
        tip="Strip HTML tags from selection (Ctrl+Shift+R)",
    )
    buttons.append(btn)


gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
