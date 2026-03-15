"""
Tests for graph.references module.

Tests reference finding within decks (no cross-deck references).
"""

import pytest
from graph.references import find_references, find_references_for_deck


class TestFindReferences:
    """Test reference finding across all decks."""
    
    def test_find_references_english_deck(self):
        """Test finding references within English deck."""
        from graph.tests.fixtures import ENGLISH_NOTES
        
        edges = find_references(ENGLISH_NOTES)
        
        # eng002 (baroque) references eng001 (flamboyant)
        eng001_eng002 = [e for e in edges if e['source'] == 'eng001' and e['target'] == 'eng002']
        assert len(eng001_eng002) > 0
        assert eng001_eng002[0]['word'] == 'flamboyant'
        
        # eng002 (baroque) references eng005 (style)
        eng005_eng002 = [e for e in edges if e['source'] == 'eng005' and e['target'] == 'eng002']
        assert len(eng005_eng002) > 0
        assert eng005_eng002[0]['word'] == 'style'
    
    def test_find_references_no_cross_deck(self):
        """Test that cross-deck references are NOT created."""
        from graph.tests.fixtures import ALL_NOTES
        
        edges = find_references(ALL_NOTES)
        
        # Should NOT have edges between English and Calculus notes
        english_guids = {'eng001', 'eng002', 'eng003', 'eng004', 'eng005'}
        calculus_guids = {'calc001', 'calc002', 'calc003'}
        biology_guids = {'bio001', 'bio002'}
        
        for edge in edges:
            source = edge['source']
            target = edge['target']
            
            # Both source and target should be from same deck
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
        
        # calc002 (integral) references calc001 (derivative)
        calc001_calc002 = [e for e in edges if e['source'] == 'calc001' and e['target'] == 'calc002']
        assert len(calc001_calc002) > 0
        assert calc001_calc002[0]['word'] == 'derivative'
    
    def test_find_references_biology_deck(self):
        """Test finding references within Biology deck."""
        from graph.tests.fixtures import BIOLOGY_NOTES
        
        edges = find_references(BIOLOGY_NOTES)
        
        # bio002 (ATP) references bio001 (mitochondria)
        bio001_bio002 = [e for e in edges if e['source'] == 'bio001' and e['target'] == 'bio002']
        assert len(bio001_bio002) > 0
        assert bio001_bio002[0]['word'] == 'mitochondria'
    
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
            assert edge['type'] in ['field_reference', 'front_reference']
            assert 'source' in edge
            assert 'target' in edge
            assert 'word' in edge


class TestFindReferencesForDeck:
    """Test per-deck reference finding."""
    
    def test_find_references_for_deck(self):
        """Test finding references for specific deck."""
        from graph.tests.fixtures import ALL_NOTES
        
        edges = find_references_for_deck(ALL_NOTES, 'English Vocabulary')
        
        # All edges should be within English deck
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
        from graph.references import find_references
        
        edges = find_references(ENGLISH_NOTES)
        
        for edge in edges:
            assert 'weight' in edge
            assert isinstance(edge['weight'], (int, float))
            assert edge['weight'] > 0
