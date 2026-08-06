import unittest.mock as mock
import pytest
import aqt

from anki_connect import edit


def test_history():
    hist = edit.History()
    n1 = mock.MagicMock(id=101)
    n2 = mock.MagicMock(id=102)
    n3 = mock.MagicMock(id=103)

    hist.append(n1)
    hist.append(n2)
    hist.append(n3)

    assert hist.note_ids == [101, 102, 103]

    assert hist.has_note_to_left_of(n2) is True
    assert hist.has_note_to_left_of(n1) is False

    assert hist.has_note_to_right_of(n2) is True
    assert hist.has_note_to_right_of(n3) is False

    with mock.patch("anki_connect.edit.get_note_by_note_id", side_effect=lambda nid: f"Note_{nid}"):
        assert hist.get_note_to_left_of(n2) == "Note_101"
        assert hist.get_note_to_right_of(n2) == "Note_103"
        assert hist.get_last_note() == "Note_103"

    with mock.patch("anki_connect.edit.filter_valid_note_ids", return_value=[101, 103]):
        hist.remove_invalid_notes()
        assert hist.note_ids == [101, 103]


def test_ready_cards_adapter():
    c1, c2, c3 = mock.MagicMock(id=1), mock.MagicMock(id=2), mock.MagicMock(id=3)
    adapter = edit.ReadyCardsAdapter([c1, c2, c3])

    assert adapter.get_current_card() == c1
    assert adapter.can_select_previous_card() is False
    assert adapter.can_select_next_card() is True

    adapter.select_next_card()
    assert adapter.get_current_card() == c2
    assert adapter.can_select_previous_card() is True
    assert adapter.can_select_next_card() is True

    adapter.select_previous_card()
    assert adapter.get_current_card() == c1


def test_decent_previewer():
    c1, c2 = mock.MagicMock(id=1), mock.MagicMock(id=2)
    adapter = edit.ReadyCardsAdapter([c1, c2])

    with mock.patch("aqt.browser.previewer.MultiCardPreviewer.__init__", return_value=None):
        previewer = edit.DecentPreviewer(adapter)
        previewer.render_card = mock.MagicMock()
        previewer._state = "question"
        previewer._show_both_sides = False

        assert previewer.card() == c1
        assert previewer.card_changed() is True
        assert previewer.card_changed() is False

        assert previewer._should_enable_next() is True
        previewer._on_next_card()
        assert adapter.get_current_card() == c2
        previewer.render_card.assert_called_once()


def test_trigger_search_for_dialog_history_notes():
    edit.history.note_ids = [10, 20]
    ctx = mock.MagicMock()

    edit.trigger_search_for_dialog_history_notes(ctx, use_history_order=True)
    assert ctx.search == "nid:10 or nid:20"
    assert "case c.nid" in ctx.order

    edit.trigger_search_for_dialog_history_notes(ctx, use_history_order=False)
    assert ctx.search == "nid:10 or nid:20"


def test_edit_dialog_registration():
    dict_dialogs = {}
    with (
        mock.patch.object(aqt.dialogs, "_dialogs", dict_dialogs),
        mock.patch.object(aqt.dialogs, "register_dialog") as mock_reg,
    ):
        edit.Edit.register_with_anki()
        mock_reg.assert_called_once_with(edit.DOMAIN_PREFIX + "Edit", edit.Edit)


def test_open_dialog_and_show_note_with_id():
    with (
        mock.patch("anki_connect.edit.get_note_by_note_id", return_value="note_obj"),
        mock.patch.object(aqt.dialogs, "open", return_value="dialog_instance") as mock_open,
    ):
        res = edit.Edit.open_dialog_and_show_note_with_id(123)
        assert res == "dialog_instance"
        mock_open.assert_called_once_with(edit.DOMAIN_PREFIX + "Edit", "note_obj")
