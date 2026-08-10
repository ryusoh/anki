import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_aqt():
    aqt_mock = MagicMock()
    mw_mock = MagicMock()
    aqt_mock.mw = mw_mock
    aqt_mock.gui_hooks = MagicMock()
    aqt_mock.qt = MagicMock()
    # default: widgets are alive (a bare MagicMock would read as "deleted")
    aqt_mock.qt.sip.isdeleted.return_value = False
    aqt_mock.webview = MagicMock()

    sys.modules['aqt'] = aqt_mock
    sys.modules['aqt.qt'] = aqt_mock.qt
    sys.modules['aqt.webview'] = aqt_mock.webview
    sys.modules['aqt.gui_hooks'] = aqt_mock.gui_hooks

    # ensure it gets reloaded with mocks
    if 'tabbed_stats' in sys.modules:
        del sys.modules['tabbed_stats']

    yield

    # cleanup after test
    for k in list(sys.modules.keys()):
        if k.startswith('aqt'):
            del sys.modules[k]
    if 'tabbed_stats' in sys.modules:
        del sys.modules['tabbed_stats']


def test_close_stats_when_none():
    import tabbed_stats
    from tabbed_stats import _close_stats

    tabbed_stats._stats_web = None
    _close_stats()


def test_close_stats_when_set():
    import tabbed_stats
    from tabbed_stats import _close_stats

    mock_web = MagicMock()
    tabbed_stats._stats_web = mock_web
    import aqt

    # mock indexOf to return an integer so the '<' comparison works
    aqt.mw.mainLayout.indexOf.return_value = -1

    _close_stats()

    mock_web.hide.assert_called_once()
    mock_web.cleanup.assert_called_once()
    mock_web.deleteLater.assert_called_once()
    assert tabbed_stats._stats_web is None

    assert aqt.mw.mainLayout.insertWidget.call_count == 1
    aqt.mw.web.show.assert_called_once()
    aqt.mw.bottomWeb.show.assert_called_once()


def test_inject_customizations_when_none():
    import tabbed_stats
    from tabbed_stats import _inject_customizations

    tabbed_stats._stats_web = None
    _inject_customizations()


def test_inject_customizations_when_set():
    import aqt

    import tabbed_stats
    from tabbed_stats import _inject_customizations

    aqt.qt.QTimer = MagicMock()
    mock_web = MagicMock()
    tabbed_stats._stats_web = mock_web

    _inject_customizations()

    assert aqt.qt.QTimer.singleShot.call_count > 0

    # Check all callbacks and run them if possible to see if mock_web.eval is called
    for call in aqt.qt.QTimer.singleShot.call_args_list:
        args, kwargs = call
        if len(args) > 1 and callable(args[1]):
            try:
                args[1]()
            except Exception:
                pass

    assert mock_web.eval.call_count > 0


def test_close_addcards_when_none():
    import tabbed_stats
    from tabbed_stats import _close_addcards

    tabbed_stats._addcards = None
    _close_addcards()


def test_close_addcards_when_set():
    import aqt

    import tabbed_stats
    from tabbed_stats import _close_addcards

    mock_addcards = MagicMock()
    mock_central = MagicMock()

    tabbed_stats._addcards = mock_addcards
    tabbed_stats._addcards_central = mock_central

    _close_addcards()

    aqt.mw.mainLayout.removeWidget.assert_called_once_with(mock_central)
    mock_central.hide.assert_called_once()
    assert tabbed_stats._addcards_central is None

    assert mock_addcards._close_event_has_cleaned_up is False
    mock_addcards._close.assert_called_once()
    assert tabbed_stats._addcards is None


def test_close_addcards_when_central_none():
    import aqt

    import tabbed_stats
    from tabbed_stats import _close_addcards

    mock_addcards = MagicMock()
    tabbed_stats._addcards = mock_addcards
    tabbed_stats._addcards_central = None

    _close_addcards()

    assert mock_addcards._close_event_has_cleaned_up is False
    mock_addcards._close.assert_called_once()
    assert tabbed_stats._addcards is None


def test_on_stats_bridge_cmd_choose_deck():
    from tabbed_stats import _on_stats_bridge_cmd

    with patch('tabbed_stats._open_deck_chooser') as mock_open_deck:
        assert _on_stats_bridge_cmd("tabbed_stats_choose_deck") is True
        mock_open_deck.assert_called_once()


