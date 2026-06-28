import sys
import types
from unittest.mock import MagicMock


class MockModule(types.ModuleType):
    def __getattr__(self, name):
        return MagicMock()


for mod in [
    'aqt',
    'aqt.browser',
    'aqt.qt',
    'aqt.editor',
    'aqt.webview',
    'aqt.utils',
    'aqt.gui_hooks',
    'aqt.main',
    'aqt.deckbrowser',
    'anki',
    'anki.hooks',
    'anki.utils',
    'anki.lang',
    'anki.stats',
]:
    sys.modules[mod] = MockModule(mod)

sys.modules['aqt.deckbrowser'].DeckBrowser = MagicMock()
sys.modules['aqt.deckbrowser'].MockDeckBrowser = MagicMock()

import importlib.util

spec = importlib.util.spec_from_file_location("debug_module", "enhance_main_window/debug.py")
debug_module = importlib.util.module_from_spec(spec)
sys.modules["debug_module"] = debug_module
spec.loader.exec_module(debug_module)

from unittest.mock import patch

import pytest


def test_start_end_debug(capsys):
    debug_module.shouldDebug = False

    debug_module.startDebug()
    assert debug_module.shouldDebug is True
    out, err = capsys.readouterr()
    assert "Debug started" in out

    debug_module.endDebug()
    assert debug_module.shouldDebug is False
    out, err = capsys.readouterr()
    assert "Debug ended" in out


def test_debug_function_when_disabled(capsys):
    debug_module.shouldDebug = False
    debug_module.indentation = 0
    debug_module.debug("test text")
    out, err = capsys.readouterr()
    assert out == ""
    assert debug_module.indentation == 0


def test_debug_function_force_and_indentation(capsys):
    debug_module.shouldDebug = False
    debug_module.indentation = 0

    debug_module.debug("hello\nworld", force=True)
    out, err = capsys.readouterr()
    assert "hello\n world" in out

    debug_module.debug("indent me", indentToAdd=2, force=True)
    out, err = capsys.readouterr()
    assert "{<indent me" in out
    assert debug_module.indentation == 2

    debug_module.debug("outdent me", indentToAdd=-2, force=True)
    out, err = capsys.readouterr()
    assert "outdent me" in out
    assert ">}" in out
    assert debug_module.indentation == 0


def test_debug_inside_this_method():
    # Test with mayDebug=False
    debug_module.mayDebug = False

    @debug_module.debugInsideThisMethod
    def my_func():
        return 42

    assert my_func() == 42

    # Test with mayDebug=True
    debug_module.mayDebug = True
    debug_module.nbInsideThis = 0

    @debug_module.debugInsideThisMethod
    def my_func2():
        return 43

    with (
        patch.object(debug_module, "startDebug") as mock_start,
        patch.object(debug_module, "endDebug") as mock_end,
    ):
        assert my_func2() == 43
        mock_start.assert_called_once()
        mock_end.assert_called_once()

    debug_module.mayDebug = False


def test_debug_fun(capsys):
    debug_module.mayDebug = True
    debug_module.shouldDebug = True

    @debug_module.debugFun
    def my_add(a, b, c=1):
        return a + b + c

    res = my_add(2, 3, c=4)
    assert res == 9
    out, err = capsys.readouterr()
    assert "my_add(2, 3, c=4)" in out
    assert "returns 9" in out

    debug_module.mayDebug = False


def test_debug_init(capsys):
    debug_module.mayDebug = True
    debug_module.shouldDebug = True

    class MyClass:
        @debug_module.debugInit
        def __init__(self, x, y=2):
            self.val = x + y

        def __str__(self):
            return f"MyClass({self.val})"

    obj = MyClass(3, y=5)
    assert obj.val == 8
    out, err = capsys.readouterr()
    assert "__init__(y=5)" in out
    assert "returns MyClass(8)" in out

    debug_module.mayDebug = False


