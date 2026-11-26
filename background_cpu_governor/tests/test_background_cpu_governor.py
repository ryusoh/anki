"""Unit tests for background_cpu_governor core helpers and Qt wiring."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from background_cpu_governor.core import (
    DEFAULT_CONFIG,
    build_config_script,
    build_set_enabled_script,
    build_set_paused_script,
    detect_software_compositing,
    format_status_report,
    normalize_config,
    to_js_config,
)


def test_normalize_config_defaults_and_partial() -> None:
    assert normalize_config(None) == DEFAULT_CONFIG
    partial = normalize_config({"enabled": False, "pause_raf": 0})
    assert partial["enabled"] is False
    assert partial["pause_raf"] is False
    assert partial["pause_css_animations"] is True
    assert partial["pause_on_app_deactivate"] is True


def test_js_builders() -> None:
    js_cfg = to_js_config({"enabled": True, "pause_css_animations": False, "pause_raf": True})
    assert js_cfg == {
        "enabled": True,
        "pauseCssAnimations": False,
        "pauseRaf": True,
    }
    script = build_config_script({"enabled": False})
    assert '"enabled": false' in script
    assert "window.__ankiCpuGovernorConfig =" in script
    assert "setPaused(true)" in build_set_paused_script(True)
    assert "setPaused(false)" in build_set_paused_script(False)
    assert "setEnabled(true)" in build_set_enabled_script(True)
    assert "setEnabled(false)" in build_set_enabled_script(False)


def test_detect_software_compositing() -> None:
    assert detect_software_compositing({}) is False
    assert (
        detect_software_compositing({"QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu-compositing"})
        is True
    )
    assert detect_software_compositing({}, qt_flags="--disable-gpu") is True
    assert detect_software_compositing({"ANKI_VIDEO_DRIVER": "software"}) is True
    assert detect_software_compositing({"QT_OPENGL": "Software"}) is True
    assert detect_software_compositing({"QT_QUICK_BACKEND": "software"}) is True


def test_format_status_report() -> None:
    report = format_status_report(
        enabled=True,
        paused=True,
        webview_count=3,
        software_compositing=True,
    )
    assert "Throttling: Enabled" in report
    assert "Paused (background)" in report
    assert "Governed WebViews: 3" in report
    assert "--disable-gpu-compositing" in report

    active_report = format_status_report(
        enabled=False,
        paused=False,
        webview_count=0,
        software_compositing=False,
    )
    assert "Throttling: Disabled" in active_report
    assert "Active (focused)" in active_report
    assert "Hardware / Default" in active_report


@pytest.fixture()
def loaded_governor():
    aqt_mock = MagicMock()
    aqt_mock.gui_hooks.webview_will_set_content = []
    aqt_mock.gui_hooks.main_window_did_init = []
    mw_mock = MagicMock()
    mw_mock.addonManager.getConfig.return_value = None
    mw_mock.web = MagicMock()
    mw_mock.web.eval = MagicMock()
    mw_mock.toolbar.web = MagicMock()
    mw_mock.toolbar.web.eval = MagicMock()
    mw_mock.bottomWeb = MagicMock()
    mw_mock.bottomWeb.eval = MagicMock()
    mw_mock._cpu_governor_menu_installed = False
    aqt_mock.mw = mw_mock

    qt_mock = MagicMock()

    class _BaseQObject:
        def __init__(self, *args, **kwargs) -> None:
            pass

    qt_mock.QObject = _BaseQObject
    qt_mock.QEvent.Type.ApplicationDeactivate = 122
    qt_mock.QEvent.Type.ApplicationActivate = 121
    app_mock = MagicMock()
    app_mock._cpu_governor_filter_installed = False
    app_mock.allWidgets.return_value = [mw_mock.web]
    qt_mock.QApplication.instance.return_value = app_mock

    saved_modules = {
        k: sys.modules.get(k)
        for k in ("aqt", "aqt.gui_hooks", "aqt.qt", "aqt.utils", "background_cpu_governor")
    }
    sys.modules["aqt"] = aqt_mock
    sys.modules["aqt.gui_hooks"] = aqt_mock.gui_hooks
    sys.modules["aqt.qt"] = qt_mock
    sys.modules["aqt.utils"] = aqt_mock.utils

    import background_cpu_governor

    mod = importlib.reload(background_cpu_governor)
    yield mod, aqt_mock, qt_mock, app_mock

    for k, prev in saved_modules.items():
        if prev is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = prev


def test_hooks_and_webview_injection(loaded_governor) -> None:
    mod, aqt_mock, _, _ = loaded_governor
    assert mod.on_webview_will_set_content in aqt_mock.gui_hooks.webview_will_set_content
    assert mod.on_main_window_did_init in aqt_mock.gui_hooks.main_window_did_init

    web_content = MagicMock()
    web_content.head = ""
    web_content.js = []
    mod.on_webview_will_set_content(web_content, None)
    assert "window.__ankiCpuGovernorConfig" in web_content.head
    assert "/_addons/background_cpu_governor/web/governor.js" in web_content.js

    count_before = len(web_content.js)
    mod.on_webview_will_set_content(web_content, None)
    assert len(web_content.js) == count_before


def test_collect_webviews_dedups_and_broadcasts_resiliently(loaded_governor) -> None:
    mod, aqt_mock, _, app_mock = loaded_governor
    qt_view = MagicMock()
    qt_view.eval = None
    qt_view.page.return_value.runJavaScript = MagicMock()
    broken_view = MagicMock()
    broken_view.eval.side_effect = RuntimeError("closed")
    app_mock.allWidgets.return_value = [aqt_mock.mw.web, qt_view, broken_view, object()]

    views = mod.collect_webviews()
    assert len(views) == 5
    sent = mod.broadcast_js("1+1;")
    assert sent == 4


def test_event_filter_pauses_and_resumes_on_focus(loaded_governor) -> None:
    mod, aqt_mock, _, app_mock = loaded_governor
    mod.on_main_window_did_init()
    app_mock.installEventFilter.assert_called_once()
    # Second call should be a no-op
    assert mod.install_app_event_filter() is False

    filt = mod._event_filter_instance
    ev_deact = MagicMock()
    ev_deact.type.return_value = 122
    assert filt.eventFilter(app_mock, ev_deact) is False
    assert mod._paused is True
    assert any("setPaused(true)" in call.args[0] for call in aqt_mock.mw.web.eval.call_args_list)

    ev_act = MagicMock()
    ev_act.type.return_value = 121
    assert filt.eventFilter(app_mock, ev_act) is False
    assert mod._paused is False
    assert any("setPaused(false)" in call.args[0] for call in aqt_mock.mw.web.eval.call_args_list)


def test_set_enabled_persists_and_status_dialog_shows(loaded_governor) -> None:
    mod, aqt_mock, _, _ = loaded_governor
    mod.set_app_paused(True)
    assert mod._paused is True

    mod.set_enabled(False)
    assert mod._paused is False
    aqt_mock.mw.addonManager.writeConfig.assert_called_once()

    # When disabled, ApplicationDeactivate does not pause
    aqt_mock.mw.addonManager.getConfig.return_value = {"enabled": False}
    mod.set_app_paused(True)
    assert mod._paused is False

    with patch.dict("os.environ", {"QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu-compositing"}):
        report = mod.show_status_dialog()
    assert "Throttling: Disabled" in report
    aqt_mock.utils.showInfo.assert_called_once()
