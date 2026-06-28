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
        # The code creates edges with source=text_owner (eng002) and target=pattern_owner (eng001)
        eng002_eng001 = [e for e in edges if e['source'] == 'eng002' and e['target'] == 'eng001']
        assert len(eng002_eng001) == 1
        assert eng002_eng001[0]['type'] == 'front_in_back'

        # eng005 front "style" appears in eng002 back ("A style of...")
        eng002_eng005 = [e for e in edges if e['source'] == 'eng002' and e['target'] == 'eng005']
        assert len(eng002_eng005) == 1

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
        calc002_calc001 = [
            e for e in edges if e['source'] == 'calc002' and e['target'] == 'calc001'
        ]
        assert len(calc002_calc001) == 1
        assert calc002_calc001[0]['type'] == 'front_in_back'

    def test_find_references_biology_deck(self):
        """Test finding references within Biology deck."""
        from graph.tests.fixtures import BIOLOGY_NOTES

        edges = find_references(BIOLOGY_NOTES)

        # bio001 front "mitochondria" appears in bio002 back
        bio002_bio001 = [e for e in edges if e['source'] == 'bio002' and e['target'] == 'bio001']
        assert len(bio002_bio001) == 1

        # bio002 front "atp" appears in bio001 back ("produces ATP")
        bio001_bio002 = [e for e in edges if e['source'] == 'bio001' and e['target'] == 'bio002']
        assert len(bio001_bio002) == 1

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
            {
                'guid': 'b',
                'deck': 'Test',
                'flds': 'sine wave::oscillation pattern of sine',
                'tags': '',
            },
        ]
        edges = find_references(notes)

        b_to_a = [e for e in edges if e['source'] == 'b' and e['target'] == 'a']
        assert len(b_to_a) == 1
        assert b_to_a[0]['type'] == 'front_in_front'

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


def test_get_pool():
    from unittest.mock import MagicMock, patch

    from graph.references import _get_pool

    with patch('multiprocessing.get_context') as mock_get_context:
        mock_ctx = MagicMock()
        mock_get_context.return_value = mock_ctx
        mock_pool = MagicMock()
        mock_ctx.Pool.return_value = mock_pool

        result = _get_pool(4)
        mock_get_context.assert_called_with("fork")
        mock_ctx.Pool.assert_called_with(4)
        assert result == mock_pool


def test_edge_type():
    from graph.references import _edge_type

    assert _edge_type(True, False) == "front_in_front"
    assert _edge_type(False, False) == "front_in_back"
    assert _edge_type(True, True) == "subphrase_in_front"
    assert _edge_type(False, True) == "subphrase_in_back"


def test_normalize():
    from graph.references import _normalize

    assert _normalize("Test ") == "test"
    assert _normalize("Test (abc)") == "test (abc)"
    assert _normalize("Test [abc]") == "test [abc]"
    assert _normalize("") == ""


def test_build_automaton_empty():
    import pytest

    from graph.references import _build_automaton

    try:
        import ahocorasick
    except ImportError:
        pytest.skip("ahocorasick not available")

    automaton, guids = _build_automaton([])
    assert len(automaton) == 0
    assert len(guids) == 0


def test_build_automaton_with_data():
    import pytest

    from graph.references import _build_automaton

    try:
        import ahocorasick
    except ImportError:
        pytest.skip("ahocorasick not available")

    notes = [{'guid': '1', 'front_norm': 'hello', 'subphrases': ['hi'], 'match_front': True}]
    automaton, guids = _build_automaton(notes)
    assert len(automaton) == 2
    assert 'hello' in guids
    assert 'hi' in guids


def test_apply_df_filter_empty():
    from graph.references import _apply_df_filter

    notes = []
    _apply_df_filter(notes, {})
    assert notes == []


