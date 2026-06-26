import sys
from unittest.mock import MagicMock, patch

_mock_aqt = MagicMock()


class _FakeStatsClass:
    def __init__(self, *a, **kw):
        pass

    def refresh(self, *a, **kw):
        pass


_mock_stats = MagicMock()
_mock_stats.DeckStats = _FakeStatsClass
_mock_stats.NewDeckStats = _FakeStatsClass

sys.modules["aqt"] = _mock_aqt
sys.modules["aqt.gui_hooks"] = MagicMock()
sys.modules["aqt.qt"] = MagicMock()
sys.modules["aqt.stats"] = _mock_stats
sys.modules["aqt.utils"] = MagicMock()
sys.modules["aqt.webview"] = MagicMock()

from stats_page_customizer import (
    CUSTOM_STATS_30D_JSON,
    _attach_on_load,
    _build_custom_stats_payload,
    _clear_custom_stats_dialog,
    _on_collection_did_load,
    _on_main_window_did_init,
    _on_profile_did_open,
    _read_custom_stats_payload,
    _refresh_custom_stats_cache,
    _render_custom_stats_html,
    mw,
)


def test_read_custom_stats_payload_missing(monkeypatch, tmp_path):
    target = tmp_path / "nope.json"
    monkeypatch.setattr("stats_page_customizer.CUSTOM_STATS_30D_JSON", target)
    assert _read_custom_stats_payload() is None


def test_read_custom_stats_payload_error(monkeypatch, tmp_path):
    target = tmp_path / "bad.json"
    target.write_text("{bad", encoding="utf-8")
    monkeypatch.setattr("stats_page_customizer.CUSTOM_STATS_30D_JSON", target)
    assert _read_custom_stats_payload() is None


def test_read_custom_stats_payload_success(monkeypatch, tmp_path):
    target = tmp_path / "good.json"
    target.write_text('{"futureDue": []}', encoding="utf-8")
    monkeypatch.setattr("stats_page_customizer.CUSTOM_STATS_30D_JSON", target)
    assert _read_custom_stats_payload() == {"futureDue": []}


@patch("stats_page_customizer._read_custom_stats_payload")
def test_build_custom_stats_payload_cache_hit(mock_read):
    mock_read.return_value = {"cached": True}
    assert _build_custom_stats_payload() == {"cached": True}


@patch("stats_page_customizer._read_custom_stats_payload")
@patch("stats_page_customizer._gather_future_due")
@patch("stats_page_customizer._write_custom_stats_payload")
def test_build_custom_stats_payload_cache_miss(mock_write, mock_gather, mock_read):
    mock_read.return_value = None
    mock_gather.return_value = [{"day": 0}]
    assert _build_custom_stats_payload() == {"futureDue": [{"day": 0}]}
    mock_write.assert_called_once()


@patch("stats_page_customizer._read_custom_stats_template")
def test_render_custom_stats_html_no_template(mock_read):
    mock_read.return_value = None
    assert _render_custom_stats_html() is None


@patch("stats_page_customizer._read_custom_stats_template")
@patch("stats_page_customizer._build_custom_stats_payload")
@patch("stats_page_customizer._inject_payload_into_html")
def test_render_custom_stats_html_success(mock_inject, mock_build, mock_read):
    mock_read.return_value = "<html>"
    mock_build.return_value = {"data": 1}
    mock_inject.return_value = "<html>injected</html>"
    assert _render_custom_stats_html() == "<html>injected</html>"


def test_clear_custom_stats_dialog():
    import stats_page_customizer

    stats_page_customizer._custom_stats_dialog = "something"
    _clear_custom_stats_dialog()
    assert stats_page_customizer._custom_stats_dialog is None


@patch("stats_page_customizer.QAction")
@patch("stats_page_customizer.qconnect")
def test_on_main_window_did_init_success(mock_qconnect, mock_qaction):
    mock_action = MagicMock()
    mock_qaction.return_value = mock_action

    import stats_page_customizer

    stats_page_customizer._custom_stats_action = None

    mock_window = MagicMock()
    mock_window.form = MagicMock()
    mock_window.form.menuTools = MagicMock()

    _on_main_window_did_init(mock_window)

    mock_window.form.menuTools.addAction.assert_called_once_with(mock_action)
    assert stats_page_customizer._custom_stats_action == mock_action


def test_on_main_window_did_init_no_qt():
    import stats_page_customizer

    old_qaction = stats_page_customizer.QAction
    stats_page_customizer.QAction = None
    _on_main_window_did_init(MagicMock())
    stats_page_customizer.QAction = old_qaction


