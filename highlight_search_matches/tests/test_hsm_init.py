import os
import sys
from unittest.mock import MagicMock, patch

# Mock aqt before import
sys.modules['aqt'] = MagicMock()

with patch('highlight_search_matches.init_addon') as mock_init:
    import highlight_search_matches


def test_log(tmp_path):
    import highlight_search_matches as hsm

    hsm.DEBUG_LOG = tmp_path / "test.log"
    hsm.log("test message")
    with open(hsm.DEBUG_LOG) as f:
        assert f.read() == "test message\n"


def test_log_respects_debug_config(tmp_path):
    import highlight_search_matches as hsm

    # Get the mocked aqt module
    aqt_mock = sys.modules["aqt"]

    # 1. Test when config has debug=False
    mock_mw = MagicMock()
    mock_mw.addonManager.getConfig.return_value = {"debug": False}
    aqt_mock.mw = mock_mw

    hsm.DEBUG_LOG = tmp_path / "test_no_debug.log"
    hsm.log("this should not be logged")
    assert not os.path.exists(hsm.DEBUG_LOG)

    # 2. Test when config has debug=True
    mock_mw.addonManager.getConfig.return_value = {"debug": True}
    hsm.log("this should be logged")
    with open(hsm.DEBUG_LOG) as f:
        assert f.read() == "this should be logged\n"

    # Clean up mock
    del aqt_mock.mw


def test_log_no_log_outside_pytest(tmp_path):
    import highlight_search_matches as hsm

    # Get mocked aqt and ensure mw is None
    aqt_mock = sys.modules["aqt"]
    if hasattr(aqt_mock, "mw"):
        del aqt_mock.mw

    # Simulate running outside pytest by temporarily removing it from sys.modules
    has_pytest = "pytest" in sys.modules
    pytest_module = sys.modules.get("pytest")
    if has_pytest:
        del sys.modules["pytest"]

    try:
        hsm.DEBUG_LOG = tmp_path / "test_no_pytest.log"
        hsm.log("should not be logged")
        assert not os.path.exists(hsm.DEBUG_LOG)
    finally:
        # Restore sys.modules
        if has_pytest:
            sys.modules["pytest"] = pytest_module


def test_init_addon_no_aqt():
    import highlight_search_matches as hsm

    # Remove aqt temporarily
    sys.modules.pop('aqt')

    with patch('highlight_search_matches.log'):
        hsm.init_addon()

    # restore
    sys.modules['aqt'] = MagicMock()


def test_init_addon_with_aqt():
    import highlight_search_matches as hsm

    with (
        patch('highlight_search_matches.log'),
        patch('highlight_search_matches.anki_integration.init_addon') as mock_browser,
        patch('highlight_search_matches.editor_integration.init_editor') as mock_editor,
    ):
        hsm.init_addon()

    assert mock_browser.called
    assert mock_editor.called
