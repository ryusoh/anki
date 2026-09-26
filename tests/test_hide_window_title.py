import unittest
from unittest.mock import MagicMock

from aqt.main import AnkiQt

import hide_window_title


class TestHideWindowTitle(unittest.TestCase):
    def test_monkey_patch(self):
        mock_instance = MagicMock()
        # Ensure our mock returns a mock for setWindowTitle if it's not defined
        AnkiQt.setWindowTitle(mock_instance, "foo")


import importlib
import sys

sys.modules['aqt'] = MagicMock()
sys.modules['aqt.main'] = MagicMock()


class DummyAnkiQt:
    def setWindowTitle(self, title):
        self.title = title


sys.modules['aqt.main'].AnkiQt = DummyAnkiQt


class TestHideWindowTitleCoverage(unittest.TestCase):
    def test_monkey_patch_coverage(self):
        if hasattr(DummyAnkiQt, "_hide_window_title_patched"):
            delattr(DummyAnkiQt, "_hide_window_title_patched")

        sys.modules['aqt'].mw = None
        import hide_window_title

        importlib.reload(hide_window_title)
        self.assertTrue(DummyAnkiQt._hide_window_title_patched)

        instance = DummyAnkiQt()
        DummyAnkiQt.setWindowTitle(instance, "new title")
        self.assertEqual(instance.title, "")

        importlib.reload(hide_window_title)
        self.assertTrue(DummyAnkiQt._hide_window_title_patched)

        sys.modules['aqt'].mw = MagicMock()
        importlib.reload(hide_window_title)
        sys.modules['aqt'].mw.setWindowTitle.assert_called_once_with("")


if __name__ == '__main__':
    unittest.main()
