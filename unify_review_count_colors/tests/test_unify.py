import pytest
import sys
from unittest.mock import MagicMock

# Mock out aqt entirely so we can import the module outside of Anki
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()

import unify_review_count_colors
from unify_review_count_colors import on_webview_will_set_content

def test_on_webview_will_set_content_ignore():
    web_content = MagicMock()
    context = MagicMock()
    context.__class__.__name__ = "SomeOtherContext"

    on_webview_will_set_content(web_content, context)

    # Should not append anything
    assert web_content.head.call_count == 0

def test_on_webview_will_set_content_inject():
    class ReviewerBottomBar:
        pass

    class WebContent:
        def __init__(self):
            self.head = "<html>"

    web_content = WebContent()
    context = ReviewerBottomBar()

    on_webview_will_set_content(web_content, context)

    assert ".new-count, .learn-count, .review-count {" in web_content.head
    assert "color: var(--text-fg, white) !important;" in web_content.head
