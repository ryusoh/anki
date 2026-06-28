import sys
from unittest.mock import MagicMock


def pytest_configure(config):
    deck_browser = sys.modules['aqt.deckbrowser'].DeckBrowser
    if not hasattr(deck_browser, '_linkHandler'):
        deck_browser._linkHandler = MagicMock()

    anki_mock = sys.modules.get('anki')
    if anki_mock:
        utils_mock = MagicMock()
        utils_mock.ids2str = MagicMock(return_value="")
        utils_mock.int_time = MagicMock(return_value=123)
        anki_mock.utils = utils_mock
        sys.modules['anki.utils'] = utils_mock

        stats_mock = MagicMock()
        anki_mock.stats = stats_mock
        sys.modules['anki.stats'] = stats_mock

        lang_mock = MagicMock()
        anki_mock.lang = lang_mock
        sys.modules['anki.lang'] = lang_mock
