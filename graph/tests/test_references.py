import unittest
from unittest.mock import MagicMock, patch

import graph.references as references


class TestReferences(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(references._normalize("A B C"), "a b c")
        self.assertEqual(references._normalize("A_B-C"), "a_b-c")
        self.assertEqual(references._normalize("A, B! C?"), "a, b! c?")
        self.assertEqual(references._normalize(""), "")

    def test_tokenize_front(self):
        tokens = references._tokenize_front("hello:world:hello")
        self.assertEqual(set(tokens), {"hello", "world"})

        tokens2 = references._tokenize_front("hi/there")
        self.assertEqual(set(tokens2), {"hi", "there"})

    def test_edge_type(self):
        self.assertEqual(references._edge_type(True, False), "front_in_front")
        self.assertEqual(references._edge_type(False, False), "front_in_back")
        self.assertEqual(references._edge_type(True, True), "subphrase_in_front")
        self.assertEqual(references._edge_type(False, True), "subphrase_in_back")

    def test_compute_df(self):
        note_fields = [
            {'front': 'cat', 'other': 'dog rat', 'front_len': 3, 'subphrases_raw': ['cat', 'dog']},
            {
                'front': 'bat',
                'other': 'cat cat dog',
                'front_len': 3,
                'subphrases_raw': ['cat', 'bat'],
            },
        ]
        df = references._compute_df(note_fields)
        self.assertEqual(df['cat'], 2)
        self.assertEqual(df['dog'], 2)

        self.assertEqual(df['bat'], 1)

    def test_prepare_note_fields(self):
        notes = [{'guid': '1', 'flds': 'Cat\x1fDog'}]
        res = references._prepare_note_fields(notes, "Deck")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['guid'], '1')
        self.assertEqual(res[0]['front'], 'cat')
        self.assertEqual(res[0]['other'], 'dog')

    def test_apply_df_filter(self):

        df = {'cat': 100, 'bat': 1, 'dog': 10}  # if total N=1, wait df filter uses max_df.
        # _apply_df_filter logic:
        # N = len(note_fields)
        # min_idf_freq = min(500, max(2, int(N * 0.05)))
        # Wait, if N=1, max is 2. So min_idf_freq = 2.
        # So df > 2 are filtered.
        # Let's mock a larger list
        notes = [
            {'guid': str(i), 'subphrases_raw': ['common', 'rare'], 'front': 'xyz'}
            for i in range(100)
        ]
        notes[0]['front'] = 'common'
        notes[1]['front'] = 'rare'
        df = {'common': 60, 'rare': 1, 'xyz': 1}
        # N=100. min_idf_freq = max(2, 5) = 5.
        references._apply_df_filter(notes, df)
        self.assertEqual(notes[0]['subphrases'], ['rare'])
