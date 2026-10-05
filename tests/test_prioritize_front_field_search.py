import pytest

from prioritize_front_field_search.search import _process_query_part, extract_terms


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
    assert extract_terms(
        'front:"hello world" back:ignore me -front:"ignored_dash" OR something "quoted_thing"'
    ) == ['hello world', 'me', 'ignored_dash', 'something', 'quoted_thing']


import sys
from unittest.mock import MagicMock

from prioritize_front_field_search import _fetch_front_fields, init, on_browser_did_search


def test_fetch_front_fields():
    col = MagicMock()
    col.db.all.return_value = [(1, 100, "Front1\x1fBack1"), (2, 100, "Front2\x1fBack2")]
    col.models.get.return_value = {
        'flds': [{'name': 'Front', 'ord': 0}, {'name': 'Back', 'ord': 1}]
    }
    result = _fetch_front_fields(col, [1, 2], True)
    assert result == {1: "Front1", 2: "Front2"}
    col.db.all.assert_called_with("select id, mid, flds from notes where id in (1,2)")
    result = _fetch_front_fields(col, [1, 2], False)
    assert result == {1: "Front1", 2: "Front2"}


def test_fetch_front_fields_chunking():
    col = MagicMock()
    col.db.all.return_value = []
    ids = list(range(1, 1001))
    _fetch_front_fields(col, ids, True)
    assert col.db.all.call_count == 2
    args, _ = col.db.all.call_args_list[0]
    assert args[0].count(",") == 899 + 2


def test_on_browser_did_search_no_query():
    ctx = MagicMock()
    ctx.search = ""
    on_browser_did_search(ctx)


def test_on_browser_did_search_no_terms():
    ctx = MagicMock()
    ctx.search = "deck:Default"
    ctx.ids = [1, 2]
    on_browser_did_search(ctx)


def test_on_browser_did_search_no_ids():
    ctx = MagicMock()
    ctx.search = "term"
    ctx.ids = []
    on_browser_did_search(ctx)


def test_on_browser_did_search_exception(capsys):
    ctx = MagicMock()
    ctx.search = "term"
    ctx.ids = [1, 2]
    type(ctx.browser).col = property(lambda self: int("not_an_int"))
    on_browser_did_search(ctx)
    captured = capsys.readouterr()
    assert "[prioritize_front_field_search] API Error executing two-tiered sort:" in captured.out


def test_fetch_front_fields_missing_idx():
    col = MagicMock()
    col.db.all.return_value = [(1, 100, "Front1")]
    col.models.get.return_value = {'flds': [{'name': 'NotFront', 'ord': 0}]}
    result = _fetch_front_fields(col, [1], True)
    assert result == {1: "Front1"}


def test_fetch_front_fields_idx_out_of_bounds():
    col = MagicMock()
    col.db.all.return_value = [(1, 100, "Front1")]
    col.models.get.return_value = {'flds': [{'name': 'Front', 'ord': 5}]}
    result = _fetch_front_fields(col, [1], True)
    assert result == {}


def test_on_browser_did_search_valid():
    ctx = MagicMock()
    ctx.search = "match"
    ctx.ids = [1, 2, 3]
    ctx.browser.table.is_notes_mode.return_value = True
    ctx.browser.col.db.all.return_value = [
        (1, 100, "match exactly\x1fBack"),
        (2, 100, "partialmatch\x1fBack"),
        (3, 100, "nomatch\x1fBack"),
    ]
    ctx.browser.col.models.get.return_value = {
        'flds': [{'name': 'Front', 'ord': 0}, {'name': 'Back', 'ord': 1}]
    }
    on_browser_did_search(ctx)
    assert ctx.ids == [1, 2, 3]


def test_init_import_error_log(monkeypatch, caplog):
    monkeypatch.setitem(sys.modules, "aqt.gui_hooks", None)
    import prioritize_front_field_search

    # re-init to trigger the catch
    prioritize_front_field_search.init()
    assert "Failed to import browser_did_search hook" in caplog.text


def test_fetch_front_fields_missing_model():
    col = MagicMock()
    col.db.all.return_value = [(1, 100, "Front1")]
    col.models.get.return_value = None
    result = _fetch_front_fields(col, [1], True)
    assert result == {1: "Front1"}


def test_on_browser_did_search_valid_reversed():
    ctx = MagicMock()
    ctx.search = "match"
    ctx.ids = [2, 1, 3]
    ctx.browser.table.is_notes_mode.return_value = True
    ctx.browser.col.db.all.return_value = [
        (1, 100, "match exactly\x1fBack"),
        (2, 100, "match \x1fBack"),
        (3, 100, "nomatch\x1fBack"),
    ]
    ctx.browser.col.models.get.return_value = {
        'flds': [{'name': 'Front', 'ord': 0}, {'name': 'Back', 'ord': 1}]
    }
    on_browser_did_search(ctx)
    assert ctx.ids == [2, 1, 3]


def test_on_browser_did_search_tier1_empty():
    ctx = MagicMock()
    ctx.search = "match"
    ctx.ids = [1, 2]
    ctx.browser.table.is_notes_mode.return_value = True
    ctx.browser.col.db.all.return_value = [
        (1, 100, "nothing\x1fBack"),
        (2, 100, "nothing\x1fBack"),
    ]
    ctx.browser.col.models.get.return_value = {
        'flds': [{'name': 'Front', 'ord': 0}, {'name': 'Back', 'ord': 1}]
    }
    on_browser_did_search(ctx)
    assert ctx.ids == [1, 2]
