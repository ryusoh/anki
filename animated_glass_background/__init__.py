import os
from aqt import mw
from aqt.gui_hooks import webview_will_set_content, webview_did_inject_style_into_page
from aqt.webview import WebContent

addon_path = os.path.dirname(__file__)
addon_dir_name = os.path.basename(addon_path)

# Register the 'web' folder so Anki can serve the JS file
mw.addonManager.setWebExports(__name__, r"web/.*")

def on_webview_will_set_content(web_content: WebContent, context):
    if not context:
        return
        
    # Check if the webview is loading one of the main UI components
    css_str = str(web_content.css)
    if any(target in css_str for target in ["deckbrowser.css", "overview.css", "reviewer.css", "toolbar.css", "toolbar-bottom.css", "reviewer-bottom.css"]):
        addon_url = f"/_addons/{addon_dir_name}/web/glass_effect.js"
        if addon_url not in web_content.js:
            web_content.js.append(addon_url)

webview_will_set_content.append(on_webview_will_set_content)

def on_webview_did_inject_style_into_page(web):
    # This hook is for Svelte-based pages like the "congrats" screen
    try:
        page = os.path.basename(web.page().url().path())
    except Exception:
        return
        
    # We want to inject the glass effect into all main Svelte pages (overview, deckbrowser, congrats, etc.)
    target_svelte_pages = ["congrats.html", "overview.html", "deckbrowser.html", "reviewer.html", "toolbar.html", "bottom.html"]
    
    if page in target_svelte_pages or "congrats" in page or "overview" in page:
        # Read the JS file directly and evaluate it to bypass potential CSP script-src blocking on Svelte pages
        js_path = os.path.join(addon_path, "web", "glass_effect.js")
        try:
            with open(js_path, "r", encoding="utf-8") as f:
                script_code = f.read()
            web.eval(script_code)
        except Exception as e:
            print(f"Glass Effect Addon Error: {e}")

webview_did_inject_style_into_page.append(on_webview_did_inject_style_into_page)