def test_debug_only_this_method(capsys):
    debug_module.mayDebug = True
    debug_module.shouldDebug = False

    @debug_module.debugOnlyThisMethod
    def my_sub(a, b):
        return a - b

    assert my_sub(5, 2) == 3
    out, err = capsys.readouterr()
    assert "my_sub(5, 2)" in out

    debug_module.mayDebug = False


def test_debug_only_this_init(capsys):
    debug_module.mayDebug = True
    debug_module.shouldDebug = False

    class MyClass2:
        @debug_module.debugOnlyThisInit
        def __init__(self, x):
            self.x = x

        def __str__(self):
            return "MC2"

    obj = MyClass2(10)
    assert obj.x == 10
    out, err = capsys.readouterr()
    assert "MC2" in out

    debug_module.mayDebug = False


def test_assert_equal(capsys):
    assert debug_module.assertEqual(1, 1) is True

    assert debug_module.assertEqual(1, 2) is False
    out, err = capsys.readouterr()
    assert "which is distinct from expected" in out


class DummyGen1:
    def firstDifference(self, other):
        return ("diff1", "diff2")


class DummyGen2:
    def firstDifference(self, other):
        return None


class DummyGen3:
    def firstDifference(self, other):
        return "not a tuple or None"


def test_assert_equal_first_difference(capsys):
    g1 = DummyGen1()

    debug_module.assertEqual(g1, DummyGen1())
    out, err = capsys.readouterr()
    assert "The first difference is" in out

    # Code bug: 'elif isinstance(pair, None):' raises TypeError in python3.
    with pytest.raises(TypeError):
        debug_module.assertEqual(DummyGen2(), DummyGen2())

    # Same goes for DummyGen3
    with pytest.raises(TypeError):
        debug_module.assertEqual(DummyGen3(), DummyGen3())

    debug_module.assertEqual(g1, 1)
    out, err = capsys.readouterr()
    assert "Only the first is a Gen" in out

    debug_module.assertEqual(1, g1)
    out, err = capsys.readouterr()
    assert "Only the second is a Gen" in out


def test_assert_type(capsys):
    assert debug_module.assertType(1, int) is True
    assert debug_module.assertType(1, [str, int]) is True

    assert debug_module.assertType(1, str) is False
    out, err = capsys.readouterr()
    assert "which is not a subtype of" in out


def test_exception_inverse():
    ex = debug_module.ExceptionInverse("line1\nline2\nline3")
    assert str(ex) == "Exception: \nline3\nline2\nline1"


def test_debug_init_args(capsys):
    debug_module.mayDebug = True
    debug_module.shouldDebug = True

    class MyClass3:
        @debug_module.debugInit
        def __init__(self, a, b):
            pass

    MyClass3("arg1", "arg2")
    out, err = capsys.readouterr()
    assert "__init__(arg2)" in out

    debug_module.mayDebug = False


def test_debug_fun_multiple_args(capsys):
    debug_module.mayDebug = True
    debug_module.shouldDebug = True

    @debug_module.debugFun
    def my_multi(a, b, c):
        pass

    my_multi(1, 2, 3)
    out, err = capsys.readouterr()
    assert "my_multi(1, 2, 3)" in out

    debug_module.mayDebug = False


def test_debug_inside_this_method_fallback():
    @debug_module.debugInsideThisMethod
    def my_func():
        return 42

    debug_module.mayDebug = False
    assert my_func() == 42


def test_debug_fun_uncalled():
    debug_module.mayDebug = False

    @debug_module.debugFun
    def my_multi2(a, b, c):
        return a + b

    assert my_multi2(1, 2, 3) == 3


def test_debug_init_uncalled():
    debug_module.mayDebug = False

    class MyClass4:
        @debug_module.debugInit
        def __init__(self, a, b):
            self.a = a

    assert MyClass4(1, 2).a == 1


class DummyGen4:
    def firstDifference(self, other):
        return [1, 2]  # Some random type


def test_assert_equal_first_diff_else():
    g4 = DummyGen4()
    with pytest.raises(TypeError):
        debug_module.assertEqual(g4, DummyGen4())
