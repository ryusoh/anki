import unittest

from rewrite_text_of_study_cards.path_manager import MESSAGE_TEMPLATE, check_custom_text


class TestPathManager(unittest.TestCase):
    def test_check_custom_text(self):
        self.assertEqual(check_custom_text("foo"), "foo")


if __name__ == '__main__':
    unittest.main()
