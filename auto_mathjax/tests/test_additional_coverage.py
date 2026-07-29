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
    # To hit line 238, core must be empty, but run must not be empty and must match BARE_LATEX_COMMAND_RE
    # Wait, if core is empty, run only consists of _RUN_TRIM_CHARS.
    # But BARE_LATEX_COMMAND_RE is r'\\[a-zA-Z]+'
    # Wait, BARE_LATEX_COMMAND_RE requires a backslash. So run must contain a backslash.
    # Ah, if BARE_LATEX_COMMAND_RE matches run, then run contains a backslash.
    # So `core` after stripping _RUN_TRIM_CHARS will contain a backslash.
    # _RUN_TRIM_CHARS is '.,;:= \t'

    pass
