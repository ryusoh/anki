import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from search import _extract_term_from_field, _process_query_part, extract_terms, score_front_match


def test_score_front_match_empty_term():
    assert score_front_match("some text", "") == 0
    assert score_front_match("some text", "   ") == 0


def test_extract_term_from_field_unknown():
    assert _extract_term_from_field("back", "term") == ""


def test_extract_term_from_field_front():
    assert _extract_term_from_field("front", "term") == "term"
    assert _extract_term_from_field("-front", "term") == "term"
    assert _extract_term_from_field("front", '"term with space"') == "term with space"
    assert _extract_term_from_field("front", "*wildcard*") == "wildcard"


def test_process_query_part():
    assert _process_query_part("OR") == ""
    assert _process_query_part("-") == "-"
    assert _process_query_part("-exclude") == ""
    assert _process_query_part('"quoted"') == "quoted"
    assert _process_query_part("*wildcard*") == "wildcard"


def test_extract_terms_empty():
    assert extract_terms("") == []
    assert extract_terms("   ") == []


def test_extract_terms_complex():
    query = 'apple OR banana -orange "grape juice" Front:"*mango*" Back:pear'
    terms = extract_terms(query)
    assert terms == ["apple", "banana", "grape juice", "mango"]
