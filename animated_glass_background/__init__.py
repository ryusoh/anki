import json
import os

from aqt import mw
from aqt.gui_hooks import webview_did_inject_style_into_page, webview_will_set_content
from aqt.webview import WebContent

addon_path = os.path.dirname(__file__)
addon_dir_name = os.path.basename(addon_path)

# Register the 'web' folder so Anki can serve the JS file
mw.addonManager.setWebExports(__name__, r"web/.*")


def get_addon_config():
    return mw.addonManager.getConfig(__name__) or {}


def on_webview_will_set_content(web_content: WebContent, context):
    if not context:
        return

    config = get_addon_config()
    if not config.get("enabled", True):
        return

    # Check if the webview is loading one of the main UI components
    css_str = str(web_content.css)
    if any(
        target in css_str
        for target in [
            "deckbrowser.css",
            "overview.css",
            "reviewer.css",
            "toolbar.css",
            "toolbar-bottom.css",
            "reviewer-bottom.css",
        ]
    ):
        # Inject config as a script tag in the head
        config_json = json.dumps(config)
        web_content.head += f"<script>window.glassEffectConfig = {config_json};</script>"

        addon_url = f"/_addons/{addon_dir_name}/web/glass_effect.js"
        if addon_url not in web_content.js:
            web_content.js.append(addon_url)


webview_will_set_content.append(on_webview_will_set_content)

_glass_effect_js = None


def get_glass_effect_js():
    global _glass_effect_js
    if _glass_effect_js is None:
        js_path = os.path.join(addon_path, "web", "glass_effect.js")
        try:
            with open(js_path, "r", encoding="utf-8") as f:
                _glass_effect_js = f.read()
        except Exception as e:
            print(f"Glass Effect Addon Error reading JS: {e}")
            _glass_effect_js = ""
    return _glass_effect_js


def on_webview_did_inject_style_into_page(web):
    # This hook is for Svelte-based pages like the "congrats" screen
    try:
        page = os.path.basename(web.page().url().path())
    except Exception as e:
        print(f"Error getting page URL path: {e}")
        return

    config = get_addon_config()
    if not config.get("enabled", True):
        return

    # We want to inject the glass effect into all main Svelte pages (overview, deckbrowser, congrats, etc.)
    target_svelte_pages = [
        "congrats.html",
        "overview.html",
        "deckbrowser.html",
        "reviewer.html",
        "toolbar.html",
        "bottom.html",
    ]

    if page in target_svelte_pages or "congrats" in page or "overview" in page:
        # Evaluate the cached JS file content
        script_code = get_glass_effect_js()
        if script_code:
            # Pass config as a global variable before executing the script
            config_json = json.dumps(config)
            web.eval(f"window.glassEffectConfig = {config_json};")
            web.eval(script_code)


webview_did_inject_style_into_page.append(on_webview_did_inject_style_into_page)
