from aqt.deckbrowser import DeckBrowser

from .column import _linkHandler
from .node import renderDeckTree


# based on Anki 2.0.36 aqt/deckbrowser.py DeckBrowser._deckRow
def deckRow(self, node, depth, cnt):
    return node.htmlRow(self, depth, cnt)


DeckBrowser._deckRow = deckRow

DeckBrowser._renderDeckTree = renderDeckTree

DeckBrowser._linkHandler = _linkHandler
