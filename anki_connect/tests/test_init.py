import base64
import tempfile
import unittest.mock as mock
import pytest
import aqt

from anki_connect import AnkiConnect, util, web


@pytest.fixture
def ac():
    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: None if k == "apiKey" else (6 if k == "apiVersion" else 1000),
    ):
        instance = AnkiConnect()
        yield instance


def test_ankiconnect_init_and_logging(ac):
    assert ac.server is not None
    with tempfile.NamedTemporaryFile() as tmp:
        with mock.patch.object(util, "setting", return_value=tmp.name):
            ac.initLogging()
            assert ac.log is not None
            ac.logEvent("test_event", {"key": "val"})
            ac.log.close()
            ac.log = None


def test_handler_api_key_check(ac):
    with mock.patch.object(
        util, "setting", side_effect=lambda k: "secret_key" if k == "apiKey" else 6
    ):
        # Invalid API key
        req = {"action": "version", "version": 6, "key": "wrong_key"}
        reply = ac.handler(req)
        assert reply["error"] == "valid api key must be provided"

        # Valid API key
        req_valid = {"action": "version", "version": 6, "key": "secret_key"}
        reply_valid = ac.handler(req_valid)
        assert reply_valid["result"] == 6
        assert reply_valid["error"] is None

        # requestPermission bypassing API key check
        req_perm = {
            "action": "requestPermission",
            "version": 6,
            "key": "wrong_key",
            "params": {"origin": "http://localhost", "allowed": True},
        }
        reply_perm = ac.handler(req_perm)
        assert reply_perm["error"] is None
        assert reply_perm["result"]["permission"] == "granted"


def test_handler_unsupported_action(ac):
    req = {"action": "non_existent_action", "version": 6}
    reply = ac.handler(req)
    assert reply["error"] == "unsupported action"


def test_api_version_endpoint(ac):
    reply = ac.handler({"action": "version", "version": 6})
    assert reply["result"] == 6


def test_api_deck_names(ac):
    mock_col = mock.MagicMock()
    mock_deck = mock.MagicMock()
    mock_deck.name = "Default"
    mock_col.decks.all_names_and_ids.return_value = [mock_deck]
    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw):
        res = ac.deckNames()
        assert "Default" in res


def test_api_create_deck(ac):
    mock_col = mock.MagicMock()
    mock_col.decks.id.return_value = 12345
    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw):
        did = ac.createDeck(deck="TestDeck")
        assert did == 12345
        mock_col.decks.id.assert_called_once_with("TestDeck")


def test_api_delete_decks(ac):
    mock_col = mock.MagicMock()
    mock_col.decks.id.return_value = 12345
    mock_mw = mock.MagicMock(col=mock_col)
    with (
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch.object(ac, "deckNames", return_value=["TestDeck"]),
    ):
        ac.deleteDecks(decks=["TestDeck"], cardsToo=True)
        mock_col.decks.remove.assert_called_once_with([12345])


def test_api_model_names(ac):
    mock_col = mock.MagicMock()
    mock_m = mock.MagicMock()
    mock_m.name = "Basic"
    mock_col.models.all_names_and_ids.return_value = [mock_m]
    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw):
        names = ac.modelNames()
        assert "Basic" in names


def test_api_model_field_names(ac):
    mock_col = mock.MagicMock()
    mock_model = {"flds": [{"name": "Front"}, {"name": "Back"}]}
    mock_col.models.by_name.return_value = mock_model
    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw):
        fields = ac.modelFieldNames(modelName="Basic")
        assert fields == ["Front", "Back"]


def test_api_add_note(ac):
    mock_col = mock.MagicMock()
    mock_model = {"id": 1, "flds": [{"name": "Front"}, {"name": "Back"}]}
    mock_col.models.by_name.return_value = mock_model
    mock_note = mock.MagicMock(id=999)
    mock_mw = mock.MagicMock(col=mock_col)

    note_param = {
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {"Front": "Question", "Back": "Answer"},
        "tags": ["tag1"],
    }

    with (
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch.object(ac, "createNote", return_value=mock_note),
        mock.patch.object(ac, "isNoteDuplicateOrEmptyInScope", return_value=0),
    ):
        mock_col.addNote.return_value = 1
        nid = ac.addNote(note=note_param)
        assert nid == 999


def test_can_add_note(ac):
    with mock.patch.object(ac, "createNote", return_value=mock.MagicMock()):
        assert ac.canAddNote(note={}) is True
        assert ac.canAddNoteWithErrorDetail(note={}) == {"canAdd": True}

    with mock.patch.object(ac, "createNote", side_effect=Exception("duplicate")):
        assert ac.canAddNote(note={}) is False
        assert ac.canAddNoteWithErrorDetail(note={}) == {"canAdd": False, "error": "duplicate"}


