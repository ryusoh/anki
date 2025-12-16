"""Stats Page Customizer add-on.

Customizes the stats page to remove the '1 year' option and default to 'All time'.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from aqt import gui_hooks
    from aqt.qt import QTimer
    from aqt.stats import DeckStats, NewDeckStats
    from aqt.webview import AnkiWebView
except Exception:  # pragma: no cover - only when run outside Anki
    gui_hooks = None  # type: ignore
    DeckStats = None  # type: ignore[misc,assignment]
    NewDeckStats = None  # type: ignore[misc,assignment]
    AnkiWebView = Any  # type: ignore[misc,assignment]
    QTimer = None  # type: ignore[misc,assignment]

JS_CODE = """
(function() {
    if (window.statsCustomizerInterval) clearInterval(window.statsCustomizerInterval);
    document.documentElement.dataset.statsCustomizer = "active";

    function applyChanges() {
        const candidateSelectors = [
            "button",
            "label",
            "[role='button']",
            "[role='tab']",
            "[role='radio']"
        ];

        const candidates = Array.from(
            document.querySelectorAll(candidateSelectors.join(","))
        );
        
        let yearBtn = null;
        let allBtn = null;

        const containsNeedle = (text, needles) => {
            if (!text) {
                return false;
            }
            const normalized = text.toLowerCase();
            return needles.some((needle) => normalized.includes(needle));
        };

        for (const el of candidates) {
            const textBits = [
                el.textContent,
                el.getAttribute("aria-label"),
                el.getAttribute("title"),
                el.getAttribute("data-key"),
            ]
                .filter(Boolean)
                .map((s) => s.trim());

            const haystack = textBits.join(" ").trim();
            if (!haystack) {
                continue;
            }

            if (
                !yearBtn &&
                containsNeedle(haystack, [
                    "1 year",
                    "year",
                    "年間",
                    "１年間",
                    "1年間",
                ]) &&
                !containsNeedle(haystack, ["all", "全", "all history", "全期間"])
            ) {
                yearBtn = el;
            }

            if (
                !allBtn &&
                containsNeedle(haystack, [
                    "all",
                    "all time",
                    "all history",
                    "全",
                    "全期間",
                    "全期間",
                    "全歴史",
                ])
            ) {
                allBtn = el;
            }
        }

        if (yearBtn && yearBtn.style.display !== 'none') {
            yearBtn.style.display = 'none';
        }

        if (allBtn) {
            const isActive = allBtn.classList.contains('active') || 
                             (allBtn.querySelector('input') && allBtn.querySelector('input').checked);
            
            if (!isActive) {
                let siblingActive = false;
                if (allBtn.parentElement) {
                    const siblings = allBtn.parentElement.querySelectorAll('button, label');
                    for (const s of siblings) {
                        if (s !== allBtn && s !== yearBtn) {
                             if (s.classList.contains('active') || (s.querySelector('input') && s.querySelector('input').checked)) {
                                 siblingActive = true;
                             }
                        }
                    }
                }
                
                // If no sibling (Month) is active, then Year (or nothing) is active. Click All.
                if (!siblingActive) {
                    allBtn.click();
                }
            }

            // Hide the All button once it's enforced; there's no reason to show it alone.
            if (allBtn.style.display !== 'none') {
                allBtn.style.display = 'none';
            }

            // If its container now only has hidden children, hide that too.
            if (allBtn.parentElement) {
                const visibleChildren = Array.from(
                    allBtn.parentElement.querySelectorAll('button, label')
                ).filter((el) => el !== allBtn && el.style.display !== 'none');
                if (visibleChildren.length === 0) {
                    allBtn.parentElement.style.display = 'none';
                }
            }
        }
    }

    // Run frequently
    applyChanges();
    window.statsCustomizerInterval = setInterval(applyChanges, 200);
})();
"""

def _log(message: str) -> None:
    """Append debug info to a log file next to this add-on."""

    try:
        log_path = Path(__file__).with_name("stats_customizer.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(message + "\n")
    except Exception:
        pass

def _schedule_js_eval(web: AnkiWebView) -> None:
    """Run the JavaScript a few times to catch async loads."""

    delays = (0, 250, 500, 1000, 2000)
    _log(f"_schedule_js_eval called for web={web} delays={delays}")
    if QTimer is None:
        web.eval(JS_CODE)
        _log("QTimer missing; executed JS once.")
        return

    _log(f"Scheduling JS evals with delays={delays}")
    for delay in delays:
        QTimer.singleShot(delay, lambda w=web: w.eval(JS_CODE))

def _attach_on_load(web: AnkiWebView) -> None:
    """Ensure the JS is injected after the stats page finishes loading."""

    if getattr(web, "_stats_customizer_connected", False):
        _log("webview already connected; skipping attach.")
        return

    _log("Attaching loadFinished hook to stats webview.")
    def _on_load_finished(ok: bool) -> None:
        if ok:
            _schedule_js_eval(web)

    load_finished = getattr(web, "loadFinished", None)
    if load_finished is not None:
        load_finished.connect(_on_load_finished)
        _log("Connected loadFinished signal.")
    else:
        _log("loadFinished signal missing.")

    setattr(web, "_stats_customizer_connected", True)
    _schedule_js_eval(web)


def _on_stats_dialog_will_show(stats_dialog: Any) -> None:
    web = getattr(stats_dialog, "web", None)
    if not web:
        _log("stats_dialog lacks web attribute; skipping.")
        return

    _log("stats_dialog_will_show fired; attaching.")
    _attach_on_load(web)


if gui_hooks and hasattr(gui_hooks, "stats_dialog_will_show"):
    gui_hooks.stats_dialog_will_show.append(_on_stats_dialog_will_show)


def _patch_stats_class(cls: Any) -> None:
    if not cls:
        _log("Stats class missing; cannot patch.")
        return

    original_init = getattr(cls, "__init__", None)
    original_refresh = getattr(cls, "refresh", None)
    if not original_init or not original_refresh:
        _log(f"{cls} lacks __init__ or refresh; cannot patch.")
        return

    if not getattr(original_init, "_stats_customizer_patched", False):
        def _wrapped_init(self: Any, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            web = getattr(self, "web", None)
            _log(
                f"{cls.__name__}.__init__ called; has web={bool(web)}; attrs={dir(self)}"
            )
            if web:
                _log(f"{cls.__name__}.__init__ attaching webview via self.web.")
                _attach_on_load(web)
            else:
                fallback_web = getattr(getattr(self, "form", None), "web", None)
                if fallback_web:
                    _log(f"{cls.__name__}.__init__ attaching webview via form.web.")
                    _attach_on_load(fallback_web)
                else:
                    for attr in ("form", "content", "mw"):
                        val = getattr(self, attr, None)
                        if val is not None:
                            _log(
                                f"{cls.__name__}.{attr} type={type(val)} attrs={dir(val)}"
                            )

        _wrapped_init._stats_customizer_patched = True  # type: ignore[attr-defined]
        cls.__init__ = _wrapped_init  # type: ignore[assignment]
        _log(f"Patched {cls.__name__}.__init__")

    if not getattr(original_refresh, "_stats_customizer_patched", False):
        def _wrapped_refresh(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = original_refresh(self, *args, **kwargs)
            web = getattr(self, "web", None)
            if web:
                _log(f"{cls.__name__}.refresh scheduling JS.")
                _schedule_js_eval(web)
            return result

        _wrapped_refresh._stats_customizer_patched = True  # type: ignore[attr-defined]
        cls.refresh = _wrapped_refresh  # type: ignore[assignment]
        _log(f"Patched {cls.__name__}.refresh")


_patch_stats_class(NewDeckStats)
_patch_stats_class(DeckStats)
