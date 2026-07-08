import pytest

from highlight_search_matches.core import extract_search_terms, highlight_text


def test_extract_search_terms():
    assert extract_search_terms("") == []
    assert extract_search_terms("term") == ["term"]
    assert frozenset(extract_search_terms("term1 term2")) == frozenset(["term1", "term2"])
    assert frozenset(extract_search_terms('"exact match" term2')) == frozenset(
        ["exact", "match", "term2"]
    )
    assert extract_search_terms('field:value term') == ["term"]
    assert extract_search_terms("-neg term") == ["term"]
    assert extract_search_terms("(term)") == ["term"]


def test_highlight_text_empty():
    assert highlight_text("", ["world"]) == ""
    assert highlight_text("hello", []) == "hello"


def test_highlight_text():
    assert (
        highlight_text("hello world", ["world"])
        == "hello <span class=\"search-highlight\">world</span>"
    )
    assert highlight_text("hello world", []) == "hello world"
    assert (
        highlight_text("hello WORLD", ["world"])
        == "hello <span class=\"search-highlight\">WORLD</span>"
    )
    assert (
        highlight_text("<div>hello</div>", ["hello"])
        == "<div><span class=\"search-highlight\">hello</span></div>"
    )
    assert (
        highlight_text("<div class=\"hello\">hello</div>", ["hello"])
        == "<div class=\"hello\"><span class=\"search-highlight\">hello</span></div>"
    )


def test_extract_search_terms_empty_brackets():
    assert extract_search_terms("()") == []
