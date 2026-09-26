import unittest

from unify_review_count_colors import on_webview_will_set_content


class MockContext:
    def __init__(self, name):
        self.__class__.__name__ = name


class MockWebContent:
    def __init__(self):
        self.head = ""


class TestUnifyReviewCountColors(unittest.TestCase):
    def test_on_webview_will_set_content_reviewer_bottom_bar(self):
        context = MockContext("ReviewerBottomBar")
        web_content = MockWebContent()
        on_webview_will_set_content(web_content, context)
        self.assertIn(".new-count, .learn-count, .review-count {", web_content.head)

    def test_on_webview_will_set_content_other(self):
        context = MockContext("Other")
        web_content = MockWebContent()
        on_webview_will_set_content(web_content, context)
        self.assertEqual(web_content.head, "")


import sys
from unittest.mock import MagicMock

sys.modules['aqt'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()

import unify_review_count_colors


class TestUnifyReviewCountColorsCoverage(unittest.TestCase):
    def test_on_webview_will_set_content(self):
        context = MagicMock()
        context.__class__.__name__ = "ReviewerBottomBar"
        web_content = MagicMock()
        web_content.head = ""

        unify_review_count_colors.on_webview_will_set_content(web_content, context)
        self.assertIn(".new-count, .learn-count, .review-count", web_content.head)

    def test_on_webview_will_set_content_other_context(self):
        context = MagicMock()
        context.__class__.__name__ = "OtherContext"
        web_content = MagicMock()
        web_content.head = ""

        unify_review_count_colors.on_webview_will_set_content(web_content, context)
        self.assertEqual(web_content.head, "")


if __name__ == '__main__':
    unittest.main()
