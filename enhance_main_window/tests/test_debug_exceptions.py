from unittest.mock import MagicMock

import pytest

from enhance_main_window.debug import assertEqual


def test_assertEqual_none_difference(capsys):
    left = MagicMock()
    left.firstDifference.return_value = None
    right = MagicMock()
    right.firstDifference.return_value = None
    with pytest.raises(TypeError):
        assertEqual(left, right)


def test_assertEqual_other_difference():
    left = MagicMock()
    left.firstDifference.return_value = "string"
    right = MagicMock()
    right.firstDifference.return_value = "string"
    with pytest.raises(TypeError):
        assertEqual(left, right)


def test_assertEqual_none_type_difference():
    MagicMock()
    pass
