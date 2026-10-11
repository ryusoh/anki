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
    sys.modules['aqt.qt'] = aqt_mock.qt

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


def test_on_webview_will_set_content_editor_context(mock_aqt):
    from animated_glass_background import on_webview_will_set_content

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    web_content = MagicMock()
    web_content.css = ["other.css"]
    web_content.head = ""
    web_content.js = []

    editor_context = MagicMock()
    editor_context.__class__.__name__ = "Editor"
    editor_context.parentWindow = MagicMock(__class__=MagicMock(__name__="AddCards"))

    on_webview_will_set_content(web_content, editor_context)
    assert "window.glassEffectConfig" in web_content.head
    assert "/_addons/animated_glass_background/web/glass_effect.js" in web_content.js


def test_on_webview_will_set_content_browser_editor_ignored(mock_aqt):
    from animated_glass_background import on_webview_will_set_content

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    web_content = MagicMock()
    web_content.css = ["editor.css"]
    web_content.head = ""
    web_content.js = []

    browser_editor = MagicMock()
    browser_editor.__class__.__name__ = "Editor"
    browser_editor.parentWindow = MagicMock(__class__=MagicMock(__name__="Browser"))

    on_webview_will_set_content(web_content, browser_editor)
    assert "window.glassEffectConfig" not in web_content.head
    assert len(web_content.js) == 0


def test_on_webview_did_inject_style_into_page_overview(mock_aqt):
    from animated_glass_background import on_webview_did_inject_style_into_page

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    web = MagicMock()
    web.page().url().path.return_value = "/_anki/pages/overview.html"

    with patch(
        'animated_glass_background.get_glass_effect_js', return_value="console.log('overview');"
    ):
        on_webview_did_inject_style_into_page(web)

    assert web.eval.call_count == 2
    web.eval.assert_any_call("console.log('overview');")


def test_on_editor_did_init(mock_aqt):
    from animated_glass_background import on_editor_did_init

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    editor = MagicMock()
    editor.parentWindow = MagicMock(__class__=MagicMock(__name__="AddCards"))

    with patch(
        'animated_glass_background.get_glass_effect_js', return_value="console.log('editor_init');"
    ):
        on_editor_did_init(editor)

    assert editor.web.eval.call_count == 2
    editor.web.eval.assert_any_call("console.log('editor_init');")


def test_on_editor_did_init_browser_ignored(mock_aqt):
    from animated_glass_background import on_editor_did_init

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    editor = MagicMock()
    editor.parentWindow = MagicMock(__class__=MagicMock(__name__="Browser"))

    with patch(
        'animated_glass_background.get_glass_effect_js', return_value="console.log('editor_init');"
    ):
        on_editor_did_init(editor)

    editor.web.eval.assert_not_called()


def test_on_editor_did_init_disabled(mock_aqt):
    from animated_glass_background import on_editor_did_init

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": False}
    editor = MagicMock()

    on_editor_did_init(editor)
    editor.web.eval.assert_not_called()


def test_on_add_cards_did_init(mock_aqt):
    from animated_glass_background import on_add_cards_did_init

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    addcards = MagicMock()
    mock_aqt.qt.QColor = MagicMock()

    on_add_cards_did_init(addcards)
    addcards.setStyleSheet.assert_called_once()
    addcards.editor.web.setStyleSheet.assert_called_once_with(
        "background: transparent; border: none;"
    )


def test_on_add_cards_did_init_disabled(mock_aqt):
    from animated_glass_background import on_add_cards_did_init

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": False}
    addcards = MagicMock()

    on_add_cards_did_init(addcards)
    addcards.setStyleSheet.assert_not_called()


def test_on_add_cards_did_init_error(mock_aqt):
    from animated_glass_background import on_add_cards_did_init

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    addcards = MagicMock()
    addcards.setStyleSheet.side_effect = Exception("Style error")

    # Should not raise exception
    on_add_cards_did_init(addcards)


def _install_theme(var_value, night_mode=True):
    theme = MagicMock()
    theme.theme_manager.var.return_value = var_value
    theme.theme_manager.night_mode = night_mode
    sys.modules['aqt.theme'] = theme
    return theme


def test_glass_window_gradient_matches_canvas_glow_over_theme_canvas(mock_aqt):
    from animated_glass_background import glass_window_gradient

    _install_theme("#2c2c2c")
    gradient = glass_window_gradient(
        {"ambientGlowColor": "rgba(118, 183, 229, 0.4)", "ambientGlowOpacity": 0.8}
    )
    assert gradient == (
        "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
        "stop:0.0 #415461, stop:0.6 #39454d, stop:1.0 #2f3133)"
    )


def test_glass_window_gradient_fallbacks(mock_aqt):
    from animated_glass_background import glass_window_gradient

    _install_theme(None, night_mode=False)
    light = glass_window_gradient({"ambientGlowColor": "not-a-color"})
    assert light.startswith("qlineargradient(") and "stop:1.0 #" in light

    sys.modules.pop('aqt.theme', None)
    assert "stop:0.0 #415461" in glass_window_gradient({})


def test_is_add_cards_editor(mock_aqt):
    from animated_glass_background import _is_add_cards_editor

    class AddCards:
        pass

    class Browser:
        pass

    add_editor = MagicMock(parentWindow=AddCards())
    browser_editor = MagicMock(parentWindow=Browser())
    assert _is_add_cards_editor(add_editor) is True
    assert _is_add_cards_editor(browser_editor) is False
    assert _is_add_cards_editor(AddCards()) is True
    assert _is_add_cards_editor(None) is False


def test_on_add_cards_did_init_paints_window_gradient_once(mock_aqt):
    from animated_glass_background import on_add_cards_did_init

    _install_theme("#2c2c2c")
    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    addcards = MagicMock()

    on_add_cards_did_init(addcards)
    qss = addcards.setStyleSheet.call_args[0][0]
    assert "QMainWindow" in qss and "qlineargradient" in qss
    assert "centralwidget" in qss
    central_qss = addcards.centralWidget().setStyleSheet.call_args[0][0]
    assert "qlineargradient" in central_qss
    assert "QPushButton" in central_qss
    addcards.form.modelArea.setStyleSheet.assert_called_once_with(
        "background: transparent; border: none;"
    )


def test_on_editor_did_init_calls_add_cards_init(mock_aqt):
    from animated_glass_background import on_editor_did_init

    mock_aqt.mw.addonManager.getConfig.return_value = {"enabled": True}
    editor = MagicMock()
    parent = MagicMock()
    parent.__class__.__name__ = "AddCards"
    editor.parentWindow = parent

    with patch("animated_glass_background.on_add_cards_did_init") as mock_add_init:
        on_editor_did_init(editor)
        mock_add_init.assert_called_once_with(parent, editor=editor)


def test_on_dialog_manager_did_open(mock_aqt):
    from animated_glass_background import on_dialog_manager_did_open

    dialog_instance = MagicMock()
    with patch("animated_glass_background.on_add_cards_did_init") as mock_add_init:
        on_dialog_manager_did_open(None, "AddCards", dialog_instance)
        mock_add_init.assert_called_once_with(dialog_instance)

        mock_add_init.reset_mock()
        on_dialog_manager_did_open(None, "Browser", dialog_instance)
        mock_add_init.assert_not_called()
