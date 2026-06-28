import builtins
import sys
import types
from unittest.mock import MagicMock


class MockModule(types.ModuleType):
    def __getattr__(self, name):
        if name == '__all__':
            return []
        return MagicMock()


for mod in [
    'aqt',
    'aqt.browser',
    'aqt.qt',
    'aqt.editor',
    'aqt.webview',
    'aqt.utils',
    'aqt.gui_hooks',
    'aqt.main',
    'aqt.deckbrowser',
    'anki',
    'anki.hooks',
    'anki.utils',
    'anki.lang',
    'anki.stats',
]:
    sys.modules[mod] = MockModule(mod)


class MockDeckBrowser:
    _renderStats = MagicMock()
    _linkHandler = MagicMock()


class MockOverview:
    pass


class MockDeckBrowserModule:
    DeckBrowser = MockDeckBrowser
    __all__ = []


class MockOverviewModule:
    Overview = MockOverview
    __all__ = []


sys.modules['aqt.deckbrowser'] = MockDeckBrowserModule()
sys.modules['aqt.overview'] = MockOverviewModule()
builtins.DeckBrowser = MockDeckBrowser

# Mock for fa2_modified in graph analysis
sys.modules['fa2_modified'] = MagicMock()
