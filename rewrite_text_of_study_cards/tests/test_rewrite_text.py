import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def setup_module():
    mock_aqt = MagicMock()
    mock_gui_hooks = MagicMock()
    mock_aqt.gui_hooks = mock_gui_hooks
    mock_aqt.mw = MagicMock()

    class MockDeckBrowser:
        _renderStats = MagicMock()

    mock_aqt.deckbrowser.DeckBrowser = MockDeckBrowser

    class MockOverview:
        pass

    mock_aqt.overview.Overview = MockOverview

    class MockQTimer:
        singleShot = MagicMock()

    mock_aqt.qt.QTimer = MockQTimer

    sys.modules['aqt'] = mock_aqt
    sys.modules['aqt.deckbrowser'] = mock_aqt.deckbrowser
    sys.modules['aqt.overview'] = mock_aqt.overview
    sys.modules['aqt.qt'] = mock_aqt.qt

    if 'rewrite_text_of_study_cards' in sys.modules:
        del sys.modules['rewrite_text_of_study_cards']

    import rewrite_text_of_study_cards

    yield rewrite_text_of_study_cards

    if 'rewrite_text_of_study_cards' in sys.modules:
        del sys.modules['rewrite_text_of_study_cards']


def test_handleMyAddonConfig(setup_module):

    sys.modules['rewrite_text_of_study_cards.shige_config.addon_config'] = MagicMock()

    handled, message = setup_module.handleMyAddonConfig(
        False, "shige_rewrite_study_cards_text", None
    )
    assert handled is True
    assert message is None

    handled = setup_module.handleMyAddonConfig(False, "some_other_message", None)
    assert handled is False


def test_on_overview_will_set_content(setup_module):
    web_content = MagicMock()
    web_content.head = "<html><head></head>"

    class Overview:
        pass

    # We must patch isinstance inside the module, or ensure context is an instance of the mocked Overview
    from aqt.overview import Overview as MockedOverview

    context = MockedOverview()

    setup_module.on_overview_will_set_content(web_content, context)

    assert ".new-count, .learn-count, .review-count" in web_content.head
    assert "color: inherit !important;" in web_content.head


def test_renderStats_3(setup_module):

    mock_self = MagicMock()
    mock_self.mw.addonManager.getConfig.return_value = {"use_distinct_count": True}

    class MockSched:
        day_cutoff = 100000

    mock_self.mw.col.sched = MockSched()

    mock_self.mw.col.db.first.return_value = (10, 50000)
    mock_self.mw.col.format_timespan.return_value = "50s"

    from aqt.deckbrowser import DeckBrowser

    result = DeckBrowser._renderStats(mock_self)

    assert "50s" in result
    assert "10" in result
    assert "pycmd('shige_rewrite_study_cards_text')" in result


def test_renderStats_3_no_distinct(setup_module):

    mock_self = MagicMock()
    mock_self.mw.addonManager.getConfig.return_value = {"use_distinct_count": False}

    class MockSched:
        dayCutoff = 100000

    mock_self.mw.col.sched = MockSched()

    mock_self.mw.col.db.first.return_value = (0, 0)
    mock_self.mw.col.format_timespan.return_value = "0s"

    from aqt.deckbrowser import DeckBrowser

    result = DeckBrowser._renderStats(mock_self)

    assert "0" in result


def test_renderStats_3_exception(setup_module):

    mock_self = MagicMock()
    mock_self.mw.addonManager.getConfig.side_effect = Exception("Test Exception")

    mock_self._render_data.studied_today = "Default Studied Today"

    from aqt.deckbrowser import DeckBrowser

    result = DeckBrowser._renderStats(mock_self)

    assert "Default Studied Today" in result


def test_renderStats_3_format_timespan_exception(setup_module):

    mock_self = MagicMock()
    mock_self.mw.addonManager.getConfig.return_value = {"use_distinct_count": True}

    class MockSched:
        day_cutoff = 100000

    mock_self.mw.col.sched = MockSched()

    mock_self.mw.col.db.first.return_value = (10, 50000)
    mock_self.mw.col.format_timespan.side_effect = Exception("Format Exception")

    sys.modules['anki.utils'] = MagicMock()
    sys.modules['anki.utils'].fmtTimeSpan = MagicMock(return_value="Fallback Time")

    from aqt.deckbrowser import DeckBrowser

    result = DeckBrowser._renderStats(mock_self)

    assert "Fallback Time" in result


def test_on_overview_will_set_content_other(setup_module):
    web_content = MagicMock()
    web_content.head = "<html><head></head>"

    class DeckBrowser:
        pass

    context = DeckBrowser()
    setup_module.on_overview_will_set_content(web_content, context)

    assert ".new-count" not in web_content.head


