# Browser table highlighting has been removed as Anki 23.10+ uses native Qt
# rendering (QItemDelegate) which doesn't support HTML in cells.
# The editor highlighting (in editor_integration.py) still works correctly.


def init_addon():
    # Browser table highlighting disabled - not supported in modern Anki
    pass
