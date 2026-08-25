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
