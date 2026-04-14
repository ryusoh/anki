import pytest
import sys
import importlib.util
from unittest.mock import MagicMock

# Mock out aqt before importing rewrite_text_of_study_cards
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.deckbrowser'] = MagicMock()
sys.modules['aqt.overview'] = MagicMock()
sys.modules['aqt.qt'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()
sys.modules['anki'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()

# But wait, deckbrowser etc might fail to import if DeckBrowser class isn't defined
sys.modules['aqt.deckbrowser'].DeckBrowser = MagicMock()
sys.modules['aqt.overview'].Overview = MagicMock()

import rewrite_text_of_study_cards
from rewrite_text_of_study_cards.path_manager import check_custom_text, MESSAGE_TEMPLATE

def test_check_custom_text():
    assert check_custom_text("foo") == "foo"
    assert check_custom_text(MESSAGE_TEMPLATE) == MESSAGE_TEMPLATE
