import importlib
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock anki.stats colors BEFORE importing strings
anki_mock = MagicMock()
anki_stats_mock = MagicMock()
anki_stats_mock.colRelearn = "colRelearn_val"
anki_stats_mock.colUnseen = "colUnseen_val"
anki_stats_mock.colLearn = "colLearn_val"
anki_stats_mock.colSusp = "colSusp_val"
anki_stats_mock.colYoung = "colYoung_val"
anki_stats_mock.colMature = "colMature_val"
anki_stats_mock.colCum = "colCum_val"

sys.modules['anki'] = anki_mock
sys.modules['anki.stats'] = anki_stats_mock

import enhance_main_window.strings as strings_module

# strings.py binds its color names via `from anki.stats import *` at first import.
# Another suite may have imported it first under the conftest's bare anki.stats mock
# (no col* attributes), leaving those names unbound. Reload so they bind from the
# mock above regardless of collection order.
importlib.reload(strings_module)


class TestStrings(unittest.TestCase):
    def test_getHeader(self):
        # Without header key
        conf = {"name": "cards seen today"}
        self.assertIsNone(strings_module.getHeader(conf))

        # With header None
        conf = {"name": "cards seen today", "header": None}
        self.assertEqual(strings_module.getHeader(conf), "Today")

        # With explicit header
        conf = {"name": "cards seen today", "header": "Custom Header"}
        self.assertEqual(strings_module.getHeader(conf), "Custom Header")

        # Dynamic flag header
        conf = {"name": "flag 1", "header": None}
        self.assertEqual(strings_module.getHeader(conf), "Flag {i}")

    def test_getOverlay(self):
        # Without overlay key -> uses default
        conf = {"name": "leech"}
        self.assertEqual(strings_module.getOverlay(conf), "Number of note with a leech card")

        # With overlay key
        conf = {"name": "leech", "overlay": "Custom Overlay"}
        self.assertEqual(strings_module.getOverlay(conf), "Custom Overlay")

        # Overlay is None in config -> uses defaultOverlay
        conf = {"name": "bar", "overlay": None}
        self.assertIsNone(strings_module.getOverlay(conf))

        # Flags overlay
        conf = {"name": "flag 2"}
        self.assertEqual(strings_module.getOverlay(conf), "Number of cards with flag 2")

    def test_getColor(self):
        # Explicit color
        conf = {"name": "leech", "color": "#FF0000"}
        self.assertEqual(strings_module.getColor(conf), "#FF0000")

        # Match keywords in name
        conf = {"name": "my new cards"}
        self.assertEqual(strings_module.getColor(conf), "colLearn_val")

        conf = {"name": "some buried things"}
        self.assertEqual(strings_module.getColor(conf), "colSusp_val")

        conf = {"name": "learning something"}
        self.assertEqual(strings_module.getColor(conf), "colRelearn_val")

        conf = {"name": "unseen stuff"}
        self.assertEqual(strings_module.getColor(conf), "colUnseen_val")

        conf = {"name": "suspended"}
        self.assertEqual(strings_module.getColor(conf), "colSusp_val")

        conf = {"name": "young ones"}
        self.assertEqual(strings_module.getColor(conf), "colYoung_val")

        conf = {"name": "mature ones"}
        self.assertEqual(strings_module.getColor(conf), "colMature_val")

        conf = {"name": "repeated tasks"}
        self.assertEqual(strings_module.getColor(conf), "colCum_val")

        # No match, use default user option
        with patch('enhance_main_window.strings.getUserOption', return_value="custom_default"):
            conf = {"name": "unknown"}
            self.assertEqual(strings_module.getColor(conf), "custom_default")
