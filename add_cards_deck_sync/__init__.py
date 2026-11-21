"""Keep Anki's current deck in sync with the Add Cards deck chooser."""

from __future__ import annotations

import aqt  # type: ignore
from aqt import gui_hooks  # type: ignore


def on_add_cards_did_change_deck(new_deck_id: int) -> None:
    """Make the deck selected in Add Cards the main window's current deck."""
    mw = aqt.mw
    if mw is None or mw.col is None:
        return

    from aqt.operations.deck import set_current_deck  # type: ignore

    set_current_deck(parent=mw, deck_id=new_deck_id).run_in_background()


gui_hooks.add_cards_did_change_deck.append(on_add_cards_did_change_deck)
