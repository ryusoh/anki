import json
import os
import re
import sys

from aqt import gui_hooks, mw
from aqt.gui_hooks import webview_did_inject_style_into_page, webview_will_set_content
from aqt.webview import WebContent

addon_path = os.path.dirname(__file__)
addon_dir_name = os.path.basename(addon_path)

# Register the 'web' folder so Anki can serve the JS file
mw.addonManager.setWebExports(__name__, r"web/.*")


def get_addon_config():
    return mw.addonManager.getConfig(__name__) or {}


_GLOW_RGB = (118, 183, 229)
_DEFAULT_GLOW_ALPHA = 0.4
# Mirrors drawAmbientGlow in web/glass_effect.js: stop offsets and per-stop alphas
# (stop 0 uses the configured innerColor alpha), and the static globalAlpha
# multiplier (0.8 + 0.5 * 0.2) applied when the pulse is disabled.
_GLOW_STOPS = ((0.0, None), (0.6, 0.25), (1.0, 0.05))
_STATIC_PULSE_FACTOR = 0.9


def _is_add_cards_editor(context) -> bool:
    if not context:
        return False
    cls = getattr(context, "__class__", None)
    cls_name = getattr(cls, "__name__", "")
    if cls_name == "AddCards" or type(context).__name__ == "AddCards":
        return True
    parent = getattr(context, "parentWindow", None)
    if parent is not None:
        parent_cls = getattr(parent, "__class__", None)
        parent_name = getattr(parent_cls, "__name__", "")
        if parent_name == "AddCards" or type(parent).__name__ == "AddCards":
            return True
    return False


def _parse_rgba(value):
    match = re.match(
        r"\s*rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)",
        str(value or ""),
    )
    if not match:
        return _GLOW_RGB, _DEFAULT_GLOW_ALPHA
    r, g, b, a = match.groups()
    return (int(r), int(g), int(b)), float(a) if a is not None else 1.0


def _canvas_hex() -> str:
    try:
        from aqt import colors
        from aqt.theme import theme_manager

        value = theme_manager.var(colors.CANVAS)
        if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            return value
        return "#2c2c2c" if theme_manager.night_mode else "#f5f5f5"
    except Exception:
        return "#2c2c2c"


