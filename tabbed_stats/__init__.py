"""Tabbed Stats — show Anki stats as a tab instead of a separate window.

Intercepts the Stats toolbar button to show stats inline in the main window
instead of opening a separate dialog. Uses the existing toolbar buttons
(Decks/Stats) for navigation.
"""

from __future__ import annotations

from typing import Any

try:
    import aqt
    from aqt import gui_hooks, mw
    from aqt.qt import QVBoxLayout
    from aqt.webview import AnkiWebView, AnkiWebViewKind
except Exception:
    mw = None  # type: ignore


_stats_web: AnkiWebView | None = None
_original_open: Any = None
_installed = False

_CENTER_GRAPHS_JS = """
(function() {
    if (document.getElementById('tabbedStatsCenterFix')) return;
    const style = document.createElement('style');
    style.id = 'tabbedStatsCenterFix';
    style.textContent = '.graphs-container { margin-left: auto !important; margin-right: auto !important; max-width: calc(100vw - 2em); width: auto !important; }';
    document.head.appendChild(style);
})();
"""

# JS: add a "Choose Deck" button next to the search input, and select the
# Custom radio so the search input value is respected by Svelte.
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


def _show_stats() -> None:
    """Hide main webview, show stats webview."""
    if _stats_web is None:
        return
    mw.web.hide()
    mw.bottomWeb.hide()
    _stats_web.show()


def _close_stats() -> None:
    """Destroy the stats webview entirely."""
    global _stats_web

    if _stats_web is None:
        return

    _stats_web.hide()
    layout: QVBoxLayout = mw.mainLayout
    layout.removeWidget(_stats_web)
    _stats_web.cleanup()
    _stats_web.deleteLater()
    _stats_web = None


def _inject_customizations() -> None:
    """Inject the deck chooser button and centering fix, with retries."""
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

    # Click the Custom radio (value=3), set the search input, trigger change
    _stats_web.eval(f"""
    (function() {{
        // Select the "custom" radio to enable manual search
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

    # Inject deck button after page loads
    web.loadFinished.connect(lambda ok: _inject_customizations() if ok else None)

    # Insert into layout after mw.web
    layout: QVBoxLayout = mw.mainLayout
    web_index = layout.indexOf(mw.web)
    layout.insertWidget(web_index + 1, web)

    _show_stats()
    web.load_sveltekit_page("graphs")

    # Let stats_page_customizer attach its JS injection
    try:
        from stats_page_customizer import _attach_on_load
        _attach_on_load(web)
    except Exception:
        pass


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
    """When Anki switches to deckBrowser/overview/review, close stats."""
    if new_state in ("deckBrowser", "overview", "review"):
        _close_stats()


def _patched_dialogs_open(name: str, *args: Any, **kwargs: Any) -> Any:
    if name == "NewDeckStats":
        _create_stats_tab()
        return None
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
