import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search import build_tier1_query, extract_terms

def test_build_tier1_simple():
    assert build_tier1_query("apple") == "Front:*apple*"

def test_build_tier1_multiple():
    assert build_tier1_query("apple banana") == "Front:*apple* Front:*banana*"

def test_build_tier1_special():
    assert build_tier1_query('apple deck:"my deck" is:due') == 'Front:*apple* deck:"my deck" is:due'

def test_build_tier1_quotes():
    assert build_tier1_query('"apple banana" is:new') == '"Front:*apple banana*" is:new'

def test_build_tier1_or():
    assert build_tier1_query("apple OR banana") == "Front:*apple* OR Front:*banana*"

def test_build_tier1_complex():
    assert build_tier1_query('apple OR "banana split" -tag:hard') == 'Front:*apple* OR "Front:*banana split*" -tag:hard'

def test_build_tier1_no_normal():
    assert build_tier1_query('deck:default is:new') == ""


class TestExtractTerms:
    """Tests for extract_terms function including regex edge cases."""

    def test_simple_terms(self):
        assert extract_terms("apple banana") == ["apple", "banana"]

    def test_quoted_phrase(self):
        assert extract_terms('"hello world"') == ["hello world"]

    def test_mixed_quoted_unquoted(self):
        assert extract_terms('apple "banana split" cherry') == ["apple", "banana split", "cherry"]

    def test_or_operator_excluded(self):
        assert extract_terms("apple OR banana") == ["apple", "banana"]

    def test_field_prefix_front(self):
        assert extract_terms('Front:tiff') == ["tiff"]
        assert extract_terms('Front:*tiff*') == ["tiff"]

    def test_negated_terms_excluded(self):
        assert extract_terms("apple -banana") == ["apple"]

    def test_empty_query(self):
        assert extract_terms("") == []

    def test_only_or_operators(self):
        assert extract_terms("OR OR OR") == []

    def test_quotes_with_apostrophes(self):
        assert extract_terms('"don\'t stop"') == ["don't stop"]

    def test_quotes_with_escaped_chars(self):
        # Escaped quotes inside quoted string
        assert extract_terms(r'"say \"hello\""') == [r'say \"hello\"']

    def test_special_characters_in_terms(self):
        terms = extract_terms("c++ python3.9 test-case")
        assert "c++" in terms
        assert "python3.9" in terms
        assert "test-case" in terms

    def test_wildcards_removed(self):
        assert extract_terms("app*le") == ["apple"]
        # Note: wildcards inside quotes are preserved for regular terms
        # (only Front: field values have wildcards removed)
        # Quotes are stripped but wildcards remain
        assert extract_terms('"*banana*"') == ["*banana*"]

    def test_field_case_insensitive(self):
        assert extract_terms('front:tiff') == ["tiff"]
        assert extract_terms('FRONT:tiff') == ["tiff"]


class TestRegexNoCatastrophicBacktracking:
    """
    Tests to verify the regex doesn't suffer from catastrophic backtracking.
    These are patterns that would trigger ReDoS in the old regex.
    """

    def test_long_unquoted_string_no_hang(self):
        """Long string without spaces/quotes should not cause backtracking."""
        long_term = "a" * 1000
        result = extract_terms(long_term)
        assert result == [long_term]

    def test_many_consecutive_spaces(self):
        """Many spaces should be handled efficiently."""
        query = "apple" + " " * 100 + "banana"
        result = extract_terms(query)
        assert result == ["apple", "banana"]

    def test_alternating_quote_patterns(self):
        """Alternating quote patterns that could cause backtracking."""
        # This pattern: "..." "..." "..." ... could cause exponential backtracking
        query = ' '.join([f'"term{i}"' for i in range(100)])
        result = extract_terms(query)
        assert len(result) == 100
        assert result[0] == "term0"
        assert result[-1] == "term99"

    def test_malformed_quotes_handled(self):
        """Unclosed quotes should not cause hangs."""
        query = '"unclosed quote apple banana'
        # Should not hang, should return something reasonable
        result = extract_terms(query)
        assert result  # Should return at least one term

    def test_many_special_chars(self):
        """Many special characters should not cause issues."""
        query = "a!@#$%^&*()b c{}[]|\\;:,.<>?/~`d"
        result = extract_terms(query)
        assert len(result) >= 1

    def test_nested_like_patterns(self):
        """Patterns that look like they could nest (common ReDoS trigger)."""
        # Pattern like: "a" "b" "c" ... without proper handling
        query = '"a" "b" "c" "d" "e" "f" "g" "h" "i" "j"'
        result = extract_terms(query)
        assert len(result) == 10

    def test_backslash_sequences(self):
        """Multiple backslashes should not cause backtracking."""
        query = r'term1 \\ term2 \\\\ term3'
        result = extract_terms(query)
        assert "term1" in result
        assert "term2" in result
        assert "term3" in result

    def test_performance_no_degradation(self):
        """
        Performance test: ensure regex scales linearly.
        If this test takes > 1 second, the regex may have ReDoS issues.
        """
        import time
        # Build increasingly large queries
        for size in [10, 50, 100, 200]:
            query = ' '.join([f'"term{i} with some extra text"' for i in range(size)])
            start = time.time()
            result = extract_terms(query)
            elapsed = time.time() - start
            # Each iteration should complete in under 0.1 seconds
            assert elapsed < 0.5, f"extract_terms took {elapsed}s for {size} terms"
            assert len(result) == size
