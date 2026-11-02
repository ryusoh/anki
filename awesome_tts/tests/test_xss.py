import html
import sys
from unittest.mock import MagicMock, patch

import aqt
import pytest


@patch('aqt.utils.showInfo')
def test_configurator_account_info_xss_escaping(mock_showInfo):
    sys.modules['aqt'] = MagicMock()
    sys.modules['aqt.qt'] = MagicMock()
    sys.modules['aqt.qt.QAction'] = type('QAction', (object,), {})
    sys.modules['aqt.utils'] = MagicMock()
    from awesome_tts.awesometts.gui.configurator import Configurator

    mock_addon = MagicMock()
    mock_addon.languagetools.account_info.return_value = {
        'status': '<script>alert(1)</script>',
        'update_url': 'https://example.com/upgrade"><script>alert(2)</script>',
        'cancel_url': 'https://example.com/cancel"><script>alert(3)</script>',
    }

    # We patch __init__ since we don't need UI initialization
    with patch.object(Configurator, '__init__', lambda self, addon: None):
        configurator = Configurator(mock_addon)
        configurator._addon = mock_addon

        mock_lineedit = MagicMock()
        mock_lineedit.text.return_value = 'some_key'

        configurator._on_plus_account_info(mock_lineedit, MagicMock())

        mock_showInfo.assert_called_once()
        html_output = mock_showInfo.call_args[0][0]

        assert '<script>' not in html_output
        assert '&lt;script&gt;' in html_output
        assert (
            'href=&#x27;' in html_output
            or 'href=&#39;' in html_output
            or 'href=&quot;' in html_output
            or 'href=\'https://example.com/upgrade&quot;&gt;&lt;script&gt;alert(2)&lt;/script&gt;\''
            in html_output
        )
