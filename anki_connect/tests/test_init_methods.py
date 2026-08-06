import base64
import tempfile
import unittest.mock as mock
import pytest
import anki.errors
import aqt
from aqt.qt import QMessageBox
from anki_connect import AnkiConnect, util


@pytest.fixture
def ac():
    import anki_connect

    anki_connect.NotFoundError = anki.errors.NotFoundError
    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: (
            None
            if k == "apiKey"
            else (
                6
                if k == "apiVersion"
                else ([] if k in ("ignoreOriginList", "webCorsOriginList") else 1000)
            )
        ),
    ):
        instance = AnkiConnect()
        yield instance


# --- Internal / Accessor helpers ---


def test_accessors_and_exceptions(ac):
    mock_mw = mock.MagicMock()
    mock_mw.reviewer = None
    mock_mw.col = None
    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.window() == mock_mw

        with pytest.raises(Exception, match="reviewer is not available"):
            ac.reviewer()

        with pytest.raises(Exception, match="collection is not available"):
            ac.collection()

    mock_col = mock.MagicMock(decks=None, sched=None, db=None, media=None)
    mock_mw2 = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw2):
        with pytest.raises(Exception, match="decks are not available"):
            ac.decks()

        with pytest.raises(Exception, match="scheduler is not available"):
            ac.scheduler()

        with pytest.raises(Exception, match="database is not available"):
            ac.database()

        with pytest.raises(Exception, match="media is not available"):
            ac.media()


def test_get_model_field_template_helpers(ac):
    mock_col = mock.MagicMock()
    mock_model = {
        "name": "Basic",
        "flds": [{"name": "Front"}, {"name": "Back"}],
        "tmpls": [{"name": "Card 1"}],
    }
    mock_col.models.by_name.side_effect = lambda n: mock_model if n == "Basic" else None
    mock_col.models.field_map.return_value = {"Front": (0, {"name": "Front"})}
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.getModel("Basic") == mock_model
        with pytest.raises(Exception, match="model was not found"):
            ac.getModel("Missing")

        assert ac.getField(mock_model, "Front") == {"name": "Front"}
        with pytest.raises(Exception, match="field was not found"):
            ac.getField(mock_model, "MissingField")

        assert ac.getTemplate(mock_model, "Card 1") == {"name": "Card 1"}
        with pytest.raises(Exception, match="template was not found"):
            ac.getTemplate(mock_model, "MissingTemplate")


def test_start_web_server_exception(ac):
    with (
        mock.patch.object(ac.server, "listen", side_effect=Exception("bind error")),
        mock.patch("aqt.qt.QMessageBox.critical") as mock_crit,
        mock.patch.object(ac, "window", return_value=mock.MagicMock()),
    ):
        ac.startWebServer()
        mock_crit.assert_called_once()


def test_advance_and_logging(ac):
    with mock.patch.object(ac.server, "advance") as mock_adv:
        ac.advance()
        mock_adv.assert_called_once()


# --- Deck Methods ---


def test_deck_methods(ac):
    mock_col = mock.MagicMock()
    d1 = mock.MagicMock(id=1)
    d1.name = "Default"
    d2 = mock.MagicMock(id=2)
    d2.name = "Custom"
    mock_col.decks.all_names_and_ids.return_value = [d1, d2]

    deck_default = {"name": "Default", "id": 1, "conf": 1}
    deck_custom = {"name": "Custom", "id": 2, "conf": 1}
    mock_col.decks.by_name.side_effect = lambda n: (
        deck_default if n == "Default" else (deck_custom if n == "Custom" else None)
    )
    mock_col.decks.get.side_effect = lambda did: (
        deck_default if did == 1 else (deck_custom if did == 2 else None)
    )
    mock_col.decks.id.side_effect = lambda n: 1 if n == "Default" else (2 if n == "Custom" else 0)
    mock_col.decks.config_dict_for_deck_id.return_value = {"id": 1, "name": "DefaultConfig"}
    mock_col.decks.all_config.return_value = [{"id": 1}]
    mock_col.decks.get_config.return_value = {"id": 1, "name": "DefaultConfig"}
    mock_col.decks.add_config_returning_id.return_value = 2

    mock_col.db.scalar.return_value = 1

    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw), mock.patch.object(ac, "startEditing"):
        assert ac.deckNames() == ["Default", "Custom"]
        assert ac.deckNamesAndIds() == {"Default": 1, "Custom": 2}
        assert ac.getDecks([101, 102]) == {"Default": [101, 102]}

        assert ac.deckNameFromId(1) == "Default"
        with pytest.raises(Exception, match="deck was not found"):
            ac.deckNameFromId(999)

        assert ac.createDeck("NewDeck") == 0
        ac.changeDeck([101], "Custom")
        mock_col.sched.remFromDyn.assert_called_once_with([101])

        # deleteDecks without cardsToo
        with pytest.raises(Exception, match="not possible to delete decks without deleting cards"):
            ac.deleteDecks(["Default"], cardsToo=False)

        ac.deleteDecks(["Default"], cardsToo=True)
        mock_col.decks.remove.assert_called_with([1])

        # deck configs
        assert ac.getDeckConfig("Default") == {"id": 1, "name": "DefaultConfig"}
        assert ac.getDeckConfig("Missing") is False

        assert ac.saveDeckConfig({"id": 1}) is True
        assert ac.saveDeckConfig({"id": 999}) is False

        # saveDeckConfig failure branch
        mock_col.decks.save.side_effect = Exception("save err")
        assert ac.saveDeckConfig({"id": 1}) is False
        mock_col.decks.save.side_effect = None

        assert ac.setDeckConfigId(["Default"], 1) is True
        assert ac.setDeckConfigId(["Missing"], 1) is False

        assert ac.cloneDeckConfigId("Cloned", cloneFrom=1) == 2
        assert ac.cloneDeckConfigId("Cloned", cloneFrom=999) is False

        assert ac.removeDeckConfigId(1) is True
        assert ac.removeDeckConfigId(999) is False


