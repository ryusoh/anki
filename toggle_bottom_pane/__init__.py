from aqt import mw, gui_hooks
from aqt.qt import QObject, QEvent, Qt

bottom_visible = False
_top_filter = None

def update_visibility():
    if getattr(mw, "state", None) in ["deckBrowser", "overview"]:
        if hasattr(mw, "bottomWeb"):
            mw.bottomWeb.setVisible(bottom_visible)
            if bottom_visible:
                mw.bottomWeb.adjustHeightToFit()

def on_state_did_change(new_state, old_state):
    if new_state in ["deckBrowser", "overview"]:
        update_visibility()
    elif new_state == "review":
        # Keep bottom bar visible in review mode (for study buttons)
        if hasattr(mw, "bottomWeb"):
            mw.bottomWeb.setVisible(True)

def toggle_bottom_pane_logic():
    if getattr(mw, "state", None) in ["deckBrowser", "overview"]:
        global bottom_visible
        bottom_visible = not bottom_visible
        update_visibility()

class TopPaneFilter(QObject):
    def eventFilter(self, obj, event):
        # We catch double clicks on the main window to handle the top pane toggle
        # This is especially useful when plugins like 'hide_window_title' or 
        # 'mac_transparent_titlebar' are used, as it catches clicks in the 
        # native titlebar/toolbar area that JS might miss.
        if event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                try:
                    # Get position relative to the main window
                    global_pos = event.globalPosition().toPoint()
                    local_pos = mw.mapFromGlobal(global_pos)
                    
                    # Top 80px typically covers both the titlebar and the top toolbar
                    if 0 <= local_pos.y() <= 80:
                        toggle_bottom_pane_logic()
                        return True
                except Exception as e:
                    import sys
                    print(f"Error handling top pane double click: {e}", file=sys.stderr)
        return False

def on_main_window_did_init():
    global _top_filter
    if not hasattr(mw, "bottomWeb"):
        return
        
    # Prevent infinite recursion and TypeError by using a manual monkey-patch with closure
    # instead of anki.hooks.wrap, which can be inconsistent across Anki versions.
    if not hasattr(mw.bottomWeb, "_toggle_bottom_pane_patched"):
        original_show = mw.bottomWeb.show
        
        def patched_show(*args, **kwargs):
            # Call the original show method
            res = original_show(*args, **kwargs)
            
            # After showing, ensure we hide it if it should be hidden
            if getattr(mw, "state", None) in ["deckBrowser", "overview"] and not bottom_visible:
                if hasattr(mw, "bottomWeb"):
                    mw.bottomWeb.setVisible(False)
            return res
            
        mw.bottomWeb.show = patched_show
        mw.bottomWeb._toggle_bottom_pane_patched = True
    
    # Install the Python-side event filter
    if _top_filter is None:
        _top_filter = TopPaneFilter()
        mw.installEventFilter(_top_filter)
    
    # Run once to apply initial state if we are already in deckBrowser
    update_visibility()

def on_webview_will_set_content(web_content, context):
    # Detect if this is the top toolbar webview
    context_name = type(context).__name__
    is_toolbar = "Toolbar" in context_name and "Bottom" not in context_name
    
    if not is_toolbar:
        return

    # Injected JS handles double-clicks specifically within the toolbar webview
    js = """
    document.addEventListener('dblclick', function(e) {
        // Only trigger if clicking on background elements, not interactive buttons/inputs
        const interactiveTags = ['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA'];
        if (!interactiveTags.includes(e.target.tagName)) {
            pycmd("toggle_bottom_pane");
        }
    });
    """
    web_content.body += f"<script>{js}</script>"

def on_webview_did_receive_js_message(handled, message, context):
    if message == "toggle_bottom_pane":
        toggle_bottom_pane_logic()
        return (True, None)
    return handled

gui_hooks.main_window_did_init.append(on_main_window_did_init)
gui_hooks.state_did_change.append(on_state_did_change)
gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
gui_hooks.webview_did_receive_js_message.append(on_webview_did_receive_js_message)

# Support late loading
if mw:
    on_main_window_did_init()
