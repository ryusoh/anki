"""Background CPU Governor — pauses WebView animations when Anki is inactive."""

from __future__ import annotations

import os
from typing import Any

from aqt import gui_hooks

from .core import (
    build_config_script,
    build_set_enabled_script,
    build_set_paused_script,
    detect_software_compositing,
    format_status_report,
    normalize_config,
)

try:
    from aqt.qt import QAction, QApplication, QEvent, QMenu, QObject  # type: ignore
except Exception:  # pragma: no cover - fallback only when Qt stubs lack symbols
    QAction = None  # type: ignore
    QApplication = None  # type: ignore
    QEvent = None  # type: ignore
    QMenu = None  # type: ignore
    QObject = object  # type: ignore

addon_path = os.path.dirname(__file__)
addon_dir_name = os.path.basename(addon_path)

_paused = False
_web_exports_registered = False
_governor_js_cache: str | None = None
_event_filter_instance: Any = None
_toggle_action: Any = None


def _get_mw() -> Any:
    import aqt

    return getattr(aqt, "mw", None)


def _addon_key() -> str:
    return __name__.split(".")[0]


def get_config() -> dict[str, bool]:
    """Read addon config normalized against defaults."""
    mw = _get_mw()
    mgr = getattr(mw, "addonManager", None)
    if mgr is None:
        return normalize_config(None)
    raw = mgr.getConfig(_addon_key())
    return normalize_config(raw)


def save_config(config: dict[str, bool]) -> None:
    """Persist normalized addon configuration."""
    mw = _get_mw()
    mgr = getattr(mw, "addonManager", None)
    if mgr is None:
        return
    writer = getattr(mgr, "writeConfig", None)
    if callable(writer):
        writer(_addon_key(), dict(config))


def ensure_web_exports() -> None:
    """Expose background_cpu_governor/web once when mw.addonManager is ready."""
    global _web_exports_registered
    if _web_exports_registered:
        return
    mw = _get_mw()
    mgr = getattr(mw, "addonManager", None)
    if mgr is not None and callable(getattr(mgr, "setWebExports", None)):
        mgr.setWebExports(_addon_key(), r"web/.*")
        _web_exports_registered = True


def get_governor_js() -> str:
    """Read and cache web/governor.js."""
    global _governor_js_cache
    if _governor_js_cache is None:
        js_path = os.path.join(addon_path, "web", "governor.js")
        try:
            with open(js_path, "r", encoding="utf-8") as f:
                _governor_js_cache = f.read()
        except Exception:
            _governor_js_cache = ""
    return _governor_js_cache


def _is_webview(obj: Any) -> bool:
    if obj is None:
        return False
    if callable(getattr(obj, "eval", None)):
        return True
    page_fn = getattr(obj, "page", None)
    if callable(page_fn):
        try:
            page = page_fn()
            return callable(getattr(page, "runJavaScript", None))
        except Exception:
            return False
    return False


def collect_webviews() -> list[Any]:
    """Return unique WebView instances across open Qt widgets and main window panes."""
    views: list[Any] = []
    seen_ids: set[int] = set()

    def _add(candidate: Any) -> None:
        if candidate is None:
            return
        ident = id(candidate)
        if ident in seen_ids or not _is_webview(candidate):
            return
        seen_ids.add(ident)
        views.append(candidate)

    app = QApplication.instance() if QApplication is not None else None
    all_widgets = getattr(app, "allWidgets", None)
    if callable(all_widgets):
        try:
            for widget in all_widgets() or ():
                _add(widget)
        except Exception:
            pass

    mw = _get_mw()
    if mw is not None:
        _add(getattr(mw, "web", None))
        _add(getattr(mw, "bottomWeb", None))
        toolbar = getattr(mw, "toolbar", None)
        if toolbar is not None:
            _add(getattr(toolbar, "web", None))
    return views


def _eval_js(view: Any, script: str) -> None:
    eval_fn = getattr(view, "eval", None)
    if callable(eval_fn):
        eval_fn(script)
        return
    page_fn = getattr(view, "page", None)
    if callable(page_fn):
        page = page_fn()
        run_js = getattr(page, "runJavaScript", None)
        if callable(run_js):
            run_js(script)


def broadcast_js(script: str) -> int:
    """Evaluate script in all live WebViews, ignoring per-view Qt errors."""
    sent = 0
    for view in collect_webviews():
        try:
            _eval_js(view, script)
            sent += 1
        except Exception:
            continue
    return sent