def test_deck_stats(ac):
    mock_col = mock.MagicMock()
    mock_col.decks.id.return_value = 1
    mock_node = mock.MagicMock(
        deck_id=1, new_count=5, learn_count=2, review_count=3, total_in_deck=10, children=[]
    )
    mock_node.name = "Default"
    mock_sched = mock.MagicMock()
    mock_sched.deck_due_tree.return_value = mock_node
    mock_col.sched = mock_sched
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        stats = ac.getDeckStats(["Default"])
        assert 1 in stats
        assert stats[1]["name"] == "Default"
        assert stats[1]["new_count"] == 5


# --- Note & Tag Methods ---


def test_create_note_validation_and_options(ac):
    mock_col = mock.MagicMock()
    mock_model = {"id": 1, "name": "Basic"}
    mock_deck = {"id": 1, "name": "Default"}
    mock_col.models.by_name.side_effect = lambda n: mock_model if n == "Basic" else None
    mock_col.decks.by_name.side_effect = lambda n: mock_deck if n == "Default" else None

    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw):
        # missing model
        with pytest.raises(Exception, match="model was not found"):
            ac.createNote({"modelName": "Missing", "deckName": "Default", "fields": {}})

        # missing deck
        with pytest.raises(Exception, match="deck was not found"):
            ac.createNote({"modelName": "Basic", "deckName": "Missing", "fields": {}})

        # invalid option types
        with pytest.raises(Exception, match='option parameter "allowDuplicate" must be boolean'):
            ac.createNote(
                {
                    "modelName": "Basic",
                    "deckName": "Default",
                    "fields": {},
                    "options": {"allowDuplicate": "yes"},
                }
            )

        with pytest.raises(
            Exception,
            match='option parameter "duplicateScopeOptions.checkChildren" must be boolean',
        ):
            ac.createNote(
                {
                    "modelName": "Basic",
                    "deckName": "Default",
                    "fields": {},
                    "options": {"duplicateScopeOptions": {"checkChildren": "yes"}},
                }
            )

        with pytest.raises(
            Exception,
            match='option parameter "duplicateScopeOptions.checkAllModels" must be boolean',
        ):
            ac.createNote(
                {
                    "modelName": "Basic",
                    "deckName": "Default",
                    "fields": {},
                    "options": {"duplicateScopeOptions": {"checkAllModels": "yes"}},
                }
            )


def test_is_note_duplicate_or_empty_in_scope(ac):
    mock_col = mock.MagicMock()
    mock_note = mock.MagicMock(fields=["front_text"], id=10, mid=1, col=mock_col)
    mock_deck = {"id": 1, "name": "Default"}

    # empty field returns 1
    mock_empty_note = mock.MagicMock(fields=["   "])
    assert (
        ac.isNoteDuplicateOrEmptyInScope(
            mock_empty_note, mock_deck, mock_col, "deck", None, False, True
        )
        == 1
    )

    # duplicateScope == 'deck', duplicateScopeDeckName invalid returns 0
    mock_col.decks.by_name.return_value = None
    assert (
        ac.isNoteDuplicateOrEmptyInScope(
            mock_note, mock_deck, mock_col, "deck", "InvalidDeck", False, True
        )
        == 0
    )

    # duplicate note exists in collection
    mock_col.decks.by_name.return_value = {"id": 2}
    mock_col.decks.children.return_value = [("Child", 3)]
    mock_col.db.list.side_effect = [
        [20],  # notes query returns noteId 20
        [2, 3],  # cards query returns card deckId 2, 3
    ]
    assert (
        ac.isNoteDuplicateOrEmptyInScope(
            mock_note, mock_deck, mock_col, "deck", "CustomDeck", True, False
        )
        == 2
    )


