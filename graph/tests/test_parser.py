"""
Tests for graph.parser module.

Tests field parsing, tokenization, and deck extraction.
"""

import pytest

from graph.parser import extract_deck_info, extract_fields, tokenize


class TestExtractFields:
    """Test field extraction from Anki flds string."""

    def test_extract_fields_basic(self):
        """Test basic field extraction with :: delimiter."""
        flds = "flamboyant::Marked by fancy display::etymology: Latin"
        result = extract_fields(flds)

        assert result['front'] == 'flamboyant'
        assert result['back'] == 'Marked by fancy display'
        assert result['extra'] == 'etymology: Latin'
        assert len(result['all_fields']) == 3

    def test_extract_fields_single_field(self):
        """Test extraction with only front field."""
        flds = "flamboyant"
        result = extract_fields(flds)

        assert result['front'] == 'flamboyant'
        assert result['back'] == ''
        assert result['extra'] == ''
        assert len(result['all_fields']) == 1

    def test_extract_fields_empty(self):
        """Test extraction with empty string."""
        flds = ""
        result = extract_fields(flds)

        assert result['front'] == ''
        assert result['back'] == ''
        assert result['extra'] == ''
        assert len(result['all_fields']) == 1  # At least empty string

    def test_extract_fields_other_fields(self):
        """Test that other_fields excludes front."""
        flds = "front::back::extra1::extra2"
        result = extract_fields(flds)

        assert result['front'] == 'front'
        assert result['other_fields'] == 'back::extra1::extra2'
        assert result['other_fields_text'] == 'back extra1 extra2'


class TestTokenize:
    """Test text tokenization."""

    def test_tokenize_simple(self):
        """Test simple tokenization."""
        text = "flamboyant baroque style"
        tokens = tokenize(text)

        assert 'flamboyant' in tokens
        assert 'baroque' in tokens
        assert 'style' in tokens
        assert len(tokens) == 3

    def test_tokenize_lowercase(self):
        """Test that tokens are lowercased."""
        text = "Flamboyant BAROQUE Style"
        tokens = tokenize(text)

        assert 'flamboyant' in tokens
        assert 'baroque' in tokens
        assert 'style' in tokens

    def test_tokenize_filters_short_words(self):
        """Test that words < 3 chars are filtered."""
        text = "an is the flamboyant baroque"
        tokens = tokenize(text)

        assert 'an' not in tokens
        assert 'is' not in tokens
        assert 'the' not in tokens
        assert 'flamboyant' in tokens
        assert 'baroque' in tokens

    def test_tokenize_filters_stop_words(self):
        """Test that stop words are filtered."""
        text = "the flamboyant style is very fancy"
        tokens = tokenize(text)

        assert 'the' not in tokens
        assert 'is' not in tokens
        assert 'very' not in tokens  # Should be in stop words
        assert 'flamboyant' in tokens
        assert 'style' in tokens
        assert 'fancy' in tokens

    def test_tokenize_removes_punctuation(self):
        """Test that punctuation is removed."""
        text = "flamboyant, baroque! style?"
        tokens = tokenize(text)

        assert 'flamboyant' in tokens
        assert 'baroque' in tokens
        assert 'style' in tokens
        assert len(tokens) == 3

    def test_tokenize_multi_word_field(self):
        """Test multi-word front fields."""
        text = "art history renaissance"
        tokens = tokenize(text)

        # Individual words
        assert 'art' in tokens
        assert 'history' in tokens
        assert 'renaissance' in tokens

        # Multi-word phrases (if supported)
        # This depends on implementation


class TestExtractDeckInfo:
    """Test deck information extraction."""

    def test_extract_deck_info(self):
        """Test extracting deck info from note dict."""
        note = {
            'guid': 'test123',
            'deck': 'English Vocabulary',
            'deck_id': 1001,
        }
        result = extract_deck_info(note)

        assert result['deck'] == 'English Vocabulary'
        assert result['deck_id'] == 1001
        assert result['guid'] == 'test123'

    def test_extract_deck_info_missing_deck(self):
        """Test handling missing deck field."""
        note = {'guid': 'test123'}
        result = extract_deck_info(note)

        assert result['deck'] is None or result['deck'] == ''
        assert result['deck_id'] is None


class TestGroupByDeck:
    """Test grouping notes by deck."""

    def test_group_by_deck(self):
        """Test grouping notes by deck."""
        from graph.parser import group_by_deck
        from graph.tests.fixtures import ALL_NOTES

        grouped = group_by_deck(ALL_NOTES)

        assert 'English Vocabulary' in grouped
        assert 'Calculus' in grouped
        assert 'Biology 101' in grouped

        assert len(grouped['English Vocabulary']) == 5
        assert len(grouped['Calculus']) == 3
        assert len(grouped['Biology 101']) == 2

    def test_group_by_deck_empty(self):
        """Test grouping empty list."""
        from graph.parser import group_by_deck

        grouped = group_by_deck([])
        assert grouped == {}


class TestGetFrontField:
    def test_get_front_field(self):
        from graph.parser import get_front_field

        note = {'flds': 'front\x1fback'}
        assert get_front_field(note) == 'front'


class TestGetOtherFieldsText:
    def test_get_other_fields_text(self):
        from graph.parser import get_other_fields_text

        note = {'flds': 'front\x1fback\x1fextra'}
        assert get_other_fields_text(note) == 'back extra'


class TestEmptyTokenize:
    def test_empty_tokenize(self):
        from graph.parser import tokenize

        assert tokenize("") == []

    def test_tokenize_no_stop_words(self):
        """Test tokenization without filtering stop words."""
        from graph.parser import tokenize

        text = "the flamboyant style is very fancy"
        tokens = tokenize(text, min_length=2, use_stop_words=False)
        assert 'the' in tokens
        assert 'is' in tokens
        assert 'very' in tokens
        assert 'flamboyant' in tokens
        assert 'style' in tokens
        assert 'fancy' in tokens

    def test_group_by_deck_none(self):
        """Test grouping notes where some have no deck."""
        from graph.parser import group_by_deck

        notes = [{'deck': 'Math'}, {'deck': None}, {'flds': 'no deck at all'}]
        grouped = group_by_deck(notes)
        assert 'Math' in grouped
        assert len(grouped['Math']) == 1
        assert None not in grouped
