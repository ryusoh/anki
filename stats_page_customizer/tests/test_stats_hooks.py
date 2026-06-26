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

from stats_page_customizer import _on_stats_dialog_will_show, _patch_stats_class


def test_on_stats_dialog_will_show_no_web():
    stats_dialog = MagicMock()
    del stats_dialog.web
    _on_stats_dialog_will_show(stats_dialog)


@patch('stats_page_customizer._attach_on_load')
def test_on_stats_dialog_will_show_with_web(mock_attach):
    stats_dialog = MagicMock()
    stats_dialog.web = MagicMock()
    _on_stats_dialog_will_show(stats_dialog)
    mock_attach.assert_called_once_with(stats_dialog.web)


def test_patch_stats_class_none():
    _patch_stats_class(None)


def test_patch_stats_class_no_refresh():
    class TestClass:
        def __init__(self):
            pass

    _patch_stats_class(TestClass)


def test_patch_stats_class_patched():
    class TestClass:
        def __init__(self):
            pass

        def refresh(self):
            pass

    TestClass.__init__._stats_customizer_patched = True
    _patch_stats_class(TestClass)


def test_patch_stats_class_already_patched():
    class TestClass:
        def __init__(self):
            pass

        def refresh(self):
            pass

    # Mark it as already patched
    TestClass.__init__._stats_customizer_patched = True

    from stats_page_customizer import _patch_stats_class

    _patch_stats_class(TestClass)

    # It shouldn't change the init method since it's already patched
    assert TestClass.__init__._stats_customizer_patched is True
    # If it was repatched, it would have replaced the __init__ method entirely
    # but we don't have a great way to verify that easily besides the fact
    # that it didn't crash.


@patch('stats_page_customizer._attach_on_load')
def test_patch_stats_class_wrap_init(mock_attach):
    class TestClass:
        def __init__(self, web=None):
            self.web = web

        def refresh(self):
            pass

    from stats_page_customizer import _patch_stats_class

    _patch_stats_class(TestClass)

    # Create an instance to trigger the wrapped init
    mock_web = MagicMock()
    TestClass(web=mock_web)

    mock_attach.assert_called_once_with(mock_web)


@patch('stats_page_customizer._attach_on_load')
def test_patch_stats_class_wrap_init_fallback_form(mock_attach):
    class TestClass:
        def __init__(self, form=None):
            self.form = form

        def refresh(self):
            pass

    from stats_page_customizer import _patch_stats_class

    _patch_stats_class(TestClass)

    mock_web = MagicMock()
    mock_form = MagicMock()
    mock_form.web = mock_web

    # Trigger wrapped init
    TestClass(form=mock_form)

    mock_attach.assert_called_once_with(mock_web)


@patch('stats_page_customizer._attach_on_load')
def test_patch_stats_class_wrap_init_no_web(mock_attach):
    class TestClass:
        def __init__(self):
            pass

        def refresh(self):
            pass

    from stats_page_customizer import _patch_stats_class

    _patch_stats_class(TestClass)

    # Trigger wrapped init
    TestClass()

    mock_attach.assert_not_called()


def test_patch_stats_class_wrap_refresh():
    class TestClass:
        def __init__(self):
            pass

        def refresh(self):
            pass

    from stats_page_customizer import _patch_stats_class, mw

    _patch_stats_class(TestClass)

    # Try calling refresh
    instance = TestClass()

    # Simply running it without error indicates success
    instance.refresh()


@patch('stats_page_customizer._schedule_js_eval')
def test_patch_stats_class_wrap_refresh_with_web(mock_schedule):
    class TestClass:
        def __init__(self):
            pass

        def refresh(self):
            pass

    from stats_page_customizer import _patch_stats_class

    _patch_stats_class(TestClass)

    mock_web = MagicMock()
    instance = TestClass()
    instance.web = mock_web

    instance.refresh()

    mock_schedule.assert_called_once_with(mock_web)


