import os
from aqt import mw
from aqt.gui_hooks import webview_will_set_content
from aqt.webview import WebContent

addon_path = os.path.dirname(__file__)
addon_dir_name = os.path.basename(addon_path)

# Register the 'web' folder so Anki can serve the JS file
mw.addonManager.setWebExports(__name__, r"web/.*")

def on_webview_will_set_content(web_content: WebContent, context):
    if not context:
        return
        
    # We apply this to the main user screens:
    ctx_name = context.__class__.__name__
    if ctx_name in ["DeckBrowser", "Overview", "Reviewer"]:
        addon_url = f"/_addons/{addon_dir_name}/web/glass_effect.js"
        web_content.js.append(addon_url)

webview_will_set_content.append(on_webview_will_set_content)