def test_handleMyAddonConfig_handled():
    from rewrite_text_of_study_cards import handleMyAddonConfig

    assert not handleMyAddonConfig(False, "some_other_message", None)
    assert handleMyAddonConfig(True, "some_other_message", None)


def test_handleMyAddonConfig_shige(monkeypatch):
    import sys
    from unittest.mock import MagicMock

    from rewrite_text_of_study_cards import handleMyAddonConfig

    mock_addon_config = MagicMock()
    monkeypatch.setitem(
        sys.modules, 'rewrite_text_of_study_cards.shige_config.addon_config', mock_addon_config
    )

    mock_timer = MagicMock()
    monkeypatch.setattr("rewrite_text_of_study_cards.QTimer.singleShot", mock_timer)
    assert handleMyAddonConfig(False, "shige_rewrite_study_cards_text", None) == (True, None)
    mock_timer.assert_called_once()


def test_on_overview_will_set_content():
    from unittest.mock import MagicMock

    from aqt.overview import Overview

    from rewrite_text_of_study_cards import on_overview_will_set_content

    context = MagicMock(spec=Overview)
    web_content = MagicMock()
    web_content.head = "<html>"
    on_overview_will_set_content(web_content, context)
    assert "<style>" in web_content.head
    assert "color: inherit !important;" in web_content.head


def test_on_overview_will_set_content_not_overview():
    from unittest.mock import MagicMock

    from rewrite_text_of_study_cards import on_overview_will_set_content

    context = MagicMock()
    web_content = MagicMock()
    web_content.head = "<html>"
    on_overview_will_set_content(web_content, context)
    assert web_content.head == "<html>"


def test_renderStats_3(monkeypatch):
    from unittest.mock import MagicMock

    from rewrite_text_of_study_cards import _renderStats_3

    self = MagicMock()
    self.mw = MagicMock()
    self.mw.addonManager = MagicMock()
    self.mw.addonManager.getConfig.return_value = {
        "use_distinct_count": True,
        "custom_text": "Cards: {card_text}, Time: {time_text}, Avg: {avg_text}",
    }
    self.mw.col.sched.dayCutoff = 86400 * 2
    del self.mw.col.sched.day_cutoff
    self.mw.col.db.first.return_value = (10, 10000)
    self.mw.col.format_timespan.return_value = "10 seconds"
    monkeypatch.setattr("rewrite_text_of_study_cards.check_custom_text", lambda x: x)
    result = _renderStats_3(self)
    assert "Cards: 10, Time: 10 seconds, Avg: 1000.0" in result
    assert "shige_rewrite_study_cards_text" in result


def test_renderStats_3_fallback_formatting(monkeypatch, capsys):
    import sys
    from unittest.mock import MagicMock

    from rewrite_text_of_study_cards import _renderStats_3

    self = MagicMock()
    self.mw = MagicMock()
    self.mw.addonManager = MagicMock()
    self.mw.addonManager.getConfig.return_value = {
        "use_distinct_count": False,
        "custom_text": "Cards: {card_text}, Time: {time_text}, Avg: {avg_text}",
    }
    self.mw.col.sched.day_cutoff = 86400 * 2
    self.mw.col.db.first.return_value = (0, 0)
    self.mw.col.format_timespan.side_effect = Exception("Format failed")
    mock_anki_utils = MagicMock()
    mock_anki_utils.fmtTimeSpan.return_value = "fallback 0 seconds"
    monkeypatch.setitem(sys.modules, "anki.utils", mock_anki_utils)
    monkeypatch.setattr("rewrite_text_of_study_cards.check_custom_text", lambda x: x)
    result = _renderStats_3(self)
    assert "Cards: 0, Time: fallback 0 seconds, Avg: 0" in result
    captured = capsys.readouterr()
    assert "Format failed" in captured.out


def test_renderStats_3_exception(capsys):
    from unittest.mock import MagicMock

    from rewrite_text_of_study_cards import _renderStats_3

    self = MagicMock()
    self.mw.addonManager.getConfig.side_effect = Exception("Config error")
    self._render_data.studied_today = "Default text"
    result = _renderStats_3(self)
    assert '<div id="studiedToday"><span>Default text</span></div>' in result
    captured = capsys.readouterr()
    assert "Config error" in captured.out


def test_mini_button():
    from unittest.mock import MagicMock

    from rewrite_text_of_study_cards.shige_config.button_manager import mini_button

    button = MagicMock()
    mini_button(button)
    button.setStyleSheet.assert_called_once_with("QPushButton { padding: 2px; }")


def test_patrons_list_import():
    import rewrite_text_of_study_cards.shige_config.patrons_list

    assert True
