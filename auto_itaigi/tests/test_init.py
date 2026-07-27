from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

# Mock aqt before import
sys.modules["aqt"] = MagicMock()
sys.modules["aqt.gui_hooks"] = MagicMock()
sys.modules["aqt.editor"] = MagicMock()
sys.modules["aqt.utils"] = MagicMock()

import auto_itaigi
from auto_itaigi import (
    _apply_itaigi,
    _on_selection_result,
    _use_front_field,
    on_auto_itaigi,
    on_editor_did_init_buttons,
)

_FIXTURE = json.dumps(
    {
        "列表": [
            {
                "外語資料": "蕃薯",
                "新詞文本": [
                    {
                        "文本資料": "蕃薯",
                        "音標資料": "han-tsî/han-tsû",
                        "按呢講好": 34,
                        "按呢講的外語列表": [
                            {"外語資料": "蕃薯"},
                            {"外語資料": "甘薯"},
                            {"外語資料": "地瓜"},
                        ],
                    }
                ],
            }
        ],
        "其他建議": [],
    },
    ensure_ascii=False,
)


def _editor_with_note():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["Front", "Back"]
    editor.note.fields = ["", ""]
    return editor


def test_apply_itaigi_no_text():
    editor = MagicMock()
    with patch("auto_itaigi._clean_html_text", return_value=""):
        _apply_itaigi(editor, "")
    assert sys.modules["aqt.utils"].tooltip.called


def test_apply_itaigi_no_back_field():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["front"]
    with patch("auto_itaigi._clean_html_text", return_value="test"):
        _apply_itaigi(editor, "test")
    assert sys.modules["aqt.utils"].tooltip.called


def test_apply_itaigi_success_with_audio():
    editor = _editor_with_note()
    with (
        patch("auto_itaigi.fetch_itaigi_json", return_value=_FIXTURE),
        patch("auto_itaigi.save_audio_to_media", return_value="itaigi_han-tsi.mp3"),
    ):
        _apply_itaigi(editor, "番薯")
    expected = (
        "han-tsî/han-tsû<br>華語：蕃薯 甘薯 地瓜<br>[sound:itaigi_han-tsi.mp3]"
    )
    assert editor.note.fields[1] == expected
    assert editor.loadNoteKeepingFocus.called
    assert sys.modules["aqt.utils"].tooltip.called


def test_apply_itaigi_not_found():
    editor = _editor_with_note()
    with patch("auto_itaigi.fetch_itaigi_json", return_value='{"列表": []}'):
        _apply_itaigi(editor, "番薯")
    assert editor.note.fields[1] == ""
    assert not editor.loadNoteKeepingFocus.called
    assert sys.modules["aqt.utils"].tooltip.called


def test_apply_itaigi_audio_failure_still_writes_text():
    editor = _editor_with_note()
    with (
        patch("auto_itaigi.fetch_itaigi_json", return_value=_FIXTURE),
        patch("auto_itaigi.save_audio_to_media", return_value=None),
    ):
        _apply_itaigi(editor, "番薯")
    assert editor.note.fields[1] == "han-tsî/han-tsû<br>華語：蕃薯 甘薯 地瓜"


def test_apply_itaigi_fetch_error():
    editor = _editor_with_note()
    with patch("auto_itaigi.fetch_itaigi_json", return_value="Error: 500"):
        _apply_itaigi(editor, "番薯")
    assert editor.note.fields[1] == ""
    assert sys.modules["aqt.utils"].tooltip.called


def test_on_auto_itaigi_no_note():
    editor = MagicMock()
    editor.note = None
    on_auto_itaigi(editor)
    assert not editor.web.evalWithCallback.called


def test_on_auto_itaigi_with_note():
    editor = _editor_with_note()
    on_auto_itaigi(editor)
    assert editor.web.evalWithCallback.called


def test_on_selection_result_with_selection():
    editor = MagicMock()
    _on_selection_result(editor, "selected text")
    assert editor.saveNow.called


def test_on_selection_result_no_selection():
    editor = MagicMock()
    _on_selection_result(editor, "")
    assert editor.saveNow.called


def test_use_front_field_no_note():
    editor = MagicMock()
    editor.note = None
    _use_front_field(editor)


def test_use_front_field_no_front_field():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["NotFront"]
    _use_front_field(editor)
    assert sys.modules["aqt.utils"].tooltip.called


def test_use_front_field_success():
    editor = MagicMock()
    editor.note = MagicMock()
    editor.note.keys.return_value = ["Front"]
    editor.note.fields = ["front text"]
    with patch("auto_itaigi._apply_itaigi") as mock_apply:
        _use_front_field(editor)
        mock_apply.assert_called_with(editor, "front text")


def test_on_editor_did_init_buttons():
    editor = MagicMock()
    on_editor_did_init_buttons([], editor)
    assert editor.addButton.called


def test_apply_itaigi_exception_caught():
    editor = _editor_with_note()
    editor.loadNoteKeepingFocus.side_effect = Exception("boom")
    with (
        patch("auto_itaigi.fetch_itaigi_json", return_value=_FIXTURE),
        patch("auto_itaigi.save_audio_to_media", return_value="itaigi_han-tsi.mp3"),
    ):
        _apply_itaigi(editor, "番薯")
