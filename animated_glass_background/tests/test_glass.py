import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.fixture(autouse=True)
def mock_aqt():
    aqt_mock = MagicMock()
    mw_mock = MagicMock()
    aqt_mock.mw = mw_mock
    aqt_mock.gui_hooks = MagicMock()
    aqt_mock.webview = MagicMock()

    sys.modules['aqt'] = aqt_mock
    sys.modules['aqt.gui_hooks'] = aqt_mock.gui_hooks
    sys.modules['aqt.webview'] = aqt_mock.webview

    if 'animated_glass_background' in sys.modules:
        del sys.modules['animated_glass_background']

    yield aqt_mock

    for k in list(sys.modules.keys()):
        if k.startswith('aqt'):
            del sys.modules[k]
    if 'animated_glass_background' in sys.modules:
        del sys.modules['animated_glass_background']


def test_get_addon_config(mock_aqt):
    from animated_glass_background import get_addon_config

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    assert get_addon_config() == {"enabled": True}

    mock_aqt.mw.addonManager.getConfig.return_value = None
    assert get_addon_config() == {}


def test_on_webview_will_set_content_no_context(mock_aqt):
    from animated_glass_background import on_webview_will_set_content

    web_content = MagicMock()
    on_webview_will_set_content(web_content, None)


def test_on_webview_will_set_content_disabled(mock_aqt):
    from animated_glass_background import on_webview_will_set_content

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": False}
    web_content = MagicMock()
    on_webview_will_set_content(web_content, "context")


def test_on_webview_will_set_content_injected(mock_aqt):
    from animated_glass_background import on_webview_will_set_content

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    web_content = MagicMock()
    web_content.css = ["deckbrowser.css"]
    web_content.head = ""
    web_content.js = []

    on_webview_will_set_content(web_content, "context")
    assert "window.glassEffectConfig" in web_content.head

    # second run to trigger js append path
    web_content.js = ["/_addons/animated_glass_background/web/glass_effect.js"]
    on_webview_will_set_content(web_content, "context")


def test_on_webview_will_set_content_not_target(mock_aqt):
    from animated_glass_background import on_webview_will_set_content

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    web_content = MagicMock()
    web_content.css = ["unknown.css"]
    on_webview_will_set_content(web_content, "context")


def test_get_glass_effect_js_success(mock_aqt):
    import animated_glass_background
    from animated_glass_background import get_glass_effect_js

    animated_glass_background._glass_effect_js = None

    m_open = mock_open(read_data="JS_CODE")
    with patch("builtins.open", m_open):
        res = get_glass_effect_js()
        assert res == "JS_CODE"

        # Test caching
        res2 = get_glass_effect_js()
        assert res2 == "JS_CODE"
        assert m_open.call_count == 1


def test_get_glass_effect_js_failure(mock_aqt):
    import animated_glass_background
    from animated_glass_background import get_glass_effect_js

    animated_glass_background._glass_effect_js = None

    m_open = mock_open()
    m_open.side_effect = Exception("Open error")
    with patch("builtins.open", m_open):
        res = get_glass_effect_js()
        assert res == ""


def test_on_webview_did_inject_style_into_page_error(mock_aqt):
    from animated_glass_background import on_webview_did_inject_style_into_page

    web = MagicMock()
    web.page.side_effect = Exception("Page error")
    on_webview_did_inject_style_into_page(web)


def test_on_webview_did_inject_style_into_page_disabled(mock_aqt):
    from animated_glass_background import on_webview_did_inject_style_into_page

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": False}
    web = MagicMock()
    web.page().url().path.return_value = "/path/congrats.html"
    on_webview_did_inject_style_into_page(web)
    web.eval.assert_not_called()


def test_on_webview_did_inject_style_into_page_success(mock_aqt):
    from animated_glass_background import on_webview_did_inject_style_into_page

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    web = MagicMock()
    web.page().url().path.return_value = "/path/congrats.html"

    with patch(
        'animated_glass_background.get_glass_effect_js', return_value="console.log('test');"
    ):
        on_webview_did_inject_style_into_page(web)

    assert web.eval.call_count == 2
    web.eval.assert_any_call("console.log('test');")


def test_on_webview_did_inject_style_into_page_not_target(mock_aqt):
    from animated_glass_background import on_webview_did_inject_style_into_page

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    web = MagicMock()
    web.page().url().path.return_value = "/path/unknown.html"

    on_webview_did_inject_style_into_page(web)
    web.eval.assert_not_called()


def test_on_webview_did_inject_style_into_page_no_script(mock_aqt):
    from animated_glass_background import on_webview_did_inject_style_into_page

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    web = MagicMock()
    web.page().url().path.return_value = "/path/congrats.html"

    with patch('animated_glass_background.get_glass_effect_js', return_value=""):
        on_webview_did_inject_style_into_page(web)

    web.eval.assert_not_called()
