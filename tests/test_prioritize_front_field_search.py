import pytest
from prioritize_front_field_search.search import extract_terms, _process_query_part

def test_extract_terms_process_query_part():
    # Covers line 28, 54, 73
    assert _process_query_part("OR") == ""
    assert _process_query_part("-some_word") == ""
    assert _process_query_part("-") == "-"
    assert _process_query_part('"hello"') == "hello"
    assert _process_query_part('"he') == '"he'
    assert _process_query_part('hel*lo') == "hello"

def test_extract_terms():
    assert extract_terms('front:"hello"') == ["hello"]
    assert extract_terms('-front:"hello"') == ["hello"]
    assert extract_terms('back:"hello"') == []
    assert extract_terms('front:hel*lo') == ["hello"]
    assert extract_terms('front:hello') == ["hello"]
    assert extract_terms('OR') == []
    assert extract_terms('') == []

    assert extract_terms('front:"some*"') == ["some"]

from prioritize_front_field_search.search import score_front_match

def test_score_front_match():
    assert score_front_match("", "test") == 0
    assert score_front_match("test", "") == 0
    assert score_front_match("test", "test") == 4
    assert score_front_match("this is a test string", "test") == 3
    assert score_front_match("testosterone", "test") == 2
    assert score_front_match("this is testosterone", "test") == 1
    assert score_front_match("hello world", "test") == 0

    # Check strip_html
    assert score_front_match("<style>hidden</style>test", "test") == 4
    assert score_front_match("<div>test</div>", "test") == 4
    assert score_front_match("te&nbsp;st", "te st") == 4
    assert score_front_match("[sound:test.mp3]test", "test") == 4

def test_extract_terms_mixed():
    assert extract_terms('front:"hello world" back:ignore me -front:"ignored_dash" OR something "quoted_thing"') == ['hello world', 'me', 'ignored_dash', 'something', 'quoted_thing']
