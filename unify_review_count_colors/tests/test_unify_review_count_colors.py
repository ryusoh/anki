import importlib
import sys
from unittest.mock import MagicMock


def test_unify_review_count_colors():
    mock_aqt = MagicMock()
    mock_gui_hooks = MagicMock()
    mock_gui_hooks.webview_will_set_content = []
    mock_aqt.gui_hooks = mock_gui_hooks

    sys.modules['aqt'] = mock_aqt

    import unify_review_count_colors

    importlib.reload(unify_review_count_colors)

    assert len(unify_review_count_colors.gui_hooks.webview_will_set_content) == 1
    handler = unify_review_count_colors.gui_hooks.webview_will_set_content[0]

    # Test wrong context
    class WrongContext:
        pass

    web_content_wrong = MagicMock()
    web_content_wrong.head = ""
    handler(web_content_wrong, WrongContext())
    assert web_content_wrong.head == ""

    # Test correct context
    class ReviewerBottomBar:
        pass

    web_content = MagicMock()
    web_content.head = ""
    handler(web_content, ReviewerBottomBar())

    assert "color: var(--text-fg, white) !important;" in web_content.head
