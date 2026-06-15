import importlib.util
import sys
from unittest.mock import MagicMock

import pytest

# Mock out aqt before importing rewrite_text_of_study_cards
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.deckbrowser'] = MagicMock()
sys.modules['aqt.overview'] = MagicMock()
sys.modules['aqt.qt'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()
sys.modules['anki'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()

sys.modules['aqt.deckbrowser'].DeckBrowser = MagicMock()
sys.modules['aqt.overview'].Overview = MagicMock()

import rewrite_text_of_study_cards
from rewrite_text_of_study_cards.path_manager import MESSAGE_TEMPLATE, check_custom_text


def test_check_custom_text():
    assert check_custom_text("foo") == "foo"
    assert check_custom_text(MESSAGE_TEMPLATE) == MESSAGE_TEMPLATE
