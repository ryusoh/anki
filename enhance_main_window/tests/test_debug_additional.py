from unittest.mock import patch
import enhance_main_window.debug as debug_module
import unittest

class GenRightOnly:
    def firstDifference(self, other):
        return None

class TestDebugAdditional2(unittest.TestCase):
    def test_assert_equal_right_only(self):
        with patch('builtins.print') as mock_print:
            debug_module.assertEqual(1, GenRightOnly())
            mock_print.assert_any_call("Only the second is a Gen")

class GenNone:
    def firstDifference(self, other):
        return None

class TestDebugAdditionalFix(unittest.TestCase):
    def test_assert_equal_none_diff_type(self):
        with patch('builtins.print') as mock_print:
            with self.assertRaises(TypeError):
                debug_module.assertEqual(GenNone(), GenNone())
