import sys
import os
from unittest.mock import MagicMock, patch

# Mock aqt before import
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.gui_hooks'] = MagicMock()
sys.modules['aqt.editor'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()

import auto_wiktionary
from auto_wiktionary import _apply_wiktionary, on_auto_wiktionary, _on_selection_result, _use_front_field, on_editor_did_init_buttons

def test_apply_wiktionary_no_text():
    editor = MagicMock()
    with patch("auto_wiktionary.clean_html_text", return_value=""):
        _apply_wiktionary(editor, "")
    assert sys.modules['aqt.utils'].tooltip.called

def test_apply_wiktionary_no_back_field():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["front"]
    with patch("auto_wiktionary.clean_html_text", return_value="test"), \
         patch("auto_wiktionary.detect_language", return_value="en"), \
         patch("auto_wiktionary.fetch_wiktionary_html", return_value="html"), \
         patch("auto_wiktionary.parse_wiktionary_html", return_value="parsed"):
        _apply_wiktionary(editor, "test")
    assert sys.modules['aqt.utils'].tooltip.called