def test_update_note_fields_and_tags(ac):
    mock_note = mock.MagicMock()
    mock_note.__contains__.side_effect = lambda k: k == "Front"
    mock_col = mock.MagicMock()
    mock_mw = mock.MagicMock(col=mock_col)

    with (
        mock.patch.object(ac, "getNote", return_value=mock_note),
        mock.patch.object(ac, "startEditing"),
        mock.patch.object(ac, "addMediaFromNote"),
        mock.patch.object(aqt, "mw", mock_mw),
    ):
        ac.updateNoteFields({"id": 123, "fields": {"Front": "New Question"}})
        mock_note.__setitem__.assert_called_once_with("Front", "New Question")
        mock_col.update_note.assert_called_once_with(mock_note, skip_undo_entry=True)

    with (
        mock.patch.object(ac, "getNoteTags", return_value=["tag1"]),
        mock.patch.object(ac, "removeTags") as mock_rem,
        mock.patch.object(ac, "addTags") as mock_add,
    ):
        ac.updateNoteTags(123, ["tag2"])
        mock_rem.assert_called_once_with([123], "tag1")
        mock_add.assert_called_once_with([123], "tag2")


def test_tag_operations(ac):
    mock_col = mock.MagicMock()
    mock_col.tags.all.return_value = ["tag1", "tag2"]
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw), mock.patch.object(ac, "startEditing"):
        ac.addTags([123], "tag1", True)
        mock_col.tags.bulkAdd.assert_called_once_with([123], "tag1", True)

        ac.removeTags([123], "tag1")
        mock_col.tags.bulkAdd.assert_called_with([123], "tag1", False)

        assert ac.getTags() == ["tag1", "tag2"]
        ac.clearUnusedTags()
        mock_col.tags.registerNotes.assert_called_once()


def test_model_templates_and_styling(ac):
    mock_col = mock.MagicMock()
    mock_model = {
        "flds": [{"name": "Front"}, {"name": "Back"}],
        "tmpls": [{"name": "Card 1", "qfmt": "{{Front}}", "afmt": "{{FrontSide}}\n\n{{Back}}"}],
        "css": "body { color: black; }",
    }
    mock_col.models.by_name.return_value = mock_model
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        tmpls = ac.modelTemplates(modelName="Basic")
        assert tmpls == {"Card 1": {"Front": "{{Front}}", "Back": "{{FrontSide}}\n\n{{Back}}"}}

        styling = ac.modelStyling(modelName="Basic")
        assert styling == {"css": "body { color: black; }"}


def test_api_store_and_retrieve_media_file(ac):
    mock_media = mock.MagicMock()
    mock_col = mock.MagicMock(media=mock_media)
    mock_media.writeData.return_value = "file.txt"
    mock_media.have.return_value = True
    mock_mw = mock.MagicMock(col=mock_col)

    b64_data = base64.b64encode(b"hello world").decode("utf-8")

    with (
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch("os.path.exists", return_value=True),
        mock.patch("builtins.open", mock.mock_open(read_data=b"hello world")),
    ):
        filename = ac.storeMediaFile(filename="file.txt", data=b64_data)
        assert filename == "file.txt"

        retrieved_b64 = ac.retrieveMediaFile(filename="file.txt")
        assert retrieved_b64 == b64_data


def test_media_file_management(ac):
    mock_media = mock.MagicMock()
    mock_media.dir.return_value = "/media"
    mock_col = mock.MagicMock(media=mock_media)
    mock_mw = mock.MagicMock(col=mock_col)

    with (
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch.object(ac, "startEditing"),
        mock.patch("glob.glob", return_value=["/media/a.jpg"]),
    ):
        files = ac.getMediaFilesNames(pattern="*.jpg")
        assert files == ["a.jpg"]

        ac.deleteMediaFile(filename="a.jpg")
        mock_media.trash_files.assert_called_once_with(["a.jpg"])


def test_api_gui_browse(ac):
    mock_browser = mock.MagicMock()
    with (
        mock.patch.object(aqt.dialogs, "open", return_value=mock_browser),
        mock.patch.object(ac, "findCards", return_value=[101, 102]),
    ):
        res = ac.guiBrowse(query="deck:Default")
        mock_browser.form.searchEdit.lineEdit().setText.assert_called_once_with("deck:Default")
        assert res == [101, 102]


def test_gui_card_and_note_actions(ac):
    with mock.patch("anki_connect.Edit.open_dialog_and_show_note_with_id") as mock_open_dialog:
        ac.guiEditNote(note=123)
        mock_open_dialog.assert_called_once_with(123)

    mock_browser = mock.MagicMock()
    dict_dialogs = {"Browser": (None, mock_browser)}
    with mock.patch.object(aqt.dialogs, "_dialogs", dict_dialogs):
        assert ac.guiSelectCard(card=456) is True
        mock_browser.table.clear_selection.assert_called_once()
        mock_browser.table.select_single_card.assert_called_once_with(456)


def test_api_sync(ac):
    mock_mw = mock.MagicMock()
    mock_auth = mock.MagicMock()
    mock_mw.pm.sync_auth.return_value = mock_auth
    mock_mw.pm.media_syncing_enabled.return_value = True
    mock_out = mock.MagicMock()
    mock_out.required = "NO_CHANGES"
    mock_out.NO_CHANGES = "NO_CHANGES"
    mock_col = mock.MagicMock()
    mock_col.sync_collection.return_value = mock_out
    mock_mw.col = mock_col

    with mock.patch.object(aqt, "mw", mock_mw):
        ac.sync()
        mock_col.sync_collection.assert_called_once_with(mock_auth, True)
