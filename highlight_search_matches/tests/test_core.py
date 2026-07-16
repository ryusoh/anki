import pytest

from highlight_search_matches.core import (
    extract_search_terms,
    highlight_text,
    note_has_real_match,
)


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


def test_highlight_text_ignores_html_entities():
    # Searching "BSP" must not match the "bsp" inside a &nbsp; entity
    assert highlight_text("word1&nbsp;word2", ["BSP"]) == "word1&nbsp;word2"
    # Named entity, exact-case term
    assert highlight_text("a&amp;b", ["amp"]) == "a&amp;b"
    # Decimal and hex numeric entities
    assert highlight_text("x&#8203;y", ["8203"]) == "x&#8203;y"
    assert highlight_text("x&#x200B;y", ["200B"]) == "x&#x200B;y"


def test_highlight_text_still_matches_next_to_entities():
    assert (
        highlight_text("BSP&nbsp;tree", ["BSP"])
        == '<span class="search-highlight">BSP</span>&nbsp;tree'
    )
    # A bare ampersand that is not an entity stays matchable
    assert highlight_text("AT&T BSP", ["BSP"]) == 'AT&T <span class="search-highlight">BSP</span>'


def test_note_has_real_match_entity_only_is_noise():
    # The reported bug: a field whose only "BSP" is inside &nbsp;
    assert note_has_real_match(["word1&nbsp;word2"], ["BSP"]) is False
    assert note_has_real_match(["x&#8203;y"], ["8203"]) is False


def test_note_has_real_match_visible_text():
    assert note_has_real_match(["BSP&nbsp;tree"], ["BSP"]) is True
    # Case-insensitive, like Anki search
    assert note_has_real_match(["the bsp algorithm"], ["BSP"]) is True
    # Any field of the note counts
    assert note_has_real_match(["front&nbsp;", "back has BSP"], ["BSP"]) is True
    # Any term counts (conservative: only entity/tag-only notes are dropped)
    assert note_has_real_match(["only tree here"], ["BSP", "tree"]) is True


def test_note_has_real_match_ignores_tag_internals():
    # "bsp" appearing only inside a tag attribute is not a visible match
    assert note_has_real_match(['<div class="bsp">x</div>'], ["BSP"]) is False


def test_note_has_real_match_decoded_entity_text_is_visible():
    # &amp; decodes to "&", so searching "a&b" is a real visible match
    assert note_has_real_match(["a&amp;b"], ["a&b"]) is True


def test_note_has_real_match_keeps_media_filenames():
    # Anki's search strips tags but preserves media filenames, so a search
    # for "bsp" legitimately matches <img src="bsp.jpg"> — don't drop it.
    assert note_has_real_match(['<img src="bsp.jpg">'], ["bsp"]) is True
    assert note_has_real_match(["[sound:bsp.mp3]"], ["bsp"]) is True
