import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import graph.export_data as export_data


class TestExportData(unittest.TestCase):
    def test_strip_html(self):
        self.assertEqual(export_data.strip_html(""), "")
        self.assertEqual(export_data.strip_html(None), "")
        self.assertEqual(export_data.strip_html("<b>hello</b>"), "hello")
        self.assertEqual(export_data.strip_html("a &nbsp; b"), "a b")
        self.assertEqual(export_data.strip_html("a &amp; b"), "a & b")
        self.assertEqual(export_data.strip_html("a &lt; b &gt; c"), "a < b > c")
        self.assertEqual(export_data.strip_html("a &quot; b &#39; c &apos; d"), "a \" b ' c ' d")
        self.assertEqual(export_data.strip_html("a :: b\nc"), "a b c")

        # Long string should be truncated to 60 chars
        long_str = "a" * 100
        self.assertEqual(len(export_data.strip_html(long_str)), 60)

    @patch('sys.stderr', new_callable=MagicMock)
    def test_progress_bar(self, mock_stdout):
        export_data.progress_bar(50, 100, "Prefix")
        mock_stdout.write.assert_called()
        mock_stdout.flush.assert_called()

    @patch('sys.stderr', new_callable=MagicMock)
    def test_progress_bar_done(self, mock_stdout):
        export_data.progress_bar(100, 100, "Prefix")
        mock_stdout.write.assert_called()

    def test_note_fingerprint(self):
        note = {'guid': '123', 'mod': 456, 'deck': 'Default'}
        fp = export_data.note_fingerprint(note)
        self.assertIsInstance(fp, str)
        self.assertEqual(len(fp), 12)

        # Test diff notes have diff fp
        note2 = {'guid': '123', 'mod': 457, 'deck': 'Default'}
        self.assertNotEqual(fp, export_data.note_fingerprint(note2))

    @patch('builtins.open')
    def test_load_cache_no_file(self, mock_open):
        mock_open.side_effect = FileNotFoundError
        self.assertIsNone(export_data.load_cache())

    @patch('builtins.open')
    @patch('json.load')
    @patch('pathlib.Path.exists')
    def test_load_cache_success(self, mock_exists, mock_json, mock_open):
        mock_exists.return_value = True
        mock_json.return_value = {"node_count": 10, "link_count": 5}
        cache = export_data.load_cache()
        self.assertEqual(cache["node_count"], 10)

    @patch('builtins.open')
    @patch('json.dump')
    def test_save_cache(self, mock_json_dump, mock_open):
        notes = [{'guid': '1', 'mod': 1, 'deck': 'A'}]
        export_data.save_cache(notes, 1, 0, 'dummy.json')
        mock_open.assert_called()
        mock_json_dump.assert_called()

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    def test_find_changed_notes(self, mock_stat, mock_exists):
        # We need to mock output_file stats
        mock_exists.return_value = True
        mock_stat.return_value.st_mtime = 1000

        cache = {'timestamp': 500, 'notes': {'1': 'fp1', '2': 'fp2', '3': 'fp3'}}

        # note 1 unchanged, note 2 modified, note 3 deleted, note 4 added
        # We mock note_fingerprint to return deterministic values
        with patch('graph.export_data.note_fingerprint') as mock_fp:

            def fp_side_effect(note):
                if note['guid'] == '1':
                    return 'fp1'
                if note['guid'] == '2':
                    return 'fp2_new'
                if note['guid'] == '4':
                    return 'fp4'

            mock_fp.side_effect = fp_side_effect

            notes = [
                {'guid': '1', 'mod': 100, 'deck': 'A'},
                {'guid': '2', 'mod': 100, 'deck': 'A'},
                {'guid': '4', 'mod': 100, 'deck': 'B'},
            ]

            # Cache matches old output_file logic (we should look into output_file timestamp vs max mod time)
            # Actually find_changed_notes does:
            # 1. max_mod = max([n.get('mod', 0) for n in notes]) if notes else 0
            # 2. if max_mod > output_time
            # Let's set max_mod > output_time
            notes[0]['mod'] = 2000

            changes = export_data.find_changed_notes(notes, cache, output_file='dummy.json')

            self.assertIn('A', changes)
            self.assertIn('B', changes)

            # Note 3 is in cache but not in notes, so its deck must be extracted from cache. Wait, does cache store decks?
            # Let's check find_changed_notes source...

    @patch('sys.stdout', new_callable=MagicMock)
    def test_find_changed_notes(self, mock_stdout):
        # Missing cache or invalid version -> None
        self.assertIsNone(export_data.find_changed_notes([], None))
        self.assertIsNone(export_data.find_changed_notes([], {'version': 3}))

        # valid version but wrong output_file -> None
        cache = {'version': 4, 'output_file': 'old.json'}
        self.assertIsNone(export_data.find_changed_notes([], cache, 'new.json'))

        cache = {
            'version': 4,
            'output_file': 'dummy.json',
            'decks': {'DeckA': {'1': 'fp1', '2': 'fp2', '3': 'fp3'}, 'DeckC': {'7': 'fp7'}},
        }

        with patch('graph.export_data.note_fingerprint') as mock_fp:

            def fp_side_effect(note):
                if note['guid'] == '1':
                    return 'fp1'
                if note['guid'] == '2':
                    return 'fp2_new'
                if note['guid'] == '4':
                    return 'fp4'
                return 'fp'

            mock_fp.side_effect = fp_side_effect

            notes = [
                {'guid': '1', 'deck': 'DeckA'},
                {'guid': '2', 'deck': 'DeckA'},
                {'guid': '4', 'deck': 'DeckB'},
            ]

            changes = export_data.find_changed_notes(notes, cache, 'dummy.json')

            self.assertIn('DeckA', changes)
            self.assertEqual(changes['DeckA']['new_guids'], set())
            self.assertEqual(changes['DeckA']['modified_guids'], {'2'})
            self.assertEqual(changes['DeckA']['removed_guids'], {'3'})

            self.assertIn('DeckB', changes)
            self.assertEqual(changes['DeckB']['new_guids'], {'4'})
            self.assertEqual(changes['DeckB']['modified_guids'], set())
            self.assertEqual(changes['DeckB']['removed_guids'], set())

            self.assertIn('DeckC', changes)
            self.assertEqual(changes['DeckC']['removed_guids'], {'7'})

    @patch('graph.export_data.progress_bar')
    def test_deck_progress(self, mock_progress_bar):
        export_data.deck_progress("Short", 0, 10, 100)
        mock_progress_bar.assert_called_with(1, 10, 'Refs: Short (100 notes)')

        long_name = "A" * 50
        export_data.deck_progress(long_name, 1, 10, 50)
        mock_progress_bar.assert_called_with(2, 10, f'Refs: {"A"*30}… (50 notes)')

    @patch('graph.export_data.ForceAtlas2')
    def test_compute_deck_layout(self, mock_fa2):
        import networkx as nx

        # Empty graph
        g_empty = nx.DiGraph()
        self.assertEqual(export_data._compute_deck_layout(g_empty, 10), {})

        # 1 node graph
        g_one = nx.DiGraph()
        g_one.add_node("A")
        self.assertEqual(export_data._compute_deck_layout(g_one, 10), {"A": (0.0, 0.0)})

        # 2+ nodes graph
        g_two = nx.DiGraph()
        g_two.add_node("A")
        g_two.add_node("B")

        mock_instance = MagicMock()
        mock_instance.forceatlas2_networkx_layout.return_value = {
            "A": (10.0, 10.0),
            "B": (20.0, 20.0),
        }
        mock_fa2.return_value = mock_instance

        layout = export_data._compute_deck_layout(g_two, 10)

        self.assertIn("A", layout)
        # Check centering (mean X = 15, mean Y = 15. A -> (-5, -5), B -> (5, 5))
        self.assertLess(layout["A"][0], 0)
        self.assertGreater(layout["B"][0], 0)
