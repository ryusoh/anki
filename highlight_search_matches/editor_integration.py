from aqt import mw
from aqt.editor import Editor
from aqt.gui_hooks import editor_did_load_note, browser_did_search
from aqt.browser import Browser
from .core import extract_search_terms
import json

_last_search_query = ""

def on_browser_did_search(search_context):
    global _last_search_query
    _last_search_query = search_context.search

def on_editor_did_load_note(editor: Editor) -> None:
    global _last_search_query
    
    if not isinstance(editor.parentWindow, Browser):
        return

    browser = editor.parentWindow
    
    try:
        search_edit = browser.form.searchEdit
        query = search_edit.currentText() if hasattr(search_edit, 'currentText') else search_edit.text()
        if not query or not query.strip():
            query = _last_search_query
    except Exception:
        query = _last_search_query

    terms = extract_search_terms(query)
    if not terms:
        return

    terms_json = json.dumps(terms)

    # Highlight using CSS highlights API (modern browsers) + fallback
    script = f"""
(function() {{
    const terms = {terms_json};
    if (!terms || terms.length === 0) return;
    
    // Remove existing highlights
    if (CSS.highlights && CSS.highlights.has('hsm')) {{
        CSS.highlights.delete('hsm');
    }}
    document.getElementById('hsm-style')?.remove();
    
    const escapeRegex = (s) => s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
    const regex = new RegExp('(' + terms.map(escapeRegex).join('|') + ')', 'gi');
    
    function findRanges(root) {{
        const ranges = [];
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
        let node;
        while (node = walker.nextNode()) {{
            const text = node.nodeValue;
            if (!text || text.trim().length === 0) continue;
            regex.lastIndex = 0;
            let match;
            while ((match = regex.exec(text)) !== null) {{
                const range = new Range();
                range.setStart(node, match.index);
                range.setEnd(node, match.index + match[0].length);
                ranges.push(range);
            }}
        }}
        return ranges;
    }}
    
    function applyHighlights() {{
        if (!CSS.highlights) {{
            console.log('[hsm] CSS Highlights not supported');
            return;
        }}
        
        const allRanges = [];
        document.querySelectorAll('.rich-text-editable, .editing-area, anki-editable').forEach(field => {{
            const root = field.shadowRoot || field;
            allRanges.push(...findRanges(root));
        }});
        
        if (allRanges.length > 0) {{
            const highlight = new Highlight(...allRanges);
            CSS.highlights.set('hsm', highlight);
            
            const style = document.createElement('style');
            style.id = 'hsm-style';
            style.textContent = '::highlight(hsm) {{ background-color: rgba(0, 188, 212, 0.3); border-bottom: 2px solid #00bcd4; }}';
            document.head.appendChild(style);
            console.log('[hsm] Applied', allRanges.length, 'highlights');
        }}
    }}
    
    // Try multiple times as Svelte renders asynchronously
    let attempts = 0;
    const tryHighlight = () => {{
        applyHighlights();
        if (attempts < 10) {{
            attempts++;
            setTimeout(tryHighlight, 200);
        }}
    }};
    setTimeout(tryHighlight, 100);
}})();
"""
    try:
        editor.web.eval(script)
    except Exception:
        pass

def init_editor():
    browser_did_search.append(on_browser_did_search)
    editor_did_load_note.append(on_editor_did_load_note)
