import unittest
from unittest.mock import MagicMock

from aqt.main import AnkiQt

import hide_window_title


class TestHideWindowTitle(unittest.TestCase):
    def test_monkey_patch(self):
        mock_instance = MagicMock()
        # Ensure our mock returns a mock for setWindowTitle if it's not defined
        AnkiQt.setWindowTitle(mock_instance, "foo")


if __name__ == '__main__':
    unittest.main()
