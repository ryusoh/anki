"""Stats Page Customizer add-on.

Currently acts as a scaffold for future stats-page tweaks.
"""

from __future__ import annotations

from typing import Any

try:
    from aqt import gui_hooks
except Exception:  # pragma: no cover - only when run outside Anki
    gui_hooks = None  # type: ignore

def _on_stats_dialog_will_show(stats_dialog: Any) -> None:
    """Placeholder hook for upcoming stats customizations."""
    # TODO: implement logic that tweaks stats_dialog.web contents.
    return

if gui_hooks and hasattr(gui_hooks, "stats_dialog_will_show"):
    gui_hooks.stats_dialog_will_show.append(_on_stats_dialog_will_show)  # type: ignore[attr-defined]
