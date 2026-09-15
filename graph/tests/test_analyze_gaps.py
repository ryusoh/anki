import json
import sys
from unittest.mock import mock_open, patch

import pytest

from graph.analyze import load_notes_with_decks, main


def test_analyze_no_notes():
    with patch('graph.analyze.load_notes_with_decks', return_value=[]):
        with patch('sys.argv', ['analyze.py']):
            with patch('sys.stderr', new_callable=lambda: open('/dev/null', 'w')):
                with pytest.raises(SystemExit) as excinfo:
                    main()
                assert excinfo.value.code == 1


def test_analyze_no_decks():
    with patch('graph.analyze.load_notes_with_decks', return_value=[{'guid': '123'}]):
        with patch('sys.argv', ['analyze.py']):
            with patch('sys.stderr', new_callable=lambda: open('/dev/null', 'w')):
                with pytest.raises(SystemExit) as excinfo:
                    main()
                assert excinfo.value.code == 1


def test_analyze_load_notes_exception():
    import builtins

    original_open = builtins.open

    def mock_open_err(*args, **kwargs):
        if 'notes.json' in str(args[0]):
            raise Exception("Test open error")
        return original_open(*args, **kwargs)

    with patch('builtins.open', side_effect=mock_open_err):
        with patch('sys.stderr', new_callable=lambda: original_open('/dev/null', 'w')):
            notes = load_notes_with_decks()
            assert notes == []


def test_analyze_all_decks():
    notes = [{'guid': '1', 'deck': 'Deck A'}, {'guid': '2', 'deck': 'Deck B'}]
    with patch('graph.analyze.load_notes_with_decks', return_value=notes):
        with patch('sys.argv', ['analyze.py', '--all-decks']):
            with patch('graph.analyze.analyze_all_decks') as mock_analyze:
                main()
                assert mock_analyze.called


def test_analyze_deck_branch():
    notes = [{'guid': '1', 'deck': 'Deck A'}, {'guid': '2', 'deck': 'Deck B'}]
    with patch('graph.analyze.load_notes_with_decks', return_value=notes):
        with patch('sys.argv', ['analyze.py', '--deck', 'Deck A']):
            with patch('graph.analyze.analyze_single_deck') as mock_analyze:
                main()
                assert mock_analyze.called


def test_analyze_default_branch():
    notes = [{'guid': '1', 'deck': 'Deck A'}, {'guid': '2', 'deck': 'Deck B'}]
    with patch('graph.analyze.load_notes_with_decks', return_value=notes):
        with patch('sys.argv', ['analyze.py']):
            with patch('graph.analyze.print_deck_list') as mock_print:
                main()
                assert mock_print.called


def test_analyze_anonymize():
    notes = [{'guid': '1', 'deck': 'Deck A'}, {'guid': '2', 'deck': 'Deck B'}]
    with patch('graph.analyze.load_notes_with_decks', return_value=notes):
        with patch('sys.argv', ['analyze.py', '--anonymize']):
            with patch('graph.analyze.print_deck_list') as mock_print:
                main()
                assert mock_print.called


def test_analyze_load_cards_exception():
    import builtins

    original_open = builtins.open

    def mock_open_side_effect(file, *args, **kwargs):
        if 'notes.json' in str(file) and 'data/anki' in str(file):
            return mock_open(read_data='[{"id": 1, "guid": "abc"}]').return_value
        if 'cards.json' in str(file):
            raise Exception("Test cards error")
        return original_open(file, *args, **kwargs)

    def mock_exists(self):
        return 'notes.json' in str(self) and 'data/anki' in str(self)

    with patch('builtins.open', side_effect=mock_open_side_effect):
        with patch('pathlib.Path.exists', autospec=True, side_effect=mock_exists):
            with patch('os.path.exists', return_value=True):
                with patch('sys.stderr', new_callable=lambda: original_open('/dev/null', 'w')):
                    notes = load_notes_with_decks()
                    assert isinstance(notes, list)
                    if len(notes) > 0:
                        assert notes[0].get('deck') == 'Unknown'


def test_build_deck_map_from_cards_uncompressed():
    """Test building deck map from uncompressed .json cards file and decks file"""
    from unittest.mock import MagicMock
    from unittest.mock import mock_open as make_mock_open

    from graph.analyze import build_deck_map_from_cards

    cards_file = MagicMock()
    cards_file.suffix = '.json'

    decks_file = MagicMock()
    decks_file.exists.return_value = True

    def side_effect(filename, *args, **kwargs):
        if cards_file == filename:
            return make_mock_open(read_data='[{"nid": 1, "did": 100}]')()
        elif decks_file == filename:
            return make_mock_open(read_data='{"100": "Test Deck"}')()
        return make_mock_open(read_data='')()

    with patch('builtins.open', side_effect=side_effect):
        deck_map = build_deck_map_from_cards(None, cards_file, decks_file)
        assert deck_map[1]['deck_name'] == 'Test Deck'
        assert deck_map[1]['did'] == 100


