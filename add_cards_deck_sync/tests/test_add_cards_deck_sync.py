import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def load_addon():
    saved = {}

    def _load(mw):
        for name in ("aqt", "aqt.operations", "aqt.operations.deck"):
            saved.setdefault(name, sys.modules.get(name))

        aqt = types.ModuleType("aqt")
        aqt.mw = mw
        aqt.gui_hooks = SimpleNamespace(
            add_cards_did_init=[],
            add_cards_did_change_deck=[],
        )
        operations = types.ModuleType("aqt.operations")
        deck_operations = types.ModuleType("aqt.operations.deck")
        deck_operations.set_current_deck = MagicMock()
        operations.deck = deck_operations
        aqt.operations = operations
        sys.modules.update(
            {
                "aqt": aqt,
                "aqt.operations": operations,
                "aqt.operations.deck": deck_operations,
            }
        )

        import add_cards_deck_sync

        mod = importlib.reload(add_cards_deck_sync)
        return SimpleNamespace(
            mod=mod,
            aqt=aqt,
            set_current_deck=deck_operations.set_current_deck,
        )

    yield _load

    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
    import add_cards_deck_sync

    importlib.reload(add_cards_deck_sync)


def test_hook_registered(load_addon):
    env = load_addon(MagicMock())
    assert env.mod.on_add_cards_did_init in env.aqt.gui_hooks.add_cards_did_init
    assert env.mod.on_add_cards_did_change_deck in env.aqt.gui_hooks.add_cards_did_change_deck


def test_initial_deck_becomes_current_deck(load_addon):
    mw = MagicMock()
    mw.col = MagicMock()
    env = load_addon(mw)
    addcards = SimpleNamespace(deck_chooser=SimpleNamespace(selected_deck_id=7))

    env.mod.on_add_cards_did_init(addcards)

    env.set_current_deck.assert_called_once_with(parent=mw, deck_id=7)
    env.set_current_deck.return_value.run_in_background.assert_called_once_with()


def test_selected_deck_becomes_current_deck(load_addon):
    mw = MagicMock()
    mw.col = MagicMock()
    env = load_addon(mw)

    env.mod.on_add_cards_did_change_deck(42)

    env.set_current_deck.assert_called_once_with(parent=mw, deck_id=42)
    env.set_current_deck.return_value.run_in_background.assert_called_once_with()


def test_change_is_safe_without_main_window(load_addon):
    env = load_addon(None)

    env.mod.on_add_cards_did_change_deck(42)

    env.set_current_deck.assert_not_called()


def test_change_is_safe_without_collection(load_addon):
    mw = MagicMock()
    mw.col = None
    env = load_addon(mw)

    env.mod.on_add_cards_did_change_deck(42)

    env.set_current_deck.assert_not_called()
