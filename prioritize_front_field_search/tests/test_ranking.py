import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search import score_front_match, extract_terms

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
    assert score_front_match("<ruby>強</ruby>がる", "強がる") == 4
    
    # Should strip contents of rt, rp, style, script tags
    assert score_front_match("<h3><ruby>連<rt>つ</rt></ruby>れ</h3>", "連れ") == 4
    assert score_front_match("<ruby>連<rp>(</rp><rt>つ</rt><rp>)</rp></ruby>れ", "連れ") == 4
    assert score_front_match("<style>.red { color: red; }</style>連れ", "連れ") == 4
    assert score_front_match("<script>alert(1);</script>連れ", "連れ") == 4
    
    # Should strip Anki sound tags
    assert score_front_match("連れ[sound:test.mp3]", "連れ") == 4

def test_extract_terms():
    assert extract_terms("apple banana") == ["apple", "banana"]
    assert extract_terms('apple "banana split" deck:default') == ["apple", "banana split"]
    assert extract_terms('apple OR banana') == ["apple", "banana"]
    assert extract_terms('Front:*tiff*') == ["tiff"] # Should remove wildcards
    assert extract_terms('Front:tiff') == ["tiff"]
