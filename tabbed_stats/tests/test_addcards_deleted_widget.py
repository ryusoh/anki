"""Regression test: _create_addcards_tab must not crash on a deleted QWidget.

When the underlying C++ QWidget has been destroyed (e.g. by Anki's dialog
manager) but the Python reference is still alive, calling .show() raises:
    TypeError: show(self): first argument of unbound method must have type 'QWidget'

The fix resets _addcards to None when sip.isdeleted() returns True, so a
fresh AddCards instance is created instead.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Stub out heavy Anki/Qt modules before importing the addon.
# NOTE: the addon imports sip via `from aqt.qt import sip` (the standalone
# top-level `sip` module does not exist under PyQt6), so the stub must live on
# aqt.qt — not as a top-level `sip` module.
_sip = MagicMock()

_aqt = MagicMock()
_aqt.mw = MagicMock()
_aqt.gui_hooks = MagicMock()
_aqt.qt.QVBoxLayout = MagicMock()
_aqt.qt.QWidget = MagicMock()
_aqt.qt.sip = _sip

sys.modules.setdefault("aqt", _aqt)
sys.modules.setdefault("aqt.gui_hooks", _aqt.gui_hooks)
sys.modules.setdefault("aqt.qt", _aqt.qt)
sys.modules.setdefault("aqt.webview", MagicMock())
sys.modules.setdefault("aqt.addcards", MagicMock())
sys.modules.setdefault("aqt.dialogs", MagicMock())

import tabbed_stats as mod


class TestCloseAddcardsDeletedWidget:
    """Calling _close_addcards when _addcards is a deleted widget.

    Real-world trigger: AddCards closes itself through a native path (Escape,
    aqt.dialogs.closeAll on sync/profile close) so the C++ object is destroyed
    while the module global still holds the Python wrapper. Clicking Decks then
    fires state_did_change -> _close_addcards -> _addcards._close(), which
    raises inside saveGeom:
        RuntimeError: wrapped C/C++ object of type AddCards has been deleted
    """

    def test_deleted_addcards_is_not_closed_again(self):
        deleted_widget = MagicMock()
        deleted_widget._close.side_effect = RuntimeError(
            "wrapped C/C++ object of type AddCards has been deleted"
        )
        deleted_central = MagicMock()
        deleted_central.hide.side_effect = RuntimeError(
            "wrapped C/C++ object of type QWidget has been deleted"
        )

        mod._addcards = deleted_widget
        mod._addcards_central = deleted_central

        sys.modules["aqt.qt"].sip.isdeleted = MagicMock(return_value=True)

        with patch.object(mod, "mw", _aqt.mw):
            mod._close_addcards()

        deleted_widget._close.assert_not_called()
        deleted_central.hide.assert_not_called()
        assert mod._addcards is None
        assert mod._addcards_central is None

    def test_live_addcards_is_closed_properly(self):
        live_widget = MagicMock()
        live_central = MagicMock()

        mod._addcards = live_widget
        mod._addcards_central = live_central

        sys.modules["aqt.qt"].sip.isdeleted = MagicMock(return_value=False)

        with patch.object(mod, "mw", _aqt.mw):
            mod._close_addcards()

        live_widget._close.assert_called_once()
        live_central.hide.assert_called_once()
        assert mod._addcards is None
        assert mod._addcards_central is None


class TestCreateAddcardsTabDeletedWidget:
    """Calling _create_addcards_tab when _addcards is a deleted widget."""

    def test_deleted_widget_is_reset(self):
        """A sip-deleted _addcards should be set to None so a new one is created."""
        deleted_widget = MagicMock()

        mod._addcards = deleted_widget

        sys.modules["aqt.qt"].sip.isdeleted = MagicMock(return_value=True)

        with (
            patch.object(mod, "_close_stats"),
            patch.object(mod, "_hide_main_content"),
            patch.object(mod, "mw", _aqt.mw),
        ):

            mod._create_addcards_tab()

            # sip.isdeleted was called with the stale widget
            sys.modules["aqt.qt"].sip.isdeleted.assert_called_once_with(deleted_widget)

            # The stale widget's .show() must NOT have been called
            deleted_widget.show.assert_not_called()

    def test_live_widget_is_reused(self):
        """A valid (not deleted) _addcards should be shown directly."""
        live_widget = MagicMock()

        mod._addcards = live_widget

        sys.modules["aqt.qt"].sip.isdeleted = MagicMock(return_value=False)

        with (
            patch.object(mod, "_close_stats"),
            patch.object(mod, "_hide_main_content"),
            patch.object(mod, "mw", _aqt.mw),
        ):

            mod._create_addcards_tab()

            live_widget.show.assert_called_once()