def _blend(base_hex: str, rgb, alpha: float) -> str:
    base = [int(base_hex[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(c * (1 - alpha) + o * alpha) for c, o in zip(base, rgb)]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def glass_window_gradient(config) -> str:
    """Opaque QSS gradient equal to the canvas glow composited over the theme canvas.

    The canvas draws a translucent linear gradient from the top-left to the
    bottom-right corner over var(--canvas). Compositing a fixed colour over a
    solid base is linear in alpha, so pre-blending each stop yields the same
    pixels as the web canvas, letting native Qt areas match it exactly.
    """
    rgb, first_alpha = _parse_rgba(config.get("ambientGlowColor"))
    opacity = config.get("ambientGlowOpacity", 0.8) or 0.8
    factor = float(opacity) * _STATIC_PULSE_FACTOR
    base = _canvas_hex()
    stops = []
    for offset, alpha in _GLOW_STOPS:
        stop_rgb = rgb if alpha is None else _GLOW_RGB
        stop_alpha = first_alpha if alpha is None else alpha
        stops.append(f"stop:{offset} {_blend(base, stop_rgb, stop_alpha * factor)}")
    return "qlineargradient(x1:0, y1:0, x2:1, y2:1, " + ", ".join(stops) + ")"


def on_webview_will_set_content(web_content: WebContent, context):
    if not context:
        return

    config = get_addon_config()
    if not config.get("enabled", True):
        return

    cls = getattr(context, "__class__", None)
    context_name = cls.__name__ if cls is not None else ""
    css_str = str(web_content.css)

    # Main window webview targets
    main_targets = [
        "deckbrowser.css",
        "overview.css",
        "reviewer.css",
        "toolbar.css",
        "toolbar-bottom.css",
        "reviewer-bottom.css",
    ]
    is_main_page = any(target in css_str for target in main_targets)
    is_addcards = _is_add_cards_editor(context)

    # Note editors outside of standalone AddCards (e.g. Card Browser) must remain unchanged
    if context_name == "Editor" and not is_addcards:
        return

    if is_main_page or is_addcards:
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


def on_editor_did_init(editor):
    config = get_addon_config()
    if not config.get("enabled", True):
        return

    # Only inject into standalone AddCards editor, NEVER Card Browser
    if not _is_add_cards_editor(editor):
        return

    parent = getattr(editor, "parentWindow", None)
    on_add_cards_did_init(parent, editor=editor)

    if hasattr(editor, "web") and editor.web:
        script_code = get_glass_effect_js()
        if script_code:
            config_json = json.dumps(config)
            editor.web.eval(f"window.glassEffectConfig = {config_json};")
            editor.web.eval(script_code)


if hasattr(gui_hooks, "editor_did_init"):
    gui_hooks.editor_did_init.append(on_editor_did_init)


def make_window_transparent(win_id):
    if sys.platform != "darwin":
        return
    if hasattr(win_id, "_mock_name") or "mock" in type(win_id).__module__:
        return
    try:
        import ctypes
        import ctypes.util

        objc_path = ctypes.util.find_library("objc")
        if not objc_path:
            return
        objc_lib = ctypes.cdll.LoadLibrary(objc_path)
        objc_lib.sel_registerName.restype = ctypes.c_void_p
        objc_lib.sel_registerName.argtypes = [ctypes.c_char_p]

        try:
            win_ptr = int(win_id)
        except (TypeError, ValueError):
            if hasattr(win_id, "__int__"):
                win_ptr = int(win_id.__int__())
            else:
                return

        if not win_ptr:
            return

        ns_view = ctypes.c_void_p(win_ptr)

        sel_window = objc_lib.sel_registerName(b"window")
        msgSend_ptr = ctypes.cast(
            objc_lib.objc_msgSend,
            ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p),
        )
        ns_window = msgSend_ptr(ns_view, sel_window)
        if not ns_window:
            return

        sel_setTitlebarAppearsTransparent = objc_lib.sel_registerName(
            b"setTitlebarAppearsTransparent:"
        )
        msgSend_bool = ctypes.cast(
            objc_lib.objc_msgSend,
            ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool),
        )
        msgSend_bool(ns_window, sel_setTitlebarAppearsTransparent, True)

        sel_setTitleVisibility = objc_lib.sel_registerName(b"setTitleVisibility:")
        msgSend_int = ctypes.cast(
            objc_lib.objc_msgSend,
            ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int),
        )
        msgSend_int(ns_window, sel_setTitleVisibility, 1)

        sel_styleMask = objc_lib.sel_registerName(b"styleMask")
        msgSend_get_ulong = ctypes.cast(
            objc_lib.objc_msgSend,
            ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p),
        )
        current_mask = msgSend_get_ulong(ns_window, sel_styleMask)
        new_mask = current_mask | (1 << 15)  # NSWindowStyleMaskFullSizeContentView
        sel_setStyleMask = objc_lib.sel_registerName(b"setStyleMask:")
        msgSend_set_ulong = ctypes.cast(
            objc_lib.objc_msgSend,
            ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong),
        )
        msgSend_set_ulong(ns_window, sel_setStyleMask, new_mask)
    except Exception as e:
        print(f"Error making window titlebar transparent: {e}")