def test_open_deck_chooser_selects_chosen_deck_as_current():
    import aqt

    import tabbed_stats
    from tabbed_stats import _open_deck_chooser

    studydeck_mod = MagicMock()
    studydeck_mod.StudyDeck.return_value.name = "Japanese::Core"
    sys.modules['aqt.studydeck'] = studydeck_mod

    aqt.mw.col.decks.id_for_name.return_value = 12345
    tabbed_stats._stats_web = MagicMock()
    try:
        _open_deck_chooser()
    finally:
        tabbed_stats._stats_web = None

    aqt.mw.col.decks.id_for_name.assert_called_once_with("Japanese::Core")
    aqt.mw.col.decks.select.assert_called_once_with(12345)


def test_open_deck_chooser_cancel_does_not_change_current_deck():
    import aqt

    from tabbed_stats import _open_deck_chooser

    studydeck_mod = MagicMock()
    studydeck_mod.StudyDeck.return_value.name = ""
    sys.modules['aqt.studydeck'] = studydeck_mod

    _open_deck_chooser()

    aqt.mw.col.decks.select.assert_not_called()


def test_on_stats_bridge_cmd_browser_search():
    import aqt

    import tabbed_stats
    from tabbed_stats import _on_stats_bridge_cmd

    mock_browser = MagicMock()

    with patch('tabbed_stats._original_open', return_value=mock_browser) as mock_open:
        assert _on_stats_bridge_cmd("browserSearch:test query") is True
        mock_open.assert_called_once_with("Browser", aqt.mw)
        mock_browser.search_for.assert_called_once_with("test query")


def test_on_stats_bridge_cmd_other():
    from tabbed_stats import _on_stats_bridge_cmd

    assert _on_stats_bridge_cmd("unknown_cmd") is False


def test_on_state_did_change():
    from tabbed_stats import _on_state_did_change

    with (
        patch('tabbed_stats._close_stats') as mock_close_stats,
        patch('tabbed_stats._close_addcards') as mock_close_add,
        patch('tabbed_stats._restore_main_content') as mock_restore,
    ):

        _on_state_did_change("deckBrowser", "old")
        mock_close_stats.assert_called_once()
        mock_close_add.assert_called_once()
        mock_restore.assert_called_once()

        mock_close_stats.reset_mock()
        mock_close_add.reset_mock()
        mock_restore.reset_mock()

        _on_state_did_change("unknown", "old")
        mock_close_stats.assert_not_called()


def test_create_addcards_tab_leaves_addcards_class_dict_clean():
    """Regression: AddCards inherits show() from QWidget, so 'restoring' it by
    assignment plants the fetched sip unbound method into AddCards.__dict__,
    where it no longer binds self — the second Add click then dies with
    TypeError: show(self): first argument of unbound method must have type
    'QWidget'. The restore must leave the class dict untouched."""
    import aqt

    import tabbed_stats

    class FakeWidgetBase:
        def show(self):
            self.shown = True

    class FakeAddCards(FakeWidgetBase):
        def __init__(self, mw):
            self.show()  # real AddCards shows itself during __init__

        def centralWidget(self):
            return MagicMock()

        def hide(self):
            pass

    addcards_mod = MagicMock()
    addcards_mod.AddCards = FakeAddCards
    sys.modules['aqt.addcards'] = addcards_mod
    aqt.addcards = addcards_mod

    tabbed_stats._create_addcards_tab()

    assert 'show' not in FakeAddCards.__dict__
    # the "already open" branch calls _addcards.show(); it must bind and work
    tabbed_stats._addcards.show()
    assert tabbed_stats._addcards.shown


def test_patched_dialogs_open():
    import tabbed_stats
    from tabbed_stats import _patched_dialogs_open

    tabbed_stats._addcards = "addcards_obj"

    with (
        patch('tabbed_stats._create_stats_tab') as mock_stats,
        patch('tabbed_stats._create_addcards_tab') as mock_add,
        patch('tabbed_stats._original_open', return_value="orig") as mock_orig,
    ):

        assert _patched_dialogs_open("NewDeckStats") is None
        mock_stats.assert_called_once()

        assert _patched_dialogs_open("AddCards") == "addcards_obj"
        mock_add.assert_called_once()

        assert _patched_dialogs_open("Other", 1, 2, kw="arg") == "orig"
        mock_orig.assert_called_once_with("Other", 1, 2, kw="arg")
