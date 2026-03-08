from aqt import mw, gui_hooks

bottom_visible = False
_orig_show = None

def update_visibility():
    if getattr(mw, "state", None) in ["deckBrowser", "overview"]:
        mw.bottomWeb.setVisible(bottom_visible)
        if bottom_visible:
            mw.bottomWeb.adjustHeightToFit()

def on_state_did_change(new_state, old_state):
    if new_state in ["deckBrowser", "overview"]:
        update_visibility()
    elif new_state == "review":
        # Keep bottom bar visible in review mode (for study buttons)
        mw.bottomWeb.setVisible(True)

def custom_bottom_show(*args, **kwargs):
    if _orig_show:
        _orig_show(*args, **kwargs)
    if getattr(mw, "state", None) in ["deckBrowser", "overview"] and not bottom_visible:
        mw.bottomWeb.setVisible(False)

def on_main_window_did_init():
    global _orig_show
    if not hasattr(mw, "bottomWeb"):
        return
        
    _orig_show = mw.bottomWeb.show
    mw.bottomWeb.show = custom_bottom_show
    
    # Run once to apply initial state if we are already in deckBrowser
    update_visibility()

def on_webview_will_set_content(web_content, context):
    # Inject double-click listener into all web views
    # So wherever the user double clicks, we can toggle it.
    js = """
    document.addEventListener('dblclick', function(e) {
        pycmd("toggle_bottom_pane");
    });
    """
    web_content.body += f"<script>{js}</script>"

def on_webview_did_receive_js_message(handled, message, context):
    if message == "toggle_bottom_pane":
        if getattr(mw, "state", None) in ["deckBrowser", "overview"]:
            global bottom_visible
            bottom_visible = not bottom_visible
            update_visibility()
        return (True, None)
    return handled

gui_hooks.main_window_did_init.append(on_main_window_did_init)
gui_hooks.state_did_change.append(on_state_did_change)
gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
gui_hooks.webview_did_receive_js_message.append(on_webview_did_receive_js_message)