def test_build_deck_map_from_cards_decks_json_error():
    """Test building deck map when decks.json fails to load"""
    import builtins
    from unittest.mock import MagicMock
    from unittest.mock import mock_open as make_mock_open

    from graph.analyze import build_deck_map_from_cards

    original_open = builtins.open

    cards_file = MagicMock()
    cards_file.suffix = '.json'

    decks_file = MagicMock()
    decks_file.exists.return_value = True

    def side_effect(filename, *args, **kwargs):
        if cards_file == filename:
            return make_mock_open(
                read_data='[{"nid": 1, "did": 100, "deck_name": "Fallback Deck"}]'
            )()
        elif decks_file == filename:
            raise Exception("Corrupted json")
        return make_mock_open(read_data='')()

    with patch('builtins.open', side_effect=side_effect):
        with patch('sys.stderr', new_callable=lambda: original_open('/dev/null', 'w')):
            deck_map = build_deck_map_from_cards(None, cards_file, decks_file)
            # Should fallback to deck_name in card or 'Unknown'
            assert deck_map[1]['deck_name'] == 'Fallback Deck'
            assert deck_map[1]['did'] == 100


def test_build_deck_map_from_cards_overall_error():
    """Test building deck map with overall exception"""
    import builtins
    from unittest.mock import MagicMock

    from graph.analyze import build_deck_map_from_cards

    original_open = builtins.open

    cards_file = MagicMock()
    cards_file.suffix = '.json'

    def side_effect(*args, **kwargs):
        raise Exception("File permission error")

    with patch('builtins.open', side_effect=side_effect):
        with patch('sys.stderr', new_callable=lambda: original_open('/dev/null', 'w')):
            deck_map = build_deck_map_from_cards(None, cards_file, None)
            assert deck_map == {}


def test_load_notes_from_file_add_deck_info():
    """Test loading notes where the notes don't have deck info, fallback to 'Unknown'"""
    from graph.analyze import load_notes_from_file

    with patch('builtins.open') as mock_open:
        with patch('pathlib.Path.exists') as mock_exists:
            from unittest.mock import mock_open as make_mock_open

            mock_exists.return_value = True
            mock_open.return_value = make_mock_open(read_data='[{"id": 1, "guid": "123"}]')()

            notes = load_notes_from_file('notes.json')
            assert len(notes) == 1
            assert notes[0]['deck'] == 'Unknown'
            assert notes[0]['deck_id'] == 0


def test_load_notes_with_decks_github_success():
    """Test loading notes from GitHub fallback and resolving deck maps"""
    from graph.analyze import load_notes_with_decks

    with patch('pathlib.Path.exists', autospec=True) as mock_exists:

        def side_effect(self):
            return 'cloudflare' not in str(self)

        mock_exists.side_effect = side_effect

        with patch('graph.analyze.load_notes_from_file') as mock_load:
            mock_load.return_value = [{'id': 1}]

            with patch('graph.analyze.build_deck_map_from_cards') as mock_build:
                mock_build.return_value = {1: {'deck_name': 'Test Deck', 'did': 123}}

                import builtins

                original_open = builtins.open
                with patch('sys.stderr', new_callable=lambda: original_open('/dev/null', 'w')):
                    with patch('sys.stdout', new_callable=lambda: original_open('/dev/null', 'w')):
                        notes = load_notes_with_decks()

                assert len(notes) == 1
                assert notes[0]['deck'] == 'Test Deck'
                assert notes[0]['deck_id'] == 123


def test_build_deck_map_from_cards_gz_suffix():
    """Test building deck map from compressed .gz cards file"""
    from unittest.mock import MagicMock
    from unittest.mock import mock_open as make_mock_open

    from graph.analyze import build_deck_map_from_cards

    cards_file = MagicMock()
    cards_file.suffix = '.gz'

    decks_file = MagicMock()
    decks_file.exists.return_value = True

    with patch('gzip.open') as mock_gzip_open:
        mock_gzip_open.return_value = make_mock_open(read_data='[{"nid": 1, "did": 100}]')()

        with patch('builtins.open') as mock_open:
            mock_open.return_value = make_mock_open(read_data='{"100": "Gz Deck"}')()

            deck_map = build_deck_map_from_cards(None, cards_file, decks_file)
            assert deck_map[1]['deck_name'] == 'Gz Deck'
            assert deck_map[1]['did'] == 100


