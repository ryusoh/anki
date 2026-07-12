"""Tabbed Views — show Anki stats and add-card as inline tabs instead of separate windows.

Intercepts the Stats and Add toolbar buttons to show content inline in the
main window. Uses the existing toolbar buttons (Decks/Stats/Add) for navigation.
"""

from __future__ import annotations

import sys
from typing import Any

try:
    import aqt
    from aqt import gui_hooks, mw
    from aqt.qt import QVBoxLayout, QWidget
    from aqt.webview import AnkiWebView, AnkiWebViewKind
except Exception as e:
    print(f"[tabbed_stats] Anki GUI modules not found: {e}", file=sys.stderr)
    mw = None  # type: ignore


_stats_web: AnkiWebView | None = None
_addcards: Any = None
_addcards_central: Any = None
_original_open: Any = None
_installed = False

_CENTER_GRAPHS_JS = """
(function() {
    if (document.getElementById('tabbedStatsCenterFix')) return;
    const style = document.createElement('style');
    style.id = 'tabbedStatsCenterFix';
    style.textContent = '.graphs-container { margin-left: auto !important; margin-right: auto !important; max-width: calc(100vw - 2em); width: auto !important; } .range-box { background: rgba(0,0,0,0.05) !important; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); } .spacer, div.spacer { height: 1em !important; margin: 0 !important; padding: 0 !important; } .range-box-pad, div.range-box-pad { height: 1em !important; margin: 0 !important; padding: 0 !important; } #statisticsSearchText { background: rgba(0,0,0,0.05) !important; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(128,128,128,0.3) !important; }';
    document.head.appendChild(style);
})();
"""

_INJECT_DECK_BUTTON_JS = """
(function() {
    const input = document.getElementById('statisticsSearchText');
    if (!input || document.getElementById('tabbedStatsDeckBtn')) return;

    const btn = document.createElement('button');
    btn.id = 'tabbedStatsDeckBtn';
    btn.textContent = '選択';
    btn.style.cssText = 'margin-left: 6px; padding: 1px 8px; cursor: pointer; border: none; border-radius: 4px; background: transparent; color: var(--fg); font-size: inherit; opacity: 0.8;';
    btn.addEventListener('mouseenter', function() { btn.style.opacity = '1'; btn.style.background = 'var(--border)'; });
    btn.addEventListener('mouseleave', function() { btn.style.opacity = '0.8'; btn.style.background = 'transparent'; });
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        pycmd('tabbed_stats_choose_deck');
    });
    input.parentNode.insertBefore(btn, input.nextSibling);
})();
"""


def _hide_main_content() -> None:
    """Remove mw.web and bottomWeb from layout so an embedded view gets full space."""
    mw.mainLayout.removeWidget(mw.web)
    mw.web.hide()
    mw.web.setFixedHeight(0)
    mw.mainLayout.removeWidget(mw.bottomWeb)
    mw.bottomWeb.hide()
    mw.bottomWeb.setFixedHeight(0)


def _restore_main_content() -> None:
    """Put mw.web and bottomWeb back into layout if not already there."""
    if mw.mainLayout.indexOf(mw.web) < 0:
        mw.web.setMinimumHeight(0)
        mw.web.setMaximumHeight(16777215)
        mw.mainLayout.insertWidget(1, mw.web)
        mw.web.show()
    if mw.mainLayout.indexOf(mw.bottomWeb) < 0:
        mw.bottomWeb.setMinimumHeight(0)
        mw.bottomWeb.setMaximumHeight(16777215)
        mw.mainLayout.addWidget(mw.bottomWeb)
        mw.bottomWeb.show()
        mw.bottomWeb.adjustHeightToFit()


def _show_stats() -> None:
    """Hide main webview, show stats webview."""
    if _stats_web is None:
        return
    _close_addcards()
    _hide_main_content()
    _stats_web.show()


def _close_stats() -> None:
    """Destroy the stats webview entirely."""
    global _stats_web

    if _stats_web is None:
        return

    _stats_web.hide()
    mw.mainLayout.removeWidget(_stats_web)
    _stats_web.cleanup()
    _stats_web.deleteLater()
    _stats_web = None

    _restore_main_content()


def _inject_customizations() -> None:
    """Inject the deck chooser button, centering fix, and glass effect."""
    if _stats_web is None:
        return
    from aqt.qt import QTimer

    def _do_inject():
        if _stats_web is None:
            return
        _stats_web.eval(_CENTER_GRAPHS_JS)
        _stats_web.eval(_INJECT_DECK_BUTTON_JS)

    for delay in (0, 300, 600, 1200, 2500):
        QTimer.singleShot(delay, _do_inject)
    QTimer.singleShot(100, _inject_glass_effect)


def _inject_glass_effect() -> None:
    """Inject a patched version of the glass effect that doesn't break stats layout."""
    if _stats_web is None:
        return
    try:
        import json

        from animated_glass_background import get_addon_config, get_glass_effect_js

        config = get_addon_config()
        if not config.get("enabled", True):
            return
        config_json = json.dumps(config)
        _stats_web.eval(f"window.glassEffectConfig = {config_json};")

        script = get_glass_effect_js()
        if not script:
            return

        # Patch: remove the aggressive per-frame background stripping loop
        # that forces position:relative and transparent backgrounds on all
        # body children, which breaks the Svelte stats page layout.
        script = script.replace(
            'body > *:not(#glass-effect-bg):not(script):not(style)', '#__never_match_anything__'
        )
        # Patch: remove position:relative on body>div which shifts layout
        script = script.replace('position: relative !important;', 'position: static !important;')

        _stats_web.eval(script)
    except Exception as e:
        print(f"[tabbed_stats] Error applying glass effect: {e}", file=sys.stderr)


