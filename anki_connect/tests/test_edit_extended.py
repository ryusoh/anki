import unittest.mock as mock
import pytest
import aqt

from anki_connect import edit


def test_edit_instance_methods():
    mock_note = mock.MagicMock(id=101)
    mock_note.cards.return_value = [mock.MagicMock(id=1, queue=0)]

    mock_ui = mock.MagicMock()
    mock_editor = mock.MagicMock()

    with (
        mock.patch("aqt.forms.editcurrent.Ui_Dialog", return_value=mock_ui),
        mock.patch.object(aqt.editor, "Editor", return_value=mock_editor),
        mock.patch("aqt.utils.restoreGeom"),
        mock.patch("aqt.utils.saveGeom"),
        mock.patch("aqt.dialogs.markClosed"),
        mock.patch("anki_connect.edit.history.remove_invalid_notes"),
        mock.patch.object(edit.Edit, "bring_to_foreground"),
    ):

        ed = edit.Edit(mock_note)
        assert ed.note == mock_note
        assert ed.editor == mock_editor
        assert mock_editor.set_note.call_count == 1
        mock_editor.set_note.assert_called_with(mock_note)

        # Test reopen
        new_note = mock.MagicMock(id=102)
        new_note.cards.return_value = []
        ed.reopen(new_note)
        assert ed.note == new_note

        # Test hooks and actions
        changes = mock.MagicMock(note_text=True)
        with mock.patch.object(ed, "reload_notes_after_user_action_elsewhere") as mock_reload:
            ed.on_operation_did_execute(changes, handler=None)
            mock_reload.assert_called_once()

        with mock.patch.object(ed, "enable_disable_next_and_previous_buttons") as mock_enable:
            ed.editor_did_load_note(mock_editor)
            mock_enable.assert_called_once()

        # Test navigation actions
        with (
            mock.patch("anki_connect.edit.history.has_note_to_left_of", return_value=True),
            mock.patch("anki_connect.edit.history.get_note_to_left_of", return_value=mock_note),
            mock.patch.object(ed, "show_note") as mock_show,
        ):
            ed.show_previous()
            mock_show.assert_called_with(mock_note)

        with (
            mock.patch("anki_connect.edit.history.has_note_to_right_of", return_value=True),
            mock.patch("anki_connect.edit.history.get_note_to_right_of", return_value=mock_note),
            mock.patch.object(ed, "show_note") as mock_show,
        ):
            ed.show_next()
            mock_show.assert_called_with(mock_note)

        # Test preview
        ed.note.cards.return_value = [mock.MagicMock(id=1)]
        with mock.patch("anki_connect.edit.DecentPreviewer") as mock_prev_cls:
            previewer_inst = ed.show_preview()
            assert previewer_inst is not None

        # Test cleanup and closeEvent
        mock_editor.call_after_note_saved.side_effect = lambda cb: cb()
        ed.closeEvent(mock.MagicMock())
        mock_editor.cleanup.assert_called_once()


def test_edit_reload_notes_after_user_action_elsewhere():
    mock_note = mock.MagicMock(id=101)
    mock_ui = mock.MagicMock()
    mock_editor = mock.MagicMock()

    with (
        mock.patch("aqt.forms.editcurrent.Ui_Dialog", return_value=mock_ui),
        mock.patch("aqt.editor.Editor", return_value=mock_editor),
        mock.patch("aqt.utils.restoreGeom"),
        mock.patch("anki_connect.edit.history.remove_invalid_notes"),
        mock.patch.object(edit.Edit, "bring_to_foreground"),
    ):
        ed = edit.Edit(mock_note)

        # Reload success
        ed.reload_notes_after_user_action_elsewhere()
        mock_note.load.assert_called()

        # Reload throws NotFoundError -> fallback to history
        mock_note.load.side_effect = edit.NotFoundError
        fallback_note = mock.MagicMock(id=100)
        fallback_note.cards.return_value = []
        with mock.patch("anki_connect.edit.history.get_last_note", return_value=fallback_note):
            ed.reload_notes_after_user_action_elsewhere()
            assert ed.note == fallback_note


def test_browser_will_search_classmethod():
    ctx = mock.MagicMock(search=edit.Edit.dialog_search_tag)
    ctx.browser.table._state.sort_column = edit.Edit.dialog_search_tag

    with mock.patch("anki_connect.edit.trigger_search_for_dialog_history_notes") as mock_trig:
        edit.Edit.browser_will_search(ctx)
        mock_trig.assert_called_once_with(search_context=ctx, use_history_order=True)
