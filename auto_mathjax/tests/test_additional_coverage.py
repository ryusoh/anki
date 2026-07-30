import re
from unittest.mock import MagicMock

from auto_mathjax import BARE_LATEX_COMMAND_RE, _wrap_embedded_latex


def test_bare_command_wrap():
    text = "\\displaystyle O(\\log N)"
    assert _wrap_embedded_latex(text) == "\\displaystyle O(\\log N)"
    text = "O(\\log N)"
    assert _wrap_embedded_latex(text) == "O(\\log N)"
    text = "\\log"
    assert _wrap_embedded_latex(text) == "\\log"
    text = "\\log "
    assert _wrap_embedded_latex(text) == "\\log "

    text = "\\frac"
    assert _wrap_embedded_latex(text) == "\\frac"

    text = "\\frac "
    assert _wrap_embedded_latex(text) == "\\frac "


def test_bare_command_wrap_trim_only():
    text = "\\ "
    assert _wrap_embedded_latex(text) == "\\ "
    text = "\\"
    assert _wrap_embedded_latex(text) == "\\"


def test_bare_command_wrap_trim_only_2():

    pass
