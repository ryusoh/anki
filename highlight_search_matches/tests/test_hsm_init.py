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