def test_add_note_empty_question_error(ac):
    mock_col = mock.MagicMock()
    mock_col.addNote.return_value = 0
    mock_mw = mock.MagicMock(col=mock_col)

    with (
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch.object(ac, "startEditing"),
        mock.patch.object(ac, "createNote", return_value=mock.MagicMock()),
    ):
        with pytest.raises(Exception, match="would make an empty question"):
            ac.addNote({})


def test_add_notes_and_can_add_notes(ac):
    with (
        mock.patch.object(ac, "addNote", side_effect=[101, 102]),
        mock.patch.object(ac, "deleteNotes") as mock_del,
    ):
        assert ac.addNotes([{"note": 1}, {"note": 2}]) == [101, 102]
        mock_del.assert_not_called()

    # Exception in addNotes triggers rollback
    with (
        mock.patch.object(ac, "addNote", side_effect=[101, Exception("error")]),
        mock.patch.object(ac, "deleteNotes") as mock_del,
    ):
        with pytest.raises(Exception, match="error"):
            ac.addNotes([{"note": 1}, {"note": 2}])
        mock_del.assert_called_once_with([101])

    with mock.patch.object(ac, "canAddNote", return_value=True):
        assert ac.canAddNotes([{}, {}]) == [True, True]

    with mock.patch.object(ac, "canAddNoteWithErrorDetail", return_value={"canAdd": True}):
        assert ac.canAddNotesWithErrorDetail([{}, {}]) == [{"canAdd": True}, {"canAdd": True}]


def test_add_media_to_note(ac):
    with mock.patch.object(ac, "storeMediaFile", return_value="img.png"):
        note_param = {
            "picture": [{"filename": "img.png", "fields": ["Front"]}],
            "audio": [{"filename": "audio.mp3", "fields": ["Back"]}],
        }
        mock_anki_note = {"Front": "Q: ", "Back": "A: "}

        ac.addMediaFromNote(mock_anki_note, note_param)
        assert '<img src="img.png">' in mock_anki_note["Front"]
        assert '[sound:img.png]' in mock_anki_note["Back"]

    # Exception during addMedia appends escaped error message
    with mock.patch.object(ac, "storeMediaFile", side_effect=Exception("error <br> & test")):
        mock_anki_note = {"Front": "Q: "}
        ac.addMediaFromNote(
            mock_anki_note, {"picture": {"filename": "img.png", "fields": ["Front"]}}
        )
        assert "error &lt;br&gt; &amp; test" in mock_anki_note["Front"]


def test_update_note_variants(ac):
    with (
        mock.patch.object(ac, "updateNoteFields") as mock_up_fields,
        mock.patch.object(ac, "updateNoteTags") as mock_up_tags,
    ):
        ac.updateNote({"id": 1, "fields": {"Front": "A"}})
        mock_up_fields.assert_called_once()

        ac.updateNote({"id": 1, "tags": ["tag"]})
        mock_up_tags.assert_called_once()

        with pytest.raises(Exception, match='Must provide a "fields" or "tags" property'):
            ac.updateNote({"id": 1})


def test_update_note_model(ac):
    mock_col = mock.MagicMock()
    mock_model = {"id": 2, "name": "Advanced", "flds": [{"name": "Front"}, {"name": "Back"}]}
    mock_col.models.by_name.side_effect = lambda n: mock_model if n == "Advanced" else None
    mock_col.models.field_map.return_value = {}

    mock_note = mock.MagicMock()
    mock_col.get_note.return_value = mock_note

    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        # Validation checks
        with pytest.raises(ValueError, match="Note ID is required"):
            ac.updateNoteModel({})

        with pytest.raises(ValueError, match="Model name is required"):
            ac.updateNoteModel({"id": 1})

        with pytest.raises(ValueError, match="Fields must be provided as a dictionary"):
            ac.updateNoteModel({"id": 1, "modelName": "Advanced", "fields": []})

        with pytest.raises(ValueError, match="Model 'Missing' not found"):
            ac.updateNoteModel({"id": 1, "modelName": "Missing", "fields": {"Front": "X"}})

        # Valid update
        ac.updateNoteModel({"id": 1, "modelName": "Advanced", "fields": {"Front": "X"}})
        assert mock_note.mid == 2
        mock_col.update_note.assert_called_once_with(mock_note, skip_undo_entry=True)


def test_update_note_tags(ac):
    with (
        mock.patch.object(ac, "getNoteTags", return_value=["t1"]),
        mock.patch.object(ac, "removeTags") as mock_rem,
        mock.patch.object(ac, "addTags") as mock_add,
    ):
        ac.updateNoteTags(101, "t2")
        mock_rem.assert_called_once_with([101], "t1")
        mock_add.assert_called_once_with([101], "t2")

    with pytest.raises(Exception, match="Must provide tags as a list of strings"):
        ac.updateNoteTags(101, 123)