def _open_deck_chooser() -> None:
    """Open a deck selection dialog and update stats search."""
    from aqt.studydeck import StudyDeck

    ret = StudyDeck(
        mw,
        accept="選択",
        title="選択",
        parent=mw,
        dyn=True,
        cancel=True,
    )
    if not ret.name:
        return

    if _stats_web is None:
        return

    import json

    deck_name = json.dumps(ret.name)

    _stats_web.eval(f"""
    (function() {{
        const radios = document.querySelectorAll('.range-box input[type="radio"]');
        for (const r of radios) {{
            if (r.value === '3') {{
                r.click();
                break;
            }}
        }}
        const input = document.getElementById('statisticsSearchText');
        if (input) {{
            const nativeSetter = Object.getOwnPropertyDescriptor(
                HTMLInputElement.prototype, 'value'
            ).set;
            nativeSetter.call(input, "deck:" + {deck_name});
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
    }})();
    """)


def _create_stats_tab() -> None:
    """Create stats webview and show it inline."""
    global _stats_web

    if _stats_web is not None:
        _show_stats()
        _stats_web.load_sveltekit_page("graphs")
        return

    web = AnkiWebView(mw, kind=AnkiWebViewKind.DECK_STATS)
    web.set_bridge_command(_on_stats_bridge_cmd, web)
    web.set_open_links_externally(True)
    _stats_web = web

    web.loadFinished.connect(lambda ok: _inject_customizations() if ok else None)

    layout: QVBoxLayout = mw.mainLayout
    web_index = layout.indexOf(mw.web)
    layout.removeWidget(mw.web)
    mw.web.hide()
    layout.removeWidget(mw.bottomWeb)
    mw.bottomWeb.hide()
    layout.insertWidget(web_index, web)

    _stats_web.show()
    web.load_sveltekit_page("graphs")

    try:
        from stats_page_customizer import _attach_on_load

        _attach_on_load(web)
    except Exception as e:
        print(f"[tabbed_stats] Error attaching stats page customizer: {e}", file=sys.stderr)


def _create_addcards_tab() -> None:
    """Create AddCards inline in the main window."""
    global _addcards

    if _addcards is not None:
        from aqt.qt import sip

        if sip.isdeleted(_addcards):
            _addcards = None
        else:
            # Already open, just switch to it
            _close_stats()
            _hide_main_content()
            _addcards.show()
            return

    _close_stats()

    from aqt.addcards import AddCards
    from aqt.qt import Qt

    # Monkey-patch show() to prevent the window from appearing separately.
    # AddCards inherits show() from QWidget: assigning the fetched sip unbound
    # method back would plant it in AddCards.__dict__, where it no longer
    # binds self and any later .show() raises TypeError — so restore by
    # deleting the override unless the class had its own show().
    _had_own_show = "show" in AddCards.__dict__
    _original_show = AddCards.__dict__.get("show")

    def _patched_show(self):
        pass  # Don't show as separate window

    AddCards.show = _patched_show
    try:
        addcards = AddCards(mw)
    finally:
        if _had_own_show:
            AddCards.show = _original_show
        else:
            del AddCards.show

    _addcards = addcards

    # Register with dialog manager so Anki knows it's open
    aqt.dialogs._dialogs["AddCards"][1] = addcards

    # Grab the central widget and embed it in the main layout
    global _addcards_central
    central = addcards.centralWidget()
    central.setParent(None)  # detach from AddCards window
    _addcards_central = central

    _hide_main_content()

    layout: QVBoxLayout = mw.mainLayout
    layout.insertWidget(1, central)
    central.show()

    # Keep the AddCards window hidden (it still owns the logic)
    addcards.hide()


def _close_addcards() -> None:
    """Close the embedded AddCards view."""
    global _addcards, _addcards_central

    if _addcards is None:
        return

    from aqt.qt import sip

    if _addcards_central is not None:
        if not sip.isdeleted(_addcards_central):
            mw.mainLayout.removeWidget(_addcards_central)
            _addcards_central.hide()
        _addcards_central = None

    # AddCards may have closed itself (Escape, dialogs.closeAll on
    # sync/profile close), leaving a dead wrapper — calling _close() on it
    # raises RuntimeError inside saveGeom.
    if not sip.isdeleted(_addcards):
        # Let AddCards clean itself up properly
        _addcards._close_event_has_cleaned_up = False
        _addcards._close()
    _addcards = None


def _on_stats_bridge_cmd(cmd: str) -> bool:
    if cmd == "tabbed_stats_choose_deck":
        _open_deck_chooser()
        return True
    if cmd.startswith("browserSearch"):
        _, query = cmd.split(":", 1)
        browser = _original_open("Browser", mw)
        browser.search_for(query)
        return True
    return False


def _on_state_did_change(new_state: str, old_state: str) -> None:
    if new_state in ("deckBrowser", "overview", "review"):
        _close_stats()
        _close_addcards()
        _restore_main_content()


def _patched_dialogs_open(name: str, *args: Any, **kwargs: Any) -> Any:
    if name == "NewDeckStats":
        _create_stats_tab()
        return None
    if name == "AddCards":
        _create_addcards_tab()
        return _addcards
    return _original_open(name, *args, **kwargs)


def _on_main_window_did_init() -> None:
    global _original_open, _installed

    if _installed:
        return

    _original_open = aqt.dialogs.open
    aqt.dialogs.open = _patched_dialogs_open
    _installed = True


if gui_hooks and mw:
    gui_hooks.main_window_did_init.append(_on_main_window_did_init)
    gui_hooks.state_did_change.append(_on_state_did_change)