def test_on_main_window_did_init_no_window():
    import stats_page_customizer

    old_mw = stats_page_customizer.mw
    stats_page_customizer.mw = None
    _on_main_window_did_init(None)
    stats_page_customizer.mw = old_mw


def test_on_main_window_did_init_no_menuTools():
    import stats_page_customizer

    mock_window = MagicMock()
    mock_window.form = MagicMock()
    del mock_window.form.menuTools
    _on_main_window_did_init(mock_window)


@patch("stats_page_customizer._gather_future_due")
@patch("stats_page_customizer._write_custom_stats_payload")
def test_refresh_custom_stats_cache_success(mock_write, mock_gather):
    import stats_page_customizer

    old_mw = stats_page_customizer.mw
    stats_page_customizer.mw = MagicMock()
    stats_page_customizer.mw.col = MagicMock()

    _refresh_custom_stats_cache()
    mock_gather.assert_called_once()
    mock_write.assert_called_once()

    stats_page_customizer.mw = old_mw


def test_refresh_custom_stats_cache_no_col():
    import stats_page_customizer

    old_mw = stats_page_customizer.mw
    stats_page_customizer.mw = MagicMock()
    del stats_page_customizer.mw.col

    _refresh_custom_stats_cache()

    stats_page_customizer.mw = old_mw


@patch("stats_page_customizer._refresh_custom_stats_cache")
def test_on_profile_did_open(mock_refresh):
    _on_profile_did_open()
    mock_refresh.assert_called_once()


@patch("stats_page_customizer._refresh_custom_stats_cache")
def test_on_collection_did_load(mock_refresh):
    _on_collection_did_load()
    mock_refresh.assert_called_once()


@patch("stats_page_customizer._schedule_js_eval")
def test_attach_on_load_already_connected(mock_schedule):
    class WebMock:
        pass

    web = WebMock()
    web._stats_customizer_connected = True
    _attach_on_load(web)
    mock_schedule.assert_not_called()


def test_attach_on_load_no_loadFinished():
    class WebMock:
        pass

    web = WebMock()
    _attach_on_load(web)
    assert getattr(web, "_stats_customizer_connected", False) is True


@patch("stats_page_customizer.QTimer")
def test_schedule_js_eval_with_timer(mock_timer):
    import stats_page_customizer

    web = MagicMock()
    stats_page_customizer._schedule_js_eval(web)
    assert mock_timer.singleShot.call_count == 5


def test_schedule_js_eval_no_timer():
    import stats_page_customizer

    old_qtimer = stats_page_customizer.QTimer
    stats_page_customizer.QTimer = None
    web = MagicMock()
    stats_page_customizer._schedule_js_eval(web)
    web.eval.assert_called_once_with(stats_page_customizer.JS_CODE)
    stats_page_customizer.QTimer = old_qtimer


@patch("webbrowser.open")
def test_show_custom_stats_dialog(mock_open):
    import stats_page_customizer

    stats_page_customizer._show_custom_stats_dialog()
    mock_open.assert_called_once_with("https://anki.lyeutsaon.com")


def test_load_injected_js_missing(monkeypatch, tmp_path):
    target = tmp_path / "nope.js"
    monkeypatch.setattr("stats_page_customizer.JS_INJECT_PATH", target)
    from stats_page_customizer import _load_injected_js

    assert _load_injected_js() == ""


def test_load_injected_js_error(monkeypatch, tmp_path):
    target = tmp_path / "bad.js"
    # make unreadable by mocking read_text
    monkeypatch.setattr("stats_page_customizer.JS_INJECT_PATH", target)
    from unittest.mock import patch

    with patch("pathlib.Path.read_text", side_effect=Exception("mock err")):
        from stats_page_customizer import _load_injected_js

        assert _load_injected_js() == ""


def test_read_custom_stats_template_missing(monkeypatch, tmp_path):
    target = tmp_path / "nope.html"
    monkeypatch.setattr("stats_page_customizer.CUSTOM_STATS_HTML", target)
    from stats_page_customizer import _read_custom_stats_template

    assert _read_custom_stats_template() is None


def test_inject_payload_into_html_no_body():
    from stats_page_customizer import _inject_payload_into_html

    html = "<html>hello</html>"
    res = _inject_payload_into_html(html, {"a": 1})
    assert "<script>" in res
    assert '{"a": 1}' in res
    assert "</body>" not in res