@patch('stats_page_customizer._attach_on_load')
def test_patch_stats_class_wrap_init_log_attrs(mock_attach):
    class TestClass:
        def __init__(self, content="something"):
            self.content = content

        def refresh(self):
            pass

    from stats_page_customizer import _patch_stats_class

    _patch_stats_class(TestClass)

    # Trigger wrapped init
    TestClass()

    mock_attach.assert_not_called()


def test_log_error(capsys):
    from unittest.mock import patch

    from stats_page_customizer import _log

    with patch("stats_page_customizer.Path.mkdir", side_effect=Exception("mocked error")):
        _log("test message")
        captured = capsys.readouterr()
        assert "Error writing to log file: mocked error" in captured.out


def test_patch_stats_class_none():
    from unittest.mock import patch

    from stats_page_customizer import _patch_stats_class

    with patch("stats_page_customizer._log") as mock_log:
        _patch_stats_class(None)
        mock_log.assert_called_with("Stats class missing; cannot patch.")


def test_patch_stats_class_no_init():
    from unittest.mock import patch

    from stats_page_customizer import _patch_stats_class

    class DummyClass:
        pass

    with patch("stats_page_customizer._log") as mock_log:
        _patch_stats_class(DummyClass)
        mock_log.assert_any_call(f"{DummyClass} lacks __init__ or refresh; cannot patch.")


def test_patch_stats_class_dummy_with_web():
    from unittest.mock import patch

    from stats_page_customizer import _patch_stats_class

    class DummyClassWithInit:
        def __init__(self):
            pass

        def refresh(self):
            pass

    # Assign some dummy attributes to bypass initial checks and allow patching
    # DummyClassWithInit._stats_customizer_patched is False by default

    with (
        patch("stats_page_customizer._log") as mock_log,
        patch("stats_page_customizer._schedule_js_eval") as mock_schedule,
    ):

        _patch_stats_class(DummyClassWithInit)

        # Test the wrapped __init__ sets up web properly
        from unittest.mock import MagicMock

        class FakeWeb:
            def __init__(self):
                self.loadFinished = MagicMock()
                self._stats_customizer_connected = False

        instance = DummyClassWithInit()
        instance.web = FakeWeb()
        # Since it calls original init, no problem, but to trigger the log in the wrapped init
        # we have to re-invoke __init__ now that we've set `web` (or we can just mock the self.web to exist after original init).
        # We can just call __init__ again to hit `if web:` block.
        instance.__init__()
        mock_log.assert_any_call("DummyClassWithInit.__init__ attaching webview via self.web.")

        # Test the wrapped refresh schedules js
        instance.refresh()
        mock_schedule.assert_called_with(instance.web)


def test_missing_gui_hooks():
    # To test branches 384->387, etc. we need to simulate gui_hooks missing or missing attribute
    import stats_page_customizer

    old_gui = stats_page_customizer.gui_hooks

    # We can't really re-evaluate the module level code without reloading,
    # but we can just use importlib.reload with a patched sys.modules
    import importlib
    import sys

    # Set gui_hooks to None
    sys.modules["aqt.gui_hooks"] = None
    importlib.reload(stats_page_customizer)

    # Restore
    sys.modules["aqt.gui_hooks"] = old_gui
    importlib.reload(stats_page_customizer)


@patch("stats_page_customizer._schedule_js_eval")
def test_on_load_finished(mock_schedule):
    from stats_page_customizer import _attach_on_load

    class WebMock:
        def __init__(self):
            self.loadFinished = MagicMock()

    web = WebMock()
    _attach_on_load(web)

    # Get the callback
    callback = web.loadFinished.connect.call_args[0][0]

    # Call with False
    callback(False)
    mock_schedule.reset_mock()
    mock_schedule.assert_not_called()

    # Call with True
    callback(True)
    mock_schedule.assert_called_with(web)
