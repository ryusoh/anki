"""
Tests for graph.references module.

Tests whole-front-field reference finding within decks (no cross-deck references).
"""

import pytest
from graph.references import find_references, find_references_for_deck


class TestFindReferences:
    """Test reference finding across all decks."""

    def test_find_references_english_deck(self):
        """Test finding references within English deck."""
        from graph.tests.fixtures import ENGLISH_NOTES

        edges = find_references(ENGLISH_NOTES)

        # eng001 front "flamboyant" appears in eng002 back
        eng001_eng002 = [e for e in edges if e['source'] == 'eng001' and e['target'] == 'eng002']
        assert len(eng001_eng002) == 1
        assert eng001_eng002[0]['type'] == 'front_in_back'

        # eng005 front "style" appears in eng002 back ("A style of...")
        eng005_eng002 = [e for e in edges if e['source'] == 'eng005' and e['target'] == 'eng002']
        assert len(eng005_eng002) == 1

    def test_find_references_no_cross_deck(self):
        """Test that cross-deck references are NOT created."""
        from graph.tests.fixtures import ALL_NOTES

        edges = find_references(ALL_NOTES)

        english_guids = {'eng001', 'eng002', 'eng003', 'eng004', 'eng005'}
        calculus_guids = {'calc001', 'calc002', 'calc003'}
        biology_guids = {'bio001', 'bio002'}

        for edge in edges:
            source = edge['source']
            target = edge['target']

            if source in english_guids:
                assert target in english_guids, f"Cross-deck edge: {source} -> {target}"
            elif source in calculus_guids:
                assert target in calculus_guids, f"Cross-deck edge: {source} -> {target}"
            elif source in biology_guids:
                assert target in biology_guids, f"Cross-deck edge: {source} -> {target}"

    def test_find_references_calculus_deck(self):
        """Test finding references within Calculus deck."""
        from graph.tests.fixtures import CALCULUS_NOTES

        edges = find_references(CALCULUS_NOTES)

        # calc001 front "derivative" appears in calc002 back
        calc001_calc002 = [e for e in edges if e['source'] == 'calc001' and e['target'] == 'calc002']
        assert len(calc001_calc002) == 1
        assert calc001_calc002[0]['type'] == 'front_in_back'

    def test_find_references_biology_deck(self):
        """Test finding references within Biology deck."""
        from graph.tests.fixtures import BIOLOGY_NOTES

        edges = find_references(BIOLOGY_NOTES)

        # bio001 front "mitochondria" appears in bio002 back
        bio001_bio002 = [e for e in edges if e['source'] == 'bio001' and e['target'] == 'bio002']
        assert len(bio001_bio002) == 1

        # bio002 front "atp" appears in bio001 back ("produces ATP")
        bio002_bio001 = [e for e in edges if e['source'] == 'bio002' and e['target'] == 'bio001']
        assert len(bio002_bio001) == 1

    def test_find_references_empty(self):
        """Test finding references in empty list."""
        edges = find_references([])
        assert edges == []

    def test_find_references_single_note(self):
        """Test finding references with single note (no edges possible)."""
        from graph.tests.fixtures import ENGLISH_NOTES

        edges = find_references([ENGLISH_NOTES[0]])
        assert edges == []

    def test_edge_has_correct_type(self):
        """Test that edges have correct type field."""
        from graph.tests.fixtures import ENGLISH_NOTES

        edges = find_references(ENGLISH_NOTES)

        for edge in edges:
            assert 'type' in edge
            assert edge['type'] in ['front_in_front', 'front_in_back']
            assert 'source' in edge
            assert 'target' in edge

    def test_no_self_references(self):
        """Test that no card references itself."""
        from graph.tests.fixtures import ALL_NOTES

        edges = find_references(ALL_NOTES)

        for edge in edges:
            assert edge['source'] != edge['target']

    def test_front_in_front_detection(self):
        """Test detection when one card's front appears in another card's front."""
        notes = [
            {'guid': 'a', 'deck': 'Test', 'flds': 'sine::trig function', 'tags': ''},
            {'guid': 'b', 'deck': 'Test', 'flds': 'sine wave::oscillation pattern of sine', 'tags': ''},
        ]
        edges = find_references(notes)

        a_to_b = [e for e in edges if e['source'] == 'a' and e['target'] == 'b']
        assert len(a_to_b) == 1
        assert a_to_b[0]['type'] == 'front_in_front'

    def test_short_fronts_ignored(self):
        """Test that very short front fields (< 2 chars) don't create edges."""
        notes = [
            {'guid': 'a', 'deck': 'Test', 'flds': 'x::variable', 'tags': ''},
            {'guid': 'b', 'deck': 'Test', 'flds': 'f(x)::function of x', 'tags': ''},
        ]
        edges = find_references(notes)
        a_edges = [e for e in edges if e['source'] == 'a']
        assert len(a_edges) == 0


class TestFindReferencesForDeck:
    """Test per-deck reference finding."""

    def test_find_references_for_deck(self):
        """Test finding references for specific deck."""
        from graph.tests.fixtures import ALL_NOTES

        edges = find_references_for_deck(ALL_NOTES, 'English Vocabulary')

        english_guids = {'eng001', 'eng002', 'eng003', 'eng004', 'eng005'}

        for edge in edges:
            assert edge['source'] in english_guids
            assert edge['target'] in english_guids

    def test_find_references_for_deck_nonexistent(self):
        """Test finding references for nonexistent deck."""
        from graph.tests.fixtures import ALL_NOTES

        edges = find_references_for_deck(ALL_NOTES, 'Nonexistent Deck')
        assert edges == []


class TestReferenceWeights:
    """Test edge weight calculation."""

    def test_edge_has_weight(self):
        """Test that edges have weight field."""
        from graph.tests.fixtures import ENGLISH_NOTES

        edges = find_references(ENGLISH_NOTES)

        for edge in edges:
            assert 'weight' in edge
            assert isinstance(edge['weight'], (int, float))
            assert edge['weight'] > 0

    def test_front_in_front_weighs_more(self):
        """Test that front-in-front edges weigh more than front-in-back."""
        from graph.references import EDGE_WEIGHTS
        assert EDGE_WEIGHTS['front_in_front'] > EDGE_WEIGHTS['front_in_back']
