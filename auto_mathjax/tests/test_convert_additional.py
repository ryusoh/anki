import pytest
from auto_mathjax import _looks_like_math_content, _track_math_state, _looks_like_bare_latex, _inject_macro_defs, _unwrap_mathjax_from_pre, _wrap_embedded_latex
import auto_mathjax
from bs4 import BeautifulSoup

def test_looks_like_math_content():
    assert _looks_like_math_content("<div>") is False
    assert _looks_like_math_content("你好") is False
    assert _looks_like_math_content("abc") is True

def test_track_math_state():
    assert _track_math_state(None, "\\[ math \\]") == None
    assert _track_math_state(None, "\\[ math") == '['
    assert _track_math_state('(', "\\) math") == None
    assert _track_math_state(None, "\\( math") == '('
    assert _track_math_state('(', "\\]") == '('
    assert _track_math_state(None, "\\]") == None

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
