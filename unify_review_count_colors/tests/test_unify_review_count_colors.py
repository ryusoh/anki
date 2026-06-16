import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def setup_module():
    mock_aqt = MagicMock()
    mock_gui_hooks = MagicMock()
    mock_aqt.gui_hooks = mock_gui_hooks
    mock_aqt.mw = MagicMock()

    sys.modules['aqt'] = mock_aqt

    if 'unify_review_count_colors' in sys.modules:
        del sys.modules['unify_review_count_colors']

    import unify_review_count_colors

    yield unify_review_count_colors

    if 'unify_review_count_colors' in sys.modules:
        del sys.modules['unify_review_count_colors']


def test_on_webview_will_set_content_reviewer(setup_module):
    # Setup
    module = setup_module
    web_content = MagicMock()
    web_content.head = "<html><head></head>"

    class ReviewerBottomBar:
        pass

    context = ReviewerBottomBar()

    # Act
    module.on_webview_will_set_content(web_content, context)

    # Assert
    assert ".new-count, .learn-count, .review-count" in web_content.head
    assert "color: var(--text-fg, white) !important;" in web_content.head


def test_on_webview_will_set_content_other_context(setup_module):
    # Setup
    module = setup_module
    web_content = MagicMock()
    web_content.head = "<html><head></head>"

    class DeckBrowser:
        pass

    context = DeckBrowser()

    # Act
    module.on_webview_will_set_content(web_content, context)

    # Assert
    assert ".new-count" not in web_content.head