def set_app_paused(paused: bool) -> None:
    """Update cached application pause state and notify active WebViews."""
    global _paused
    config = get_config()
    if paused and not (config["enabled"] and config["pause_on_app_deactivate"]):
        return
    _paused = bool(paused)
    broadcast_js(build_set_paused_script(_paused))


def set_enabled(enabled: bool) -> None:
    """Toggle governor enabled state, persist config, and update live WebViews."""
    global _paused
    config = get_config()
    config["enabled"] = bool(enabled)
    save_config(config)
    if not config["enabled"]:
        _paused = False
    broadcast_js(build_set_enabled_script(config["enabled"]))


def _event_type(name: str) -> Any:
    if QEvent is None:
        return None
    enum_cls = getattr(QEvent, "Type", None)
    if enum_cls is not None and hasattr(enum_cls, name):
        return getattr(enum_cls, name)
    return getattr(QEvent, name, None)


class _AppFocusFilter(QObject):
    """Qt application event filter pausing WebViews on deactivate and resuming on activate."""

    def eventFilter(self, obj: Any, event: Any) -> bool:  # noqa: N802
        ev_type = event.type() if hasattr(event, "type") else None
        deactivate_type = _event_type("ApplicationDeactivate")
        activate_type = _event_type("ApplicationActivate")
        if deactivate_type is not None and ev_type == deactivate_type:
            set_app_paused(True)
        elif activate_type is not None and ev_type == activate_type:
            set_app_paused(False)
        return False


def install_app_event_filter() -> bool:
    """Install singleton application focus filter on QApplication.instance()."""
    global _event_filter_instance
    if QApplication is None:
        return False
    app = QApplication.instance()
    if app is None or not callable(getattr(app, "installEventFilter", None)):
        return False
    if getattr(app, "_cpu_governor_filter_installed", False):
        return False
    _event_filter_instance = _AppFocusFilter()
    app.installEventFilter(_event_filter_instance)
    app._cpu_governor_filter_installed = True
    return True


def show_status_dialog() -> str:
    """Display the current CPU governor status via aqt.utils.showInfo when available."""
    config = get_config()
    views = collect_webviews()
    soft = detect_software_compositing(os.environ)
    report = format_status_report(
        enabled=config["enabled"],
        paused=_paused,
        webview_count=len(views),
        software_compositing=soft,
    )
    try:
        from aqt.utils import showInfo  # type: ignore

        showInfo(report, title="Background CPU Governor")
    except Exception:
        pass
    return report


def _setup_tools_menu() -> None:
    global _toggle_action
    mw = _get_mw()
    if mw is None or QAction is None or QMenu is None:
        return
    menu_tools = getattr(getattr(mw, "form", None), "menuTools", None)
    if menu_tools is None:
        return
    if getattr(mw, "_cpu_governor_menu_installed", False):
        return

    config = get_config()
    submenu = QMenu("Background CPU Governor", mw)

    _toggle_action = QAction("Enable Background Throttling", mw)
    _toggle_action.setCheckable(True)
    _toggle_action.setChecked(config["enabled"])
    _toggle_action.triggered.connect(lambda checked: set_enabled(bool(checked)))
    submenu.addAction(_toggle_action)

    status_action = QAction("Show Status…", mw)
    status_action.triggered.connect(lambda _checked=False: show_status_dialog())
    submenu.addAction(status_action)

    menu_tools.addMenu(submenu)
    mw._cpu_governor_menu_installed = True


def on_webview_will_set_content(web_content: Any, context: Any) -> None:
    """Inject governor config and web/governor.js into every Anki WebView."""
    ensure_web_exports()
    config = get_config()
    web_content.head += f"<script>{build_config_script(config)}</script>"
    addon_url = f"/_addons/{addon_dir_name}/web/governor.js"
    if addon_url not in web_content.js:
        web_content.js.append(addon_url)


def on_main_window_did_init() -> None:
    """Initialize app-level focus filter, menu actions, and initial WebViews."""
    ensure_web_exports()
    install_app_event_filter()
    _setup_tools_menu()
    config = get_config()
    js_code = get_governor_js()
    if js_code:
        broadcast_js(f"{build_config_script(config)}\n{js_code}")


gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
gui_hooks.main_window_did_init.append(on_main_window_did_init)