def on_add_cards_did_init(addcards, editor=None):
    config = get_addon_config()
    if not config.get("enabled", True):
        return

    try:
        from aqt.qt import QColor, Qt

        # Extend window into titlebar and make titlebar transparent on macOS
        if addcards and hasattr(addcards, "winId"):
            make_window_transparent(addcards.winId())

        # Find central widget: check cached attribute, centralWidget(), editor hierarchy, or tabbed_stats
        central = None
        if addcards and "_glass_central" in getattr(addcards, "__dict__", {}):
            central = addcards._glass_central
        elif addcards and hasattr(addcards, "centralWidget"):
            central = addcards.centralWidget()
            if central:
                try:
                    addcards._glass_central = central
                except Exception:
                    pass
        elif editor is not None:
            curr = getattr(editor, "widget", None) or getattr(editor, "web", None)
            while curr:
                parent = curr.parentWidget() if hasattr(curr, "parentWidget") else None
                if parent is None or parent == mw or (addcards and parent == addcards):
                    central = curr
                    break
                curr = parent

        if central is None:
            try:
                import tabbed_stats

                if getattr(tabbed_stats, "_addcards_central", None):
                    central = tabbed_stats._addcards_central
            except Exception:
                pass

        if addcards and central and not getattr(addcards, "_glass_central", None):
            try:
                addcards._glass_central = central
            except Exception:
                pass

        # Set transparent webview background so it blends seamlessly with the central widget
        web = None
        if addcards and hasattr(addcards, "editor") and hasattr(addcards.editor, "web"):
            web = addcards.editor.web
        elif editor and hasattr(editor, "web"):
            web = editor.web

        if web:
            if hasattr(web, "page") and hasattr(web.page(), "setBackgroundColor"):
                web.page().setBackgroundColor(QColor(0, 0, 0, 0))
            if hasattr(web, "setStyleSheet"):
                web.setStyleSheet("background: transparent; border: none;")

        bg_gradient = glass_window_gradient(config)

        # Style native AddCards window if standalone QMainWindow
        if addcards and hasattr(addcards, "setStyleSheet"):
            qss_window = """
                QMainWindow {
                    background: %s;
                }
                #centralwidget, QWidget#centralwidget {
                    background: %s;
                }
            """ % (bg_gradient, bg_gradient)
            addcards.setStyleSheet(qss_window)

        # Style central widget directly so embedded (tabbed_stats) and standalone both get covered
        if central:
            wa = getattr(getattr(Qt, "WidgetAttribute", Qt), "WA_StyledBackground", None)
            if wa is not None:
                central.setAttribute(wa, True)
            if hasattr(central, "setObjectName"):
                central.setObjectName("centralwidget")

            central_qss = """
                #centralwidget, QWidget#centralwidget {
                    background: %s;
                }
                QWidget#modelArea, QWidget#deckArea, QWidget#fieldsArea, QWidget#buttonBox,
                #modelArea, #deckArea, #fieldsArea, #buttonBox {
                    background: transparent;
                    border: none;
                }
                QLabel {
                    background: transparent;
                    color: #e2e8f0;
                }
                QFrame, QGroupBox {
                    background: transparent;
                    border: none;
                }
                QDialogButtonBox {
                    background: transparent;
                    border: none;
                }
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #e2e8f0;
                    border: 1px solid rgba(255, 255, 255, 0.16);
                    border-radius: 6px;
                    padding: 5px 14px;
                    min-height: 22px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.16);
                    border-color: rgba(118, 183, 229, 0.6);
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.25);
                }
                QPushButton[default="true"], QPushButton:default {
                    background-color: rgba(118, 183, 229, 0.28);
                    border: 1px solid rgba(118, 183, 229, 0.65);
                    color: #ffffff;
                }
                QPushButton[default="true"]:hover, QPushButton:default:hover {
                    background-color: rgba(118, 183, 229, 0.42);
                }
            """ % bg_gradient
            if hasattr(central, "setStyleSheet"):
                central.setStyleSheet(central_qss)

        if addcards and hasattr(addcards, "form"):
            for attr in ("modelArea", "deckArea", "fieldsArea", "buttonBox"):
                area = getattr(addcards.form, attr, None)
                if area and hasattr(area, "setStyleSheet"):
                    area.setStyleSheet("background: transparent; border: none;")

        if addcards:
            for chooser in ("modelChooser", "deckChooser"):
                ch = getattr(addcards, chooser, None)
                if ch:
                    w = getattr(ch, "widget", None)
                    if w and hasattr(w, "setStyleSheet"):
                        w.setStyleSheet("background: transparent; border: none;")

    except Exception as e:
        print(f"Error styling AddCards window: {e}")


if hasattr(gui_hooks, "add_cards_did_init"):
    gui_hooks.add_cards_did_init.append(on_add_cards_did_init)


def on_dialog_manager_did_open(dialog_manager, dialog_name, dialog_instance):
    if dialog_name == "AddCards" and dialog_instance:
        on_add_cards_did_init(dialog_instance)


if hasattr(gui_hooks, "dialog_manager_did_open_dialog"):
    gui_hooks.dialog_manager_did_open_dialog.append(on_dialog_manager_did_open)

try:
    from aqt.addcards import AddCards

    _orig_addcards_init = AddCards.__init__

    def _patched_addcards_init(self, *args, **kwargs):
        _orig_addcards_init(self, *args, **kwargs)
        try:
            on_add_cards_did_init(self)
            from aqt.qt import QTimer

            QTimer.singleShot(0, lambda: on_add_cards_did_init(self))
            QTimer.singleShot(50, lambda: on_add_cards_did_init(self))
        except Exception as e:
            print(f"Error in AddCards init hook: {e}")

    AddCards.__init__ = _patched_addcards_init
except Exception:
    pass