def test_replace_tags(ac):
    note1 = mock.MagicMock(tags=["old_tag"])
    note1.has_tag.side_effect = lambda t: t in note1.tags
    mock_col = mock.MagicMock()
    mock_col.get_note.side_effect = lambda nid: (
        note1 if nid == 1 else (_ for _ in ()).throw(anki.errors.NotFoundError("not found"))
    )
    mock_col.db.list.return_value = [1]
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        ac.replaceTags([1, 2], "old_tag", "new_tag")
        note1.remove_tag.assert_called_once_with("old_tag")
        note1.add_tag.assert_called_once_with("new_tag")

        note1.reset_mock()
        ac.replaceTagsInAllNotes("old_tag", "new_tag")
        note1.remove_tag.assert_called_once_with("old_tag")


def test_notes_info_and_mod_time_and_delete(ac):
    mock_note = mock.MagicMock(id=50, tags=["t1"], mod=12345)
    mock_model = {"name": "Basic", "flds": [{"ord": 0, "name": "Front"}]}
    mock_note.note_type.return_value = mock_model
    mock_note.fields = ["Question"]

    mock_col = mock.MagicMock()
    mock_col.get_note.side_effect = lambda nid: (
        mock_note if nid == 50 else (_ for _ in ()).throw(anki.errors.NotFoundError("not found"))
    )
    mock_col.db.all.return_value = [(101, 50)]
    mock_col.find_notes.return_value = [50]

    mock_m0 = {"id": 1}
    mock_col.models.all.return_value = [mock_m0]
    mock_col.models.use_count.return_value = 0

    mock_mw = mock.MagicMock(col=mock_col)
    mock_mw.pm.name = "User1"

    with mock.patch.object(aqt, "mw", mock_mw):
        with pytest.raises(Exception, match='Must provide either "notes" or a "query"'):
            ac.notesInfo()

        info = ac.notesInfo(query="deck:Default")
        assert len(info) == 1
        assert info[0]["noteId"] == 50
        assert info[0]["cards"] == [101]

        mod_time = ac.notesModTime([50, 99])
        assert mod_time == [{"noteId": 50, "mod": 12345}, {}]

        ac.deleteNotes([50])
        mock_col.remove_notes.assert_called_once_with([50])

        ac.removeEmptyNotes()
        mock_col.models.remove.assert_called_once_with(1)
        mock_mw.requireReset.assert_called_once()


def test_find_notes_and_cards(ac):
    mock_col = mock.MagicMock()
    mock_col.find_notes.return_value = ["50"]
    mock_col.find_cards.return_value = ["101"]
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.findNotes(None) == []
        assert ac.findNotes("tag:test") == [50]

        assert ac.findCards(None) == []
        assert ac.findCards("tag:test") == [101]


# --- Model Methods ---


def test_create_model_and_model_queries(ac):
    mock_col = mock.MagicMock()
    model_basic = {
        "id": 1,
        "name": "Basic",
        "css": "body {}",
        "flds": [{"name": "Front", "description": "Front field", "font": "Arial", "size": 12}],
        "tmpls": [{"name": "Card 1", "qfmt": "{{Front}}", "afmt": "{{Back}}"}],
    }
    m_basic = mock.MagicMock(id=1)
    m_basic.name = "Basic"
    mock_col.models.all_names_and_ids.return_value = [m_basic]
    mock_col.models.by_name.side_effect = lambda n: model_basic if n == "Basic" else None
    mock_col.models.get.side_effect = lambda mid: model_basic if mid == 1 else None
    mock_col.models.new.return_value = {"name": "NewModel", "tmpls": [], "flds": []}

    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.modelNames() == ["Basic"]
        assert ac.modelNamesAndIds() == {"Basic": 1}

        assert ac.findModelsById([1]) == [model_basic]
        with pytest.raises(Exception, match="model was not found"):
            ac.findModelsById([999])

        assert ac.findModelsByName(["Basic"]) == [model_basic]
        with pytest.raises(Exception, match="model was not found"):
            ac.findModelsByName(["Missing"])

        assert ac.modelNameFromId(1) == "Basic"
        with pytest.raises(Exception, match="model was not found"):
            ac.modelNameFromId(999)

        assert ac.modelFieldNames("Basic") == ["Front"]
        assert ac.modelFieldDescriptions("Basic") == ["Front field"]
        assert ac.modelFieldFonts("Basic") == {"Front": {"font": "Arial", "size": 12}}
        assert ac.modelFieldsOnTemplates("Basic") == {"Card 1": [["Front"], ["Back"]]}
        assert ac.modelTemplates("Basic") == {"Card 1": {"Front": "{{Front}}", "Back": "{{Back}}"}}
        assert ac.modelStyling("Basic") == {"css": "body {}"}

        # createModel validation
        with pytest.raises(Exception, match="Must provide at least one field"):
            ac.createModel("M", [], [{"Front": "a", "Back": "b"}])

        with pytest.raises(Exception, match="Must provide at least one card"):
            ac.createModel("M", ["f1"], [])

        with pytest.raises(Exception, match="Model name already exists"):
            ac.createModel("Basic", ["f1"], [{"Front": "a", "Back": "b"}])

        m = ac.createModel("NewModel", ["f1"], [{"Front": "a", "Back": "b"}], isCloze=True)
        assert m["name"] == "NewModel"


