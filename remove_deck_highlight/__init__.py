from aqt import mw, gui_hooks

def on_webview_will_set_content(web_content, context):
    # Only inject into the deck browser
    if not isinstance(context, type(mw.deckBrowser)):
        return
        
    # Remove the .current deck highlighting (the "black bar" or highlight)
    web_content.head += """
    <style>
        .current, .current td, tr.deck.current td, .current:hover, .current:focus {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
    </style>
    """

gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
