from aqt import mw
from aqt.editor import Editor
from aqt.gui_hooks import editor_did_load_note
from aqt.browser import Browser
from .core import extract_search_terms
import json

JS_HIGHLIGHT_SCRIPT = """
(function() {
    const terms = %s;
    if (!terms || terms.length === 0) return;

    // We inject a CSS rule directly into the head if not exists
    if (!document.getElementById('search-highlight-style')) {
        const style = document.createElement('style');
        style.id = 'search-highlight-style';
        style.textContent = `
            .search-highlight {
                border-bottom: 2px solid #00bcd4;
                background-color: rgba(0, 188, 212, 0.15);
                border-radius: 2px;
                font-weight: 600;
            }
        `;
        document.head.appendChild(style);
    }

    // Modern Anki (2.1.50+) Svelte editor uses shadow DOM for rich text fields.
    // CSS Custom Highlights API is the best and non-destructive approach!
    if (CSS && CSS.highlights) {
        // Clear previous highlight ranges if any
        if (CSS.highlights.has('search-matches')) {
             CSS.highlights.delete('search-matches');
        }

        const highlightRanges = new Highlight();
        const escapedTerms = terms.map(t => t.replace(/[.*+?^${}()|[\]\\\\]/g, '\\\\$&'));
        const regex = new RegExp(`(${escapedTerms.join('|')})`, 'gi');

        function findRanges(element) {
            const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
            let node;
            while (node = walker.nextNode()) {
                let match;
                regex.lastIndex = 0;
                while ((match = regex.exec(node.nodeValue)) !== null) {
                    const range = new Range();
                    range.setStart(node, match.index);
                    range.setEnd(node, match.index + match[0].length);
                    highlightRanges.add(range);
                }
            }
        }

        // Wait for Svelte editor fields to load
        setTimeout(() => {
            const roots = document.querySelectorAll('.editing-area, anki-editable, .field');
            roots.forEach(root => {
                if (root.shadowRoot) {
                    findRanges(root.shadowRoot);
                } else {
                    findRanges(root);
                }
            });
            CSS.highlights.set('search-matches', highlightRanges);

            if (!document.getElementById('search-highlight-api-style')) {
                const style = document.createElement('style');
                style.id = 'search-highlight-api-style';
                style.textContent = `
                    ::highlight(search-matches) {
                        background-color: rgba(0, 188, 212, 0.15);
                        border-bottom: 2px solid #00bcd4;
                        color: inherit;
                        font-weight: 600;
                    }
                `;
                document.head.appendChild(style);
            }
        }, 300);
        return;
    }

    // Fallback function to highlight text nodes inside elements safely
    function highlightTextNodes(element, terms) {
        if (!element || element.nodeType !== Node.ELEMENT_NODE) return;

        const escapedTerms = terms.map(t => t.replace(/[.*+?^${}()|[\]\\\\]/g, '\\\\$&'));
        const regex = new RegExp(`(${escapedTerms.join('|')})`, 'gi');

        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
        const nodes = [];
        let node;
        while (node = walker.nextNode()) nodes.push(node);

        nodes.forEach(textNode => {
            const parent = textNode.parentNode;

            if (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE' || parent.classList.contains('search-highlight')) return;

            const text = textNode.nodeValue;
            if (!regex.test(text)) return;

            regex.lastIndex = 0;
            let match;
            let lastIndex = 0;
            const fragment = document.createDocumentFragment();

            while ((match = regex.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    fragment.appendChild(document.createTextNode(text.substring(lastIndex, match.index)));
                }

                const span = document.createElement('span');
                span.className = 'search-highlight';
                span.textContent = match[0];

                // CRITICAL FOR ANKI: Add data attributes so Anki ignores it/strips it when saving
                // We add multiple common attributes to attempt to signal this is not part of the actual note
                span.setAttribute('data-rich-text-format', 'true');
                span.setAttribute('data-search-highlight', 'true');
                span.setAttribute('contenteditable', 'false'); // Prevents user editing the highlight itself

                fragment.appendChild(span);
                lastIndex = regex.lastIndex;
            }

            if (lastIndex < text.length) {
                fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
            }

            parent.replaceChild(fragment, textNode);
        });
    }

    // Wait for older editor fields to load
    setTimeout(() => {
        const editables = document.querySelectorAll('anki-editable, .field, .editing-area');
        editables.forEach(field => {
            const root = field.shadowRoot ? field.shadowRoot : field;
            highlightTextNodes(root, terms);
        });
    }, 300);
})();
"""

def on_editor_did_load_note(editor: Editor) -> None:
    if not isinstance(editor.parentWindow, Browser):
        return

    browser = editor.parentWindow
    query = browser.form.searchEdit.text()

    terms = extract_search_terms(query)
    if not terms:
        return

    script = JS_HIGHLIGHT_SCRIPT % json.dumps(terms)
    editor.web.eval(script)

def init_editor():
    editor_did_load_note.append(on_editor_did_load_note)
