import sys
import unittest.mock as mock
import pytest

from anki_connect import util


def test_media_type_enum():
    assert util.MediaType.Audio.value == 1
    assert util.MediaType.Video.value == 2
    assert util.MediaType.Picture.value == 3


def test_download_success():
    mock_client = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_client.get.return_value = mock_resp
    mock_client.streamContent.return_value = b"test content"

    with (
        mock.patch("sys.modules", sys.modules),
        mock.patch.object(util.anki.sync, "AnkiRequestsClient", return_value=mock_client),
    ):
        res = util.download("http://example.com/file.mp3")
        assert res == b"test content"


def test_download_failure():
    mock_client = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 404
    mock_client.get.return_value = mock_resp

    with mock.patch.object(util.anki.sync, "AnkiRequestsClient", return_value=mock_client):
        with pytest.raises(Exception, match="404"):
            util.download("http://example.com/missing.mp3")


def test_api_decorator():
    @util.api(1, 2, 3)
    def dummy_func():
        pass

    assert dummy_func.api is True
    assert dummy_func.versions == (1, 2, 3)


def test_card_question():
    card_with_method = mock.MagicMock()
    card_with_method.question.return_value = "Question text"
    assert util.cardQuestion(card_with_method) == "Question text"

    card_without_method = mock.MagicMock(spec=["_getQA"])
    card_without_method._getQA.return_value = {"q": "QA Question"}
    assert util.cardQuestion(card_without_method) == "QA Question"


def test_card_answer():
    card_with_method = mock.MagicMock()
    card_with_method.answer.return_value = "Answer text"
    assert util.cardAnswer(card_with_method) == "Answer text"

    card_without_method = mock.MagicMock(spec=["_getQA"])
    card_without_method._getQA.return_value = {"a": "QA Answer"}
    assert util.cardAnswer(card_without_method) == "QA Answer"


def test_setting():
    mock_config_manager = mock.MagicMock()
    mock_config_manager.getConfig.return_value = {"webBindPort": 9999}
    with mock.patch("aqt.mw.addonManager", mock_config_manager):
        assert util.setting("webBindPort") == 9999
        assert util.setting("apiVersion") == 6

    mock_config_manager.getConfig.side_effect = Exception("config error")
    with mock.patch("aqt.mw.addonManager", mock_config_manager):
        with pytest.raises(Exception, match="setting non_existent_key not found"):
            util.setting("non_existent_key")


def test_patch_null_stdout():
    orig_stdout = sys.stdout
    try:
        sys.stdout = None
        util.patch_anki_2_1_50_having_null_stdout_on_windows()
        assert sys.stdout is not None
    finally:
        sys.stdout = orig_stdout


def test_batched():
    items = [1, 2, 3, 4, 5]
    batches = list(util.batched(items, 2))
    assert batches == [(1, 2), (3, 4), (5,)]
