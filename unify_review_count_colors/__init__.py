from aqt import mw, gui_hooks

def on_webview_will_set_content(web_content, context):
    # Only inject into the reviewer's bottom bar
    # In Anki, this context is often ReviewerBottomBar
    if context.__class__.__name__ != "ReviewerBottomBar":
        return
        
    # Override the colors for new (blue), learn (red), and review (green) counts
    # to be consistent with the system text color (white in dark mode)
    web_content.head += """
    <style>
        .new-count, .learn-count, .review-count {
            color: var(--text-fg, white) !important;
        }
    </style>
    """

gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