def test_model_field_and_template_modifications(ac):
    mock_col = mock.MagicMock()
    mock_model = {
        "id": 1,
        "name": "Basic",
        "css": "body { color: red; }",
        "flds": [{"name": "Front", "description": "desc"}],
        "tmpls": [{"name": "Card 1", "qfmt": "Q", "afmt": "A"}],
    }
    mock_col.models.allNames.return_value = ["Basic"]
    mock_col.models.by_name.side_effect = lambda n: mock_model if n == "Basic" else None
    mock_col.models.field_map.return_value = {"Front": (0, mock_model["flds"][0])}

    mock_mw = mock.MagicMock(col=mock_col)
    with mock.patch.object(aqt, "mw", mock_mw):
        ac.updateModelTemplates(
            {"name": "Basic", "templates": {"Card 1": {"Front": "Q2", "Back": "A2"}}}
        )
        assert mock_model["tmpls"][0]["qfmt"] == "Q2"

        ac.updateModelStyling({"name": "Basic", "css": "body { color: blue; }"})
        assert mock_model["css"] == "body { color: blue; }"

        replaced = ac.findAndReplaceInModels("Basic", "blue", "green")
        assert replaced == 1

        # findAndReplaceInModels across all models
        replaced_all = ac.findAndReplaceInModels(None, "green", "black")
        assert replaced_all == 1

        ac.modelTemplateRename("Basic", "Card 1", "Renamed Card")
        assert mock_model["tmpls"][0]["name"] == "Renamed Card"

        ac.modelTemplateReposition("Basic", "Renamed Card", 0)
        mock_col.models.reposition_template.assert_called_once()

        ac.modelTemplateAdd("Basic", {"Name": "Renamed Card", "Front": "QF", "Back": "AB"})
        assert mock_model["tmpls"][0]["qfmt"] == "QF"

        mock_col.models.new_template.return_value = {"name": "Card 2"}
        ac.modelTemplateAdd("Basic", {"Name": "Card 2", "Front": "QF2", "Back": "AB2"})
        mock_col.models.add_template.assert_called_once()

        ac.modelTemplateRemove("Basic", "Renamed Card")
        mock_col.models.remove_template.assert_called_once()

        ac.modelFieldRename("Basic", "Front", "FrontNew")
        fmap = {"FrontNew": (0, mock_model["flds"][0]), "Front": (0, mock_model["flds"][0])}
        mock_col.models.field_map.side_effect = lambda m: fmap
        mock_col.models.new_field.side_effect = lambda name: {"name": name}
        mock_col.models.addField.side_effect = lambda m, f: fmap.update({f["name"]: (1, f)})

        ac.modelFieldReposition("Basic", "FrontNew", 0)
        mock_col.models.reposition_field.assert_called_once()

        ac.modelFieldAdd("Basic", "NewFieldAdd", index=1)
        mock_col.models.addField.assert_called_once()

        ac.modelFieldRemove("Basic", "FrontNew")
        mock_col.models.remove_field.assert_called_once()

        ac.modelFieldSetFont("Basic", "FrontNew", "Helvetica")
        ac.modelFieldSetFontSize("Basic", "FrontNew", 16)
        assert ac.modelFieldSetDescription("Basic", "FrontNew", "New Desc") is True

        # Field description absent branch
        mock_model["flds"][0].pop("description")
        assert ac.modelFieldSetDescription("Basic", "FrontNew", "New Desc") is False

        with pytest.raises(Exception, match="font should be a string"):
            ac.modelFieldSetFont("Basic", "FrontNew", 123)

        with pytest.raises(Exception, match="fontSize should be an integer"):
            ac.modelFieldSetFontSize("Basic", "FrontNew", "16")

        with pytest.raises(Exception, match="description should be a string"):
            ac.modelFieldSetDescription("Basic", "FrontNew", None)


# --- Media Operations ---


