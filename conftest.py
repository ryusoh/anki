import sys
from unittest.mock import MagicMock
import builtins

sys.modules['aqt'] = MagicMock()
sys.modules['aqt.browser'] = MagicMock()
sys.modules['aqt.qt'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()
sys.modules['aqt.webview'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()
sys.modules['aqt.main'] = MagicMock()
sys.modules['anki'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()

# Mocks for rewrite_text_of_study_cards
class MockDeckBrowser:
    _renderStats = MagicMock()

class MockOverview:
    pass

class MockDeckBrowserModule:
    pass

class MockOverviewModule:
    Overview = MockOverview

sys.modules['aqt.deckbrowser'] = MockDeckBrowserModule()
sys.modules['aqt.overview'] = MockOverviewModule()
builtins.DeckBrowser = MockDeckBrowser

# Mock for fa2_modified in graph analysis
sys.modules['fa2_modified'] = MagicMock()
