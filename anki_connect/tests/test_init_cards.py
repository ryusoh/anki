import unittest.mock as mock
import pytest
from anki.errors import NotFoundError
import aqt
from anki_connect import AnkiConnect, util


@pytest.fixture
def ac():
    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: None if k == "apiKey" else (6 if k == "apiVersion" else 1000),
    ):
        instance = AnkiConnect()
        yield instance


def test_get_card_success_and_not_found(ac):
    mock_col = mock.MagicMock()
    mock_card = mock.MagicMock(id=101)
    mock_col.get_card.side_effect = lambda cid: (
        mock_card if cid == 101 else (_ for _ in ()).throw(NotFoundError("Card not found"))
    )

    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.getCard(101) == mock_card
        with pytest.raises(NotFoundError):
            ac.getCard(999)


def test_cards_info(ac):
    mock_col = mock.MagicMock()
    mock_card = mock.MagicMock()
    mock_card.id = 101
    mock_card.ord = 0
    mock_card.did = 1
    mock_card.factor = 2500
    mock_card.reps = 3
    mock_card.lapses = 0
    mock_card.left = 0
    mock_card.type = 2
    mock_card.queue = 2
    mock_card.due = 100
    mock_card.ivl = 10
    mock_card.mod = 1600000000
    mock_card.nid = 50
    mock_card.flags = 0

    mock_note_obj = mock.MagicMock(id=50, fields=["Val1", "Val2"])
    mock_card.note.return_value = mock_note_obj

    model_dict = {
        "name": "Basic",
        "css": "body {}",
        "flds": [{"name": "Front", "ord": 0}],
    }
    mock_card.note_type.return_value = model_dict

    mock_col.get_card.side_effect = lambda cid: (
        mock_card if cid == 101 else (_ for _ in ()).throw(NotFoundError("not found"))
    )
    mock_col.decks.name.return_value = "Default"
    mock_col._backend.describe_next_states.return_value = []
    mock_mw = mock.MagicMock(col=mock_col)

    with (
        mock.patch("anki_connect.util.cardQuestion", return_value="Q"),
        mock.patch("anki_connect.util.cardAnswer", return_value="A"),
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch.object(ac, "deckNameFromId", return_value="Default"),
    ):

        res = ac.cardsInfo([101, 999])
        assert len(res) == 2
        assert res[0]["cardId"] == 101
        assert res[1] == {}


def test_cards_mod_time(ac):
    mock_col = mock.MagicMock()
    mock_card = mock.MagicMock(id=101, mod=1600000000)
    mock_col.get_card.side_effect = lambda cid: (
        mock_card if cid == 101 else (_ for _ in ()).throw(NotFoundError("not found"))
    )
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        res = ac.cardsModTime([101, 999])
        assert len(res) == 2
        assert res[0] == {"cardId": 101, "mod": 1600000000}
        assert res[1] == {}


def test_forget_cards(ac):
    mock_col = mock.MagicMock()
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw), mock.patch.object(ac, "startEditing"):
        ac.forgetCards([101, 102])
        mock_col._backend.schedule_cards_as_new.assert_called_once()


def test_relearn_cards(ac):
    mock_col = mock.MagicMock()
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw), mock.patch.object(ac, "startEditing"):
        ac.relearnCards([101, 102])
        mock_col.db.execute.assert_called_once_with(
            "update cards set type=3, queue=1 where id in (101,102)"
        )


def test_answer_cards(ac):
    card1 = mock.MagicMock(id=101)
    mock_col = mock.MagicMock()
    mock_col.get_card.side_effect = lambda cid: (
        card1 if cid == 101 else (_ for _ in ()).throw(NotFoundError("not found"))
    )
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw), mock.patch.object(ac, "startEditing"):
        res = ac.answerCards(answers=[{"cardId": 101, "ease": 3}, {"cardId": 999, "ease": 2}])
        assert res[0] is True
        assert res[1] is False


def test_set_and_get_ease_factors(ac):
    card1 = mock.MagicMock(id=101, factor=2000)
    mock_col = mock.MagicMock()
    mock_col.get_card.side_effect = lambda cid: (
        card1 if cid == 101 else (_ for _ in ()).throw(NotFoundError("not found"))
    )
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        factors = ac.getEaseFactors([101, 999])
        assert factors == [2000, None]

        set_res = ac.setEaseFactors([101, 999], [2500, 2500])
        assert set_res == [True, False]
        assert card1.factor == 2500


def test_suspend_unsuspend_are_suspended(ac):
    card1 = mock.MagicMock(id=101, queue=-1)
    card2 = mock.MagicMock(id=102, queue=1)
    mock_col = mock.MagicMock()

    def get_card(cid):
        if cid == 101:
            return card1
        if cid == 102:
            return card2
        raise NotFoundError("not found")

    mock_col.get_card.side_effect = get_card
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw), mock.patch.object(ac, "startEditing"):
        # suspended check
        assert ac.suspended(101) is True
        assert ac.suspended(102) is False
        assert ac.areSuspended([101, 102, 999]) == [True, False, None]

        # suspend card2
        res = ac.suspend([101, 102], True)
        assert res is True

        # unsuspend
        ac.unsuspend([101])


def test_are_due(ac):
    mock_col = mock.MagicMock()
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        with mock.patch.object(
            ac, "findCards", side_effect=lambda q: [101] if "is:new" in q else []
        ):
            assert ac.areDue([101]) == [True]


def test_get_intervals(ac):
    mock_col = mock.MagicMock()
    mock_col.db.list.return_value = [1, 5, 10]
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        with mock.patch.object(ac, "findCards", return_value=[101]):
            assert ac.getIntervals([101]) == [0]


def test_cards_to_notes(ac):
    mock_col = mock.MagicMock()
    mock_col.db.list.return_value = [50, 51]
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        res = ac.cardsToNotes([101, 102])
        assert res == [50, 51]
        mock_col.db.list.assert_called_once_with(
            "select distinct nid from cards where id in (101,102)"
        )


def test_get_reviews_of_cards_batching(ac):
    mock_col = mock.MagicMock()
    cards = list(range(1, 1005))
    mock_col.db.all.side_effect = [
        [(cid, cid * 10, 0, 2, 5, 1, 2500, 10, 1) for cid in cards[:999]],
        [(cid, cid * 10, 0, 2, 5, 1, 2500, 10, 1) for cid in cards[999:]],
    ]
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        res = ac.getReviewsOfCards(cards)
        assert len(res) == 1004
        assert res[1][0]["id"] == 10
        assert res[1000][0]["id"] == 10000


def test_set_specific_value_of_card_restricted_keys(ac):
    mock_card = mock.MagicMock(id=101)
    mock_col = mock.MagicMock()
    mock_col.get_card.return_value = mock_card
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        for restricted_key in [
            "did",
            "id",
            "ivl",
            "lapses",
            "left",
            "mod",
            "nid",
            "odid",
            "odue",
            "ord",
            "queue",
            "reps",
            "type",
            "usn",
        ]:
            res = ac.setSpecificValueOfCard(101, [restricted_key], [10], warning_check=False)
            assert res is False
