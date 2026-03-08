from aqt import mw, gui_hooks

def on_webview_will_set_content(web_content, context):
    # Only inject into the deck browser
    if not isinstance(context, type(mw.deckBrowser)):
        return

    # Remove the .current deck highlighting and all possible nested highlights/filters
    web_content.head += """
    <style>
        /* Force absolute transparency and strip all visual effects from the current row and its descendants */
        tr.deck.current, 
        tr.deck.current td, 
        tr.deck.current a, 
        tr.deck.current img, 
        tr.deck.current svg,
        tr.deck.current div,
        tr.deck.current span,
        .current, .current * {
            background-color: transparent !important;
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            filter: none !important;
            -webkit-filter: none !important;
            outline: none !important;
        }
        
        /* Targeted fix for the gear/options icon area */
        .opts, .opts a, .gears, .gear, [class*="opt"], .opts *, .gears * {
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
