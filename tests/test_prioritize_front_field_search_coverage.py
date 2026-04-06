import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prioritize_front_field_search.search import score_front_match, extract_terms, build_tier1_query, sort_tier1_by_score

def test_score_front_match_empty_term():
    # Covers line 24
    assert score_front_match("some text", "") == 0

def test_extract_terms_front_quoted():
    # Covers line 69 (term.startswith('"') and term.endswith('"'))
    assert extract_terms('Front:"hello"') == ["hello"]

def test_build_tier1_empty_query():
    # Covers line 95
    assert build_tier1_query("") == ""

def test_build_tier1_negated_normal_terms():
    # Covers line 115
    # Needs a normal term to not return early empty string
    assert build_tier1_query("-hello world") == "-hello Front:*world*"

def test_build_tier1_with_wildcard():
    # Covers line 124
    assert build_tier1_query("test*") == "Front:test*"

def test_sort_tier1_empty_ids_or_terms():
    # Covers line 140
    assert sort_tier1_by_score([], {}, ["term"]) == []
    assert sort_tier1_by_score([1, 2], {}, []) == [1, 2]
    assert sort_tier1_by_score([], {}, []) == []
