# -*- coding: utf-8 -*-

"""
Anki Add-on: Remove Deck Highlighting
Removes both the 'current' selection highlight and the hover highlight in the deck browser.
"""

from aqt import mw, gui_hooks

def on_webview_will_set_content(web_content, context):
    # Only inject into the deck browser
    if not isinstance(context, type(mw.deckBrowser)):
        return

    # 1. Remove .current (selected) highlighting
    # 2. Remove :hover highlighting
    web_content.head += """
    <style>
        /* Force absolute transparency for selected and hovered rows */
        tr.deck.current, 
        tr.deck.current td,
        tr.deck:hover,
        tr.deck:hover td,
        .current, .current *,
        tr:hover, tr:hover td {
            background-color: transparent !important;
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            filter: none !important;
            -webkit-filter: none !important;
            outline: none !important;
        }
        
        /* Ensure the options/gear icons also stay transparent on hover */
        .opts, .opts a, .gears, .gear, [class*="opt"], .opts *:hover, .gears *:hover {
            background-color: transparent !important;
            background: none !important;
            filter: none !important;
            -webkit-filter: none !important;
            border: none !important;
        }
    </style>
    """
    
    # Inject JS to actively strip the 'current' class which Anki uses for highlighting
    web_content.body += """
    <script>
    (function() {
        const stripCurrent = () => {
            document.querySelectorAll('.current').forEach(el => {
                el.classList.remove('current');
            });
        };
        
        // Strip immediately
        stripCurrent();
        
        // Strip whenever the deck list is re-rendered
        const observer = new MutationObserver(stripCurrent);
        observer.observe(document.body, { childList: true, subtree: true });
    })();
    </script>
    """

gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
