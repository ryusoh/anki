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

# Stub out heavy Anki/Qt modules before importing the addon
_sip = MagicMock()
sys.modules.setdefault("sip", _sip)

_aqt = MagicMock()
_aqt.mw = MagicMock()
_aqt.gui_hooks = MagicMock()
_aqt.qt.QVBoxLayout = MagicMock()
_aqt.qt.QWidget = MagicMock()

sys.modules.setdefault("aqt", _aqt)
sys.modules.setdefault("aqt.gui_hooks", _aqt.gui_hooks)
sys.modules.setdefault("aqt.qt", _aqt.qt)
sys.modules.setdefault("aqt.webview", MagicMock())
sys.modules.setdefault("aqt.addcards", MagicMock())
sys.modules.setdefault("aqt.dialogs", MagicMock())

import tabbed_stats as mod


class TestCreateAddcardsTabDeletedWidget:
    """Calling _create_addcards_tab when _addcards is a deleted widget."""

    def test_deleted_widget_is_reset(self):
        """A sip-deleted _addcards should be set to None so a new one is created."""
        deleted_widget = MagicMock()

        mod._addcards = deleted_widget

        _sip.isdeleted = MagicMock(return_value=True)

        with patch.object(mod, "_close_stats"), \
             patch.object(mod, "_hide_main_content"), \
             patch.object(mod, "mw", _aqt.mw):

            mod._create_addcards_tab()

            # sip.isdeleted was called with the stale widget
            _sip.isdeleted.assert_called_once_with(deleted_widget)

            # The stale widget's .show() must NOT have been called
            deleted_widget.show.assert_not_called()

    def test_live_widget_is_reused(self):
        """A valid (not deleted) _addcards should be shown directly."""
        live_widget = MagicMock()

        mod._addcards = live_widget

        _sip.isdeleted = MagicMock(return_value=False)

        with patch.object(mod, "_close_stats"), \
             patch.object(mod, "_hide_main_content"), \
             patch.object(mod, "mw", _aqt.mw):

            mod._create_addcards_tab()

            live_widget.show.assert_called_once()
