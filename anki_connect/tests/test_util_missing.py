import pytest
import sys
import os
import importlib
from unittest.mock import patch, MagicMock
from anki_connect.util import patch_anki_2_1_50_having_null_stdout_on_windows, setting


def test_patch_anki_null_stdout():
    with patch('sys.stdout', None):
        with patch('builtins.open', return_value="mock_stdout") as mock_open:
            patch_anki_2_1_50_having_null_stdout_on_windows()
            assert sys.stdout == "mock_stdout"
            mock_open.assert_called_with(os.devnull, "w", encoding="utf8")


def test_patch_anki_not_null_stdout():
    mock_stdout = MagicMock()
    with patch('sys.stdout', mock_stdout):
        with patch('builtins.open') as mock_open:
            patch_anki_2_1_50_having_null_stdout_on_windows()
            assert sys.stdout == mock_stdout
            mock_open.assert_not_called()


def test_batched():
    import anki_connect.util

    with patch('sys.version_info', (3, 11)):
        importlib.reload(anki_connect.util)

        items = [1, 2, 3, 4, 5]
        result = list(anki_connect.util.batched(items, 2))
        assert result == [(1, 2), (3, 4), (5,)]

        result2 = list(anki_connect.util.batched([], 2))
        assert result2 == []

    importlib.reload(anki_connect.util)


def test_setting():
    mock_mw = MagicMock()
    mock_mw.addonManager.getConfig.return_value = {"key1": "value1"}
    with patch('anki_connect.util.aqt', MagicMock(mw=mock_mw)):
        with patch.dict('anki_connect.util.DEFAULT_CONFIG', {"key1": "default1"}):
            assert setting("key1") == "value1"


def test_setting_default():
    mock_mw = MagicMock()
    mock_mw.addonManager.getConfig.return_value = {}
    with patch('anki_connect.util.aqt', MagicMock(mw=mock_mw)):
        with patch.dict('anki_connect.util.DEFAULT_CONFIG', {"key2": "default2"}):
            assert setting("key2") == "default2"


def test_setting_exception():
    mock_mw = MagicMock()
    mock_mw.addonManager.getConfig.side_effect = Exception("Test Exception")
    with patch('anki_connect.util.aqt', MagicMock(mw=mock_mw)):
        with pytest.raises(Exception, match="setting key3 not found"):
            setting("key3")
