from unittest.mock import MagicMock, patch

import pytest

import auto_image
from auto_image import _apply_image, _save_to_media, _use_front_field


def test_apply_image_flush_exception():
    editor = MagicMock()
    editor.addMode = False
    editor.note.flush.side_effect = Exception("flush error")
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["Test", ""]

    with (
        patch("auto_image.clean_html_text", return_value="test_flush"),
        patch("auto_image.fetch_image_results", return_value=["url"]),
        patch("auto_image.download_image", return_value=b"data"),
        patch("auto_image._save_to_media", return_value="img.jpg"),
    ):
        _apply_image(editor, "test_flush")

    editor.loadNoteKeepingFocus.assert_called_once()


def test_apply_image_load_exception():
    editor = MagicMock()
    editor.addMode = False
    editor.loadNoteKeepingFocus.side_effect = Exception("load error")
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["Test", ""]

    with (
        patch("auto_image.clean_html_text", return_value="test_load"),
        patch("auto_image.fetch_image_results", return_value=["url"]),
        patch("auto_image.download_image", return_value=b"data"),
        patch("auto_image._save_to_media", return_value="img.jpg"),
    ):
        _apply_image(editor, "test_load")

    editor.note.flush.assert_called_once()


def test_use_front_field_none_note():
    editor = MagicMock()
    editor.note = None

    _use_front_field(editor)


def test_save_to_media():
    auto_image.mw = MagicMock()
    auto_image.mw.col.media.write_data = MagicMock()

    filename = _save_to_media(b'dummy_data', 'test query!@#', 1)

    assert filename == 'auto_image_test_query____1.jpg'
    auto_image.mw.col.media.write_data.assert_called_once_with(
        'auto_image_test_query____1.jpg', b'dummy_data'
    )
