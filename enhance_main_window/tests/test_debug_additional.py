import pytest

from enhance_main_window.debug import ExceptionInverse, assertEqual


def test_assertEqual_gen_first_difference_not_tuple(capsys):
    class GenMock:
        def firstDifference(self, other):
            return "string_difference"

    with pytest.raises(TypeError):
        assertEqual(GenMock(), GenMock())


def test_assertEqual_gen_first_difference_none(capsys):
    class GenMock:
        def firstDifference(self, other):
            return None

    with pytest.raises(TypeError):
        assertEqual(GenMock(), GenMock())


def test_assertEqual_only_first_gen(capsys):
    class GenMock:
        def firstDifference(self, other):
            return None

    class NotGenMock:
        pass

    assert not assertEqual(GenMock(), NotGenMock())
    out = capsys.readouterr().out
    assert "Only the second is a Gen" not in out
    assert "Only the first is a Gen" in out


def test_assertEqual_only_second_gen(capsys):
    class GenMock:
        def firstDifference(self, other):
            return None

    class NotGenMock:
        pass

    assert not assertEqual(NotGenMock(), GenMock())
    assert "Only the second is a Gen" in capsys.readouterr().out
