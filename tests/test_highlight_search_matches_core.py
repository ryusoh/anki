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


def test_init_py_coverage():
    import sys
    from unittest.mock import mock_open, patch

    # Save original modules
    orig_aqt = sys.modules.get("aqt")

    # Remove aqt to test the ImportError path
    if "aqt" in sys.modules:
        del sys.modules["aqt"]

    import importlib

    import highlight_search_matches

    importlib.reload(highlight_search_matches)

    # Run the `log` function
    with patch("builtins.open", mock_open()) as mocked_file:
        highlight_search_matches.log("test_message")
        mocked_file.assert_called()

    # Put aqt back
    if orig_aqt:
        sys.modules["aqt"] = orig_aqt

    # Re-import to test the normal path
    importlib.reload(highlight_search_matches)

    # Test when mw is present but no config
    with patch("aqt.mw") as mock_mw:
        mock_mw.addonManager.getConfig.return_value = None
        with patch("builtins.open", mock_open()) as mocked_file:
            highlight_search_matches.log("test_message")
            # should not write
            mocked_file.assert_not_called()

    # Test when mw is present and debug is True
    with patch("aqt.mw") as mock_mw:
        mock_mw.addonManager.getConfig.return_value = {"debug": True}
        with patch("builtins.open", mock_open()) as mocked_file:
            highlight_search_matches.log("test_message")
            mocked_file.assert_called()

    # Test Exception in getConfig
    with patch("aqt.mw") as mock_mw, patch("logging.getLogger") as mock_logger:
        mock_mw.addonManager.getConfig.side_effect = Exception("err")
        highlight_search_matches.log("test_message")
        mock_logger.return_value.debug.assert_called()

    # Test Exception in file writing
    if "aqt" in sys.modules:
        del sys.modules["aqt"]
    importlib.reload(highlight_search_matches)
    with (
        patch("builtins.open", side_effect=Exception("write err")),
        patch("logging.getLogger") as mock_logger,
    ):
        highlight_search_matches.log("test_message")
        mock_logger.return_value.debug.assert_called()

    if orig_aqt:
        sys.modules["aqt"] = orig_aqt
