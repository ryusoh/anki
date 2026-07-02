from unittest.mock import MagicMock

import pytest
from aqt.deckbrowser import DeckBrowser

from enhance_main_window.changeFunction import deckRow


def test_deckRow():
    node = MagicMock()
    node.htmlRow.return_value = "row_html"

    assert deckRow(None, node, 1, 2) == "row_html"
    node.htmlRow.assert_called_with(None, 1, 2)
