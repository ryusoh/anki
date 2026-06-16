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