def test_media_file_operations(ac):
    mock_media = mock.MagicMock()
    mock_media.writeData.return_value = "saved.png"
    mock_media.dir.return_value = "/media/dir"
    mock_col = mock.MagicMock(media=mock_media)
    mock_mw = mock.MagicMock(col=mock_col)

    b64_str = base64.b64encode(b"test data").decode("utf-8")

    with mock.patch.object(aqt, "mw", mock_mw):
        with pytest.raises(Exception, match='You must provide a "data", "path", or "url" field.'):
            ac.storeMediaFile("file.png")

        res_data = ac.storeMediaFile("file.png", data=b64_str)
        assert res_data == "saved.png"

        with mock.patch("builtins.open", mock.mock_open(read_data=b"test data")):
            res_path = ac.storeMediaFile("file.png", path="/tmp/file.png")
            assert res_path == "saved.png"

        with mock.patch.object(util, "download", return_value=b"test data"):
            res_url = ac.storeMediaFile("file.png", url="http://example.com/file.png")
            assert res_url == "saved.png"

        # skipHash match
        with mock.patch.object(ac, "deleteMediaFile") as mock_del:
            import hashlib

            md5_hash = hashlib.md5(b"test data", usedforsecurity=False).hexdigest()
            res_skip = ac.storeMediaFile("file.png", data=b64_str, skipHash=md5_hash)
            assert res_skip is None
            mock_del.assert_not_called()

        assert ac.getMediaDirPath() == "/media/dir"

        with (
            mock.patch("os.path.exists", return_value=True),
            mock.patch("builtins.open", mock.mock_open(read_data=b"test data")),
        ):
            assert ac.retrieveMediaFile("file.png") == b64_str

        with mock.patch("glob.glob", return_value=["/media/dir/a.png"]):
            assert ac.getMediaFilesNames("*.png") == ["a.png"]

        ac.deleteMediaFile("a.png")
        mock_media.trash_files.assert_called_with(["a.png"])


# --- Exporter & Importer ---


def test_export_and_import_package(ac):
    mock_col = mock.MagicMock()
    mock_col.decks.by_name.side_effect = lambda n: {"id": 1} if n == "Default" else None
    mock_mw = mock.MagicMock(col=mock_col)

    with (
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch("anki_connect.AnkiPackageExporter") as mock_exporter,
        mock.patch("anki_connect.AnkiPackageImporter") as mock_importer,
        mock.patch.object(ac, "startEditing"),
    ):
        assert ac.exportPackage("Default", "/tmp/deck.apkg") is True
        mock_exporter.return_value.exportInto.assert_called_once_with("/tmp/deck.apkg")

        assert ac.exportPackage("Missing", "/tmp/deck.apkg") is False

        assert ac.importPackage("/tmp/deck.apkg") is True
        mock_importer.return_value.run.assert_called_once()

        mock_importer.side_effect = Exception("import err")
        with pytest.raises(Exception, match="import err"):
            ac.importPackage("/tmp/deck.apkg")


# --- Stats & Miscellaneous ---


def test_stats_and_misc(ac):
    mock_col = mock.MagicMock()
    mock_col.db.scalar.return_value = 10
    mock_col.db.all.return_value = [("2026-08-07", 10)]
    mock_col.stats.return_value.report.return_value = "<html>Stats</html>"
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.version() == 6
        assert ac.getNumCardsReviewedToday() == 10
        assert ac.getNumCardsReviewedByDay() == [("2026-08-07", 10)]
        assert ac.getCollectionStatsHTML() == "<html>Stats</html>"

        ac.reloadCollection()
        mock_col.reset.assert_called_once()

        res_reflect = ac.apiReflect(scopes=["actions"])
        assert "actions" in res_reflect["scopes"]
        assert "version" in res_reflect["actions"]

        with pytest.raises(Exception, match="scopes has invalid value"):
            ac.apiReflect(scopes="not_a_list")

        with pytest.raises(Exception, match="actions has invalid value"):
            ac.apiReflect(scopes=["actions"], actions="not_a_list")


def test_sync(ac):
    mock_mw = mock.MagicMock()
    mock_auth = mock.MagicMock()
    mock_mw.pm.sync_auth.return_value = mock_auth
    mock_mw.pm.media_syncing_enabled.return_value = True

    mock_out = mock.MagicMock()
    mock_out.required = "NO_CHANGES"
    mock_out.NO_CHANGES = "NO_CHANGES"
    mock_out.NORMAL_SYNC = "NORMAL_SYNC"
    mock_col = mock.MagicMock()
    mock_col.sync_collection.return_value = mock_out
    mock_mw.col = mock_col

    with mock.patch.object(aqt, "mw", mock_mw):
        ac.sync()
        mock_mw.onSync.assert_called_once()

        # Auth missing
        mock_mw.pm.sync_auth.return_value = None
        with pytest.raises(Exception, match="auth not configured"):
            ac.sync()

        # Status unaccepted
        mock_mw.pm.sync_auth.return_value = mock_auth
        mock_out.required = "FULL_SYNC"
        with pytest.raises(Exception, match="Sync status FULL_SYNC not one of"):
            ac.sync()


