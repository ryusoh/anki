import re

import pytest
from bs4 import BeautifulSoup

import auto_mathjax
from auto_mathjax import (
    _inject_macro_defs,
    _looks_like_bare_latex,
    _looks_like_math_content,
    _track_math_state,
    _unwrap_mathjax_from_pre,
    _wrap_embedded_latex,
)


def test_looks_like_math_content():
    assert _looks_like_math_content("<div>") is False
    assert _looks_like_math_content("你好") is False
    assert _looks_like_math_content("abc") is True


def test_track_math_state():
    assert _track_math_state(None, "\\[ math \\]") is None
    assert _track_math_state(None, "\\[ math") == '['
    assert _track_math_state('(', "\\) math") is None
    assert _track_math_state(None, "\\( math") == '('
    assert _track_math_state('(', "\\]") == '('
    assert _track_math_state(None, "\\]") is None


def test_wrap_embedded_latex():
    assert _wrap_embedded_latex("\\sum ") == "\\sum "
    assert _wrap_embedded_latex("\\LaTeX ") == "\\LaTeX "
    assert _wrap_embedded_latex("some \\LaTeX=") == "some \\LaTeX="


def test_inject_macro_defs(monkeypatch):
    monkeypatch.setattr(auto_mathjax, "CUSTOM_MACROS", {})
    assert _inject_macro_defs("some html") == "some html"
    monkeypatch.setattr(auto_mathjax, "CUSTOM_MACROS", {"cmd": "body"})
    assert _inject_macro_defs("some html \\cmd") == "\\(\\def\\cmd{body}\\)some html \\cmd"
    assert _inject_macro_defs("some html \\def\\cmd") == "some html \\def\\cmd"


def test_unwrap_math_pre_blocks():
    html = "<pre></pre><pre> </pre>"
    assert _unwrap_mathjax_from_pre(html) == ""
    html2 = "<pre>\\( math \\)</pre><pre> </pre>"
    assert _unwrap_mathjax_from_pre(html2) == "\\( math \\)"
    html3 = "<pre>text</pre><pre></pre>"
    assert _unwrap_mathjax_from_pre(html3) == "<pre>text</pre>"


def test_wrap_embedded_latex_empty_core(monkeypatch):
    import auto_mathjax

    monkeypatch.setattr(auto_mathjax, '_RUN_TRIM_CHARS', '\\to ')
    assert _wrap_embedded_latex(' \\to ') == ' \\to '
