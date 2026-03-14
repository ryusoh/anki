import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search import score_front_match, extract_terms, sort_tier1_by_score

@pytest.mark.parametrize("text, term, expected_score", [
    ("tiff", "tiff", 4),           # Exact match
    ("TIFF", "tiff", 4),           # Exact match (case-insensitive)
    ("blow up a tiff", "tiff", 3), # Word match
    ("a tiff is here", "tiff", 3), # Word match
    ("stiff", "tiff", 2),          # Substring match (single word)
    ("mastiff", "tiff", 2),        # Substring match (single word)
    ("plaintiff", "tiff", 2),      # Substring match (single word)
    ("working stiff", "tiff", 1),  # Substring match (multiple words)
    ("very stiff indeed", "tiff", 1), # Substring match (multiple words)
    ("apple", "tiff", 0),          # No match
])
def test_score_front_match(text, term, expected_score):
    assert score_front_match(text, term) == expected_score

def test_score_front_match_html():
    # Should strip HTML tags before matching
    assert score_front_match("<b>tiff</b>", "tiff") == 4
    assert score_front_match("<i>blow up a tiff</i>", "tiff") == 3
    assert score_front_match("<u>stiff</u>", "tiff") == 2
    assert score_front_match("<div class='foo'>working stiff</div>", "tiff") == 1

def test_extract_terms():
    assert extract_terms("apple banana") == ["apple", "banana"]
    assert extract_terms('apple "banana split" deck:default') == ["apple", "banana split"]
    assert extract_terms('apple OR banana') == ["apple", "banana"]
    assert extract_terms('Front:*tiff*') == ["tiff"] # Should remove wildcards
    assert extract_terms('Front:tiff') == ["tiff"]

def test_sort_tier1_by_score():
    ids = [1, 2, 3, 4]
    note_data = {
        1: "working stiff", # score 1
        2: "tiff",          # score 4
        3: "stiff",          # score 2
        4: "a tiff"          # score 3
    }
    terms = ["tiff"]
    sorted_ids = sort_tier1_by_score(ids, note_data, terms)
    assert sorted_ids == [2, 4, 3, 1]

def test_sort_tier1_stable():
    # Items with same score should preserve original order
    ids = [1, 2, 3]
    note_data = {
        1: "tiff one", # score 3
        2: "tiff two", # score 3
        3: "tiff"      # score 4
    }
    terms = ["tiff"]
    sorted_ids = sort_tier1_by_score(ids, note_data, terms)
    assert sorted_ids == [3, 1, 2] # 3 is highest, 1 and 2 same score so 1 then 2