def test_request_permission(ac):
    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: (
            [] if k == "ignoreOriginList" else (6 if k == "apiVersion" else "key")
        ),
    ):
        res_allowed = ac.requestPermission("http://localhost", True)
        assert res_allowed["permission"] == "granted"

    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: ["http://ignored.com"] if k == "ignoreOriginList" else 6,
    ):
        res_denied = ac.requestPermission("http://ignored.com", False)
        assert res_denied["permission"] == "denied"

    # Prompt user - Yes button
    yes_btn = 1
    no_btn = 2
    mock_msg = mock.MagicMock()
    mock_msg.exec.return_value = yes_btn
    std_btn_mock = mock.MagicMock()
    std_btn_mock.Yes = yes_btn
    std_btn_mock.No = no_btn

    import anki_connect

    with (
        mock.patch("anki_connect.QMessageBox", return_value=mock_msg),
        mock.patch.object(anki_connect.QMessageBox, "StandardButton", std_btn_mock),
        mock.patch.object(
            util,
            "setting",
            side_effect=lambda k: [] if k in ("ignoreOriginList", "webCorsOriginList") else 6,
        ),
        mock.patch.object(aqt.mw.addonManager, "getConfig", return_value={"webCorsOriginList": []}),
        mock.patch.object(aqt.mw.addonManager, "writeConfig") as mock_write_cfg,
    ):
        res_yes = ac.requestPermission("http://app.com", False)
        assert res_yes["permission"] == "granted"
        mock_write_cfg.assert_called_once()

    # Prompt user - No button + ignore checkbox
    mock_msg.exec.return_value = no_btn
    mock_msg.checkBox().isChecked.return_value = True
    with (
        mock.patch("anki_connect.QMessageBox", return_value=mock_msg),
        mock.patch.object(anki_connect.QMessageBox, "StandardButton", std_btn_mock),
        mock.patch.object(
            util,
            "setting",
            side_effect=lambda k: [] if k in ("ignoreOriginList", "webCorsOriginList") else 6,
        ),
        mock.patch.object(aqt.mw.addonManager, "getConfig", return_value={"ignoreOriginList": []}),
        mock.patch.object(aqt.mw.addonManager, "writeConfig") as mock_write_cfg,
    ):
        res_no = ac.requestPermission("http://app.com", False)
        assert res_no["permission"] == "denied"
        mock_write_cfg.assert_called_once()


# --- GUI Methods ---


def test_gui_methods(ac):
    mock_mw = mock.MagicMock()
    mock_mw.pm.profiles.return_value = ["User1", "User2"]
    mock_mw.pm.name = "User1"

    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.getProfiles() == ["User1", "User2"]
        assert ac.getActiveProfile() == "User1"
        assert ac.loadProfile("NonExistent") is False
        assert ac.loadProfile("User1") is True

        ac.guiEditNote(101)
        assert ac.guiUndo() is True
        ac.guiDeckBrowser()
        mock_mw.moveToState.assert_called_with("deckBrowser")

        assert ac.guiCheckDatabase() is True
        mock_mw.onCheckDB.assert_called_once()


def test_gui_browse_and_selection(ac):
    mock_browser = mock.MagicMock()
    dict_dialogs = {"Browser": (None, mock_browser)}

    with (
        mock.patch.object(aqt.dialogs, "open", return_value=mock_browser),
        mock.patch.object(aqt.dialogs, "_dialogs", dict_dialogs),
        mock.patch.object(ac, "findCards", return_value=[101]),
    ):
        res = ac.guiBrowse(
            query="deck:Default", reorderCards={"columnId": "card", "order": "descending"}
        )
        assert res == [101]

        ac.guiSelectNote(101)
        mock_browser.table.select_single_card.assert_called_with(101)

        mock_browser.selectedNotes.return_value = [50]
        assert ac.guiSelectedNotes() == [50]

        # Invalid reorderCards options
        with pytest.raises(Exception, match="reorderCards should be a dict"):
            ac.guiBrowse(reorderCards="invalid")

        with pytest.raises(Exception, match='Must provide a "columnId" and a "order" property'):
            ac.guiBrowse(reorderCards={"columnId": "card"})

        with pytest.raises(Exception, match="invalid card order"):
            ac.guiBrowse(reorderCards={"columnId": "card", "order": "invalid"})

        mock_browser.table._model.active_column_index.return_value = None
        with pytest.raises(Exception, match="invalid columnId"):
            ac.guiBrowse(reorderCards={"columnId": "invalid", "order": "ascending"})


