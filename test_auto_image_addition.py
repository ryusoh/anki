import pytest
from unittest.mock import MagicMock, patch

import auto_image
from auto_image import _save_to_media, _flush_and_load, _use_front_field

def test_save_to_media():
    auto_image.mw = MagicMock()
    auto_image.mw.col.media.write_data = MagicMock()

    filename = _save_to_media(b'dummy_data', 'test query!@#', 1)

    assert filename == 'auto_image_test_query____1.jpg'
    auto_image.mw.col.media.write_data.assert_called_once_with('auto_image_test_query____1.jpg', b'dummy_data')

def test_flush_and_load_exception_flush():
    editor = MagicMock()
    editor.note.flush.side_effect = Exception("flush error")
    editor.addMode = False

    # We just need to ensure it doesn't crash
    _flush_and_load(editor)
    editor.loadNoteKeepingFocus.assert_called_once()

def test_flush_and_load_exception_load():
    editor = MagicMock()
    editor.addMode = False
    editor.loadNoteKeepingFocus.side_effect = Exception("load error")

    # We just need to ensure it doesn't crash
    _flush_and_load(editor)
    editor.note.flush.assert_called_once()

def test_use_front_field_none_note():
    editor = MagicMock()
    editor.note = None

    _use_front_field(editor)

    # No assertion needed, just verifying it returns early
