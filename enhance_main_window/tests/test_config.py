from unittest.mock import MagicMock, patch

import pytest
from aqt import mw

import enhance_main_window.config as config_mod


@pytest.fixture(autouse=True)
def reset_globals():
    config_mod.userOption = None
    config_mod.fromName = None
    yield
    config_mod.userOption = None
    config_mod.fromName = None


def test_getUserOption():
    mw.addonManager.getConfig.return_value = {"a": 1, "columns": [{"name": "col1"}]}

    assert config_mod.getUserOption() == {"a": 1, "columns": [{"name": "col1"}]}
    assert config_mod.getUserOption("a") == 1

    assert config_mod.getUserOption("b", default=2) == 2
    mw.addonManager.writeConfig.assert_called_with(
        "enhance_main_window.config", {"a": 1, "columns": [{"name": "col1"}], "b": 2}
    )


def test_update():
    config_mod.userOption = {"x": 1}
    config_mod.fromName = {"y": 2}
    config_mod.update(None)
    assert config_mod.userOption is None
    assert config_mod.fromName is None


def test_getFromName():
    mw.addonManager.getConfig.return_value = {
        "columns": [{"name": "col1", "val": 1}, {"name": "col2", "val": 2}]
    }
    assert config_mod.getFromName("col1") == {"name": "col1", "val": 1}
    assert config_mod.getFromName("col3") is None