def test_gui_add_cards(ac):
    mock_addcards = mock.MagicMock()
    mock_addcards.editor.note.id = 50
    mock_col = mock.MagicMock()
    mock_col.decks.by_name.side_effect = lambda n: {"id": 1} if n == "Default" else None
    mock_col.models.by_name.side_effect = lambda n: {"id": 1} if n == "Basic" else None
    dict_dialogs = {"AddCards": (None, None)}
    mock_mw = mock.MagicMock(col=mock_col)

    with (
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch.object(aqt.dialogs, "open", return_value=mock_addcards),
        mock.patch.object(aqt.dialogs, "_dialogs", dict_dialogs),
    ):
        assert ac.guiAddCards() == 50

        nid = ac.guiAddCards(
            {"deckName": "Default", "modelName": "Basic", "fields": {"Front": "Q"}, "tags": ["t1"]}
        )
        assert isinstance(nid, mock.MagicMock)

        # Validation errors
        with pytest.raises(Exception, match="deck was not found"):
            ac.guiAddCards({"deckName": "Missing", "modelName": "Basic"})

        with pytest.raises(Exception, match="model was not found"):
            ac.guiAddCards({"deckName": "Default", "modelName": "Missing"})


def test_gui_deck_overview_and_review(ac):
    mock_col = mock.MagicMock()
    mock_col.decks.by_name.side_effect = lambda n: {"id": 1} if n == "Default" else None
    mock_mw = mock.MagicMock(col=mock_col)

    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.guiDeckOverview("Default") is True
        mock_col.decks.select.assert_called_once_with(1)

        assert ac.guiDeckReview("Default") is True
        mock_mw.moveToState.assert_called_with("review")

        assert ac.guiDeckReview("Missing") is False


def test_gui_review_actions(ac):
    mock_card = mock.MagicMock(id=101, ord=0, did=1)
    mock_model = {"name": "Basic", "css": "body {}", "flds": [{"ord": 0, "name": "Front"}]}
    mock_note = mock.MagicMock()
    mock_note.fields = ["FrontText"]

    mock_card.note_type.return_value = mock_model
    mock_card.note.return_value = mock_note
    mock_card.template.return_value = {"name": "Card 1"}

    mock_reviewer = mock.MagicMock()
    mock_reviewer.card = mock_card
    mock_reviewer._answerButtonList.return_value = [(1, "Again"), (2, "Good")]
    mock_reviewer.state = "answer"

    mock_col = mock.MagicMock()
    mock_col.decks.get.return_value = {"name": "Default"}
    mock_col.sched.nextIvlStr.return_value = "1d"
    mock_mw = mock.MagicMock(reviewer=mock_reviewer, state="review", col=mock_col)

    with (
        mock.patch.object(aqt, "mw", mock_mw),
        mock.patch("anki_connect.util.cardQuestion", return_value="Q"),
        mock.patch("anki_connect.util.cardAnswer", return_value="A"),
    ):
        assert ac.guiReviewActive() is True

        curr = ac.guiCurrentCard()
        assert curr["cardId"] == 101
        assert curr["buttons"] == [1, 2]

        assert ac.guiStartCardTimer() is True
        mock_card.startTimer.assert_called_once()

        assert ac.guiShowQuestion() is True
        mock_reviewer._showQuestion.assert_called_once()

        assert ac.guiShowAnswer() is True
        mock_reviewer._showAnswer.assert_called_once()

        mock_col.sched.answerButtons.return_value = 4
        assert ac.guiAnswerCard(2) is True
        mock_reviewer._answerCard.assert_called_once_with(2)

        assert ac.guiAnswerCard(5) is False  # ease out of bounds

        assert ac.guiPlayAudio() is True
        mock_reviewer.replayAudio.assert_called_once()

    # Reviewer inactive cases
    mock_mw.state = "deckBrowser"
    with mock.patch.object(aqt, "mw", mock_mw):
        assert ac.guiReviewActive() is False
        assert ac.guiStartCardTimer() is False
        assert ac.guiShowQuestion() is False
        assert ac.guiShowAnswer() is False
        assert ac.guiAnswerCard(2) is False
        assert ac.guiPlayAudio() is False

        with pytest.raises(Exception, match="Gui review is not currently active"):
            ac.guiCurrentCard()


def test_gui_import_file(ac):
    with (
        mock.patch("aqt.import_export.importing.import_file") as mock_imp_file,
        mock.patch("aqt.import_export.importing.prompt_for_file_then_import") as mock_prompt_imp,
        mock.patch.object(ac, "window", return_value=mock.MagicMock()),
    ):
        ac.guiImportFile("/tmp/file.txt")
        mock_imp_file.assert_called_once()

        ac.guiImportFile(None)
        mock_prompt_imp.assert_called_once()