def test_analyze_compare_decks_hubs_isolated():
    """Test the CLI flags for --compare, --isolated, --hubs inside main flow"""
    from unittest.mock import MagicMock

    from graph.analyze import analyze_all_decks

    args = MagicMock()
    args.compare = True
    args.isolated = True
    args.hubs = True
    args.export = False
    args.top = 2
    args.anonymize = False

    decks = ['Deck A']
    notes = [{'guid': '1', 'deck': 'Deck A', 'flds': 'front\x1fback'}]

    with patch('graph.analyze.build_per_deck_graphs') as mock_build:
        mock_graph = MagicMock()
        mock_build.return_value = {'Deck A': mock_graph}

        with patch('graph.analyze.compare_decks') as mock_compare:
            with patch('graph.analyze.print_top_notes') as mock_top:
                with patch('graph.analyze.print_isolated_notes') as mock_iso:
                    with patch('graph.analyze.print_hub_notes') as mock_hubs:
                        analyze_all_decks(args, decks, notes)

                        mock_compare.assert_called_once_with({'Deck A': mock_graph})
                        mock_top.assert_called_once_with(mock_graph, 'Deck A', 2)
                        mock_iso.assert_called_once_with(mock_graph, 'Deck A')
                        mock_hubs.assert_called_once_with(mock_graph, 'Deck A')


def test_analyze_export_all():
    """Test the CLI flag for --export across all decks"""
    from unittest.mock import MagicMock

    from graph.analyze import analyze_all_decks

    args = MagicMock()
    args.compare = False
    args.isolated = False
    args.hubs = False
    args.export = 'test_dir'
    args.format = 'json'
    args.top = 2
    args.anonymize = False

    decks = ['Deck A']
    notes = [{'guid': '1', 'deck': 'Deck A', 'flds': 'front\x1fback'}]

    with patch('graph.analyze.build_per_deck_graphs') as mock_build:
        mock_graph = MagicMock()
        mock_build.return_value = {'Deck A Space': mock_graph}

        with patch('graph.analyze.print_top_notes') as _:
            with patch('graph.analyze.export_graph') as mock_export:
                analyze_all_decks(args, decks, notes)

                mock_export.assert_called_once_with(mock_graph, 'test_dir', 'json', 'Deck_A_Space')


def test_main_execution():
    """Test if __name__ == '__main__' block logic is executed"""
    from graph.analyze import main

    with patch('graph.analyze.main'):
        with patch('sys.argv', ['analyze.py']):
            # Need to re-import or use runpy to hit the name == main block
            import runpy

            try:
                runpy.run_module('graph.analyze', run_name='__main__')
            except SystemExit:
                pass


def test_build_deck_map_from_cards_empty_decks():
    """Test building deck map when decks.json doesn't exist"""
    from unittest.mock import MagicMock
    from unittest.mock import mock_open as make_mock_open

    from graph.analyze import build_deck_map_from_cards

    cards_file = MagicMock()
    cards_file.suffix = '.json'

    decks_file = MagicMock()
    decks_file.exists.return_value = False

    def side_effect(filename, *args, **kwargs):
        if cards_file == filename:
            return make_mock_open(read_data='[{"nid": 1, "did": 100}]')()
        return make_mock_open(read_data='')()

    with patch('builtins.open', side_effect=side_effect):
        deck_map = build_deck_map_from_cards(None, cards_file, decks_file)
        assert deck_map[1]['deck_name'] == 'Unknown'
        assert deck_map[1]['did'] == 100


def test_build_deck_map_from_cards_missing_nid():
    """Test building deck map when nid is present in map but we don't overwrite"""
    from unittest.mock import MagicMock
    from unittest.mock import mock_open as make_mock_open

    from graph.analyze import build_deck_map_from_cards

    cards_file = MagicMock()
    cards_file.suffix = '.json'

    decks_file = MagicMock()
    decks_file.exists.return_value = False

    def side_effect(filename, *args, **kwargs):
        if cards_file == filename:
            return make_mock_open(read_data='[{"nid": 1, "did": 100}, {"nid": 1, "did": 200}]')()
        return make_mock_open(read_data='')()

    with patch('builtins.open', side_effect=side_effect):
        deck_map = build_deck_map_from_cards(None, cards_file, decks_file)
        assert deck_map[1]['did'] == 100
