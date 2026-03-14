import pytest
from highlight_search_matches.core import extract_search_terms, highlight_text

def test_extract_search_terms_basic():
    assert extract_search_terms("apple") == ["apple"]

def test_extract_search_terms_multiple():
    assert extract_search_terms("apple banana") == ["apple", "banana"]

def test_extract_search_terms_ignore_fields():
    assert extract_search_terms("deck:Default apple") == ["apple"]
    assert extract_search_terms("apple is:due") == ["apple"]
    assert extract_search_terms("note:Basic apple") == ["apple"]

def test_extract_search_terms_ignore_negation():
    assert extract_search_terms("apple -banana") == ["apple"]
    assert extract_search_terms("-deck:Default apple") == ["apple"]

def test_extract_search_terms_strip_quotes():
    assert extract_search_terms('"apple"') == ["apple"]
    assert extract_search_terms("'banana'") == ["banana"]
    assert extract_search_terms('"apple pie"') == ["apple", "pie"]

def test_extract_search_terms_wildcards():
    assert extract_search_terms("app*") == ["app*"]

def test_extract_search_terms_empty():
    assert extract_search_terms("") == []
    assert extract_search_terms("   ") == []
    assert extract_search_terms("deck:Default") == []

def test_highlight_text_basic():
    text = "The quick brown fox"
    terms = ["quick", "fox"]
    highlighted = highlight_text(text, terms)
    assert 'class="search-highlight">quick</span>' in highlighted
    assert 'class="search-highlight">fox</span>' in highlighted
    assert "The " in highlighted

def test_highlight_text_case_insensitive():
    text = "Apple and banana"
    terms = ["apple", "BANANA"]
    highlighted = highlight_text(text, terms)
    assert 'class="search-highlight">Apple</span>' in highlighted
    assert 'class="search-highlight">banana</span>' in highlighted

def test_highlight_text_html_safe():
    # It shouldn't highlight terms inside HTML tags like <span class="apple">
    text = 'An <span class="apple">apple</span> pie'
    terms = ["apple"]
    highlighted = highlight_text(text, terms)
    # The inner text 'apple' should be highlighted, but the class name shouldn't change
    assert 'class="apple"' in highlighted
    assert '><span class="search-highlight">apple</span><' in highlighted

def test_highlight_text_no_matches():
    text = "The quick brown fox"
    terms = ["apple"]
    assert highlight_text(text, terms) == text

def test_highlight_text_empty():
    assert highlight_text("", ["apple"]) == ""
    assert highlight_text("apple", []) == "apple"