def test_apply_df_filter_with_data():
    from graph.references import _apply_df_filter

    notes_large = [{'front': 'front', 'subphrases_raw': []} for _ in range(50)]
    notes_large[0]['subphrases_raw'] = ['rare', 'common']

    df = {'rare': 1, 'common': 50, 'front': 1}
    _apply_df_filter(notes_large, df)
    assert 'rare' in notes_large[0]['subphrases']
    assert 'common' not in notes_large[0]['subphrases']
    assert notes_large[0]['match_front'] is True


def test_scan_chunk():
    import pytest

    from graph.references import _scan_chunk

    try:
        import ahocorasick
    except ImportError:
        pytest.skip("ahocorasick not available")

    auto = ahocorasick.Automaton()
    auto.add_word('hello', 'hello')
    auto.make_automaton()

    guid_by_pattern = {'hello': {'type': 'whole', 'guid': '1'}}
    chunk = [{'guid': '2', 'front_norm': 'hello world', 'other_norm': ''}]

    result = _scan_chunk((chunk, auto, guid_by_pattern, "deck"))
    assert len(result) == 1
    assert result[0] == ('1', '2', 'front_in_front')


def test_find_refs_bruteforce():
    from graph.references import _find_refs_bruteforce

    notes = [
        {
            'guid': '1',
            'front': 'hello',
            'front_norm': 'hello',
            'front_len': 5,
            'subphrases': [],
            'other': '',
            'other_norm': '',
            'match_front': True,
        },
        {
            'guid': '2',
            'front': 'world hello',
            'front_norm': 'hello world',
            'front_len': 11,
            'subphrases': [],
            'other': 'hello test',
            'other_norm': '',
            'match_front': True,
        },
    ]

    edges = _find_refs_bruteforce(notes, "deck")
    assert len(edges) >= 1

    def test_normalize(self):
        from graph.references import _normalize

        assert _normalize("A B C") == "a b c"
        assert _normalize("A_B-C") == "a_b-c"
        assert _normalize("A, B! C?") == "a, b! c?"
        assert _normalize("") == ""

    def test_tokenize_front(self):
        from graph.references import _tokenize_front

        tokens = _tokenize_front("hello:world:hello")
        assert set(tokens) == {"hello", "world"}

        tokens2 = _tokenize_front("hi/there")
        assert set(tokens2) == {"hi", "there"}

    def test_edge_type(self):
        from graph.references import _edge_type

        assert _edge_type(True, False) == "front_in_front"
        assert _edge_type(False, False) == "front_in_back"
        assert _edge_type(True, True) == "subphrase_in_front"
        assert _edge_type(False, True) == "subphrase_in_back"

    def test_compute_df(self):
        from graph.references import _compute_df

        note_fields = [
            {'front': 'cat', 'other': 'dog rat', 'front_len': 3, 'subphrases_raw': ['cat', 'dog']},
            {
                'front': 'bat',
                'other': 'cat cat dog',
                'front_len': 3,
                'subphrases_raw': ['cat', 'bat'],
            },
        ]
        df = _compute_df(note_fields)
        assert df['cat'] == 2
        assert df['dog'] == 2
        assert df['bat'] == 1

    def test_prepare_note_fields(self):
        from graph.references import _prepare_note_fields

        notes = [{'guid': '1', 'flds': 'Cat\x1fDog'}]
        res = _prepare_note_fields(notes, "Deck")
        assert len(res) == 1
        assert res[0]['guid'] == '1'
        assert res[0]['front'] == 'cat'
        assert res[0]['other'] == 'dog'

    def test_apply_df_filter(self):
        from graph.references import _apply_df_filter

        notes = [
            {'guid': str(i), 'subphrases_raw': ['common', 'rare'], 'front': 'xyz'}
            for i in range(100)
        ]
        notes[0]['front'] = 'common'
        notes[1]['front'] = 'rare'
        df = {'common': 60, 'rare': 1, 'xyz': 1}
        _apply_df_filter(notes, df)
        assert notes[0]['subphrases'] == ['rare']
