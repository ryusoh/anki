from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from auto_itaigi.utils import (
    download_audio,
    hapsing_url,
    itaigi_lookup_url,
    media_filename,
    save_audio_to_media,
)


def test_media_filename_first_variant():
    assert media_filename("han-tsî/han-tsû") == "itaigi_han-tsi.mp3"


def test_media_filename_ascii_normalization():
    assert media_filename("pû-han-tsî/pû-huan-tsû") == "itaigi_pu-han-tsi.mp3"


def test_media_filename_empty_slug_fallback():
    assert media_filename("///") == "itaigi_audio.mp3"


def test_hapsing_url_is_ascii_and_replaces_first_slash():
    url = hapsing_url("han-tsî/han-tsû")
    assert url.isascii()
    parsed = urlparse(url)
    assert "/" not in parsed.query
    taibun = parse_qs(parsed.query)["taibun"][0]
    assert " 。 " in taibun


def test_itaigi_lookup_url_is_ascii():
    url = itaigi_lookup_url("番薯")
    assert url.isascii()
    assert "itaigi.tw" in url
    assert "關鍵字" not in url


def _mock_urlopen_context(resp):
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = resp
    return mock_urlopen


def test_download_audio_returns_mp3_bytes():
    mp3 = b"\xff\xfb" + b"x" * 3031
    mock_resp = MagicMock()
    mock_resp.read.return_value = mp3
    with patch(
        "auto_itaigi.utils.urlopen_with_proxy_fallback",
        new=_mock_urlopen_context(mock_resp),
    ):
        assert download_audio("han-tsî") == mp3


def test_download_audio_rejects_non_mp3():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<html>not mp3</html>"
    with patch(
        "auto_itaigi.utils.urlopen_with_proxy_fallback",
        new=_mock_urlopen_context(mock_resp),
    ):
        assert download_audio("han-tsî") is None


def test_download_audio_catches_exception():
    with patch(
        "auto_itaigi.utils.urlopen_with_proxy_fallback",
        side_effect=OSError("network"),
    ):
        assert download_audio("han-tsî") is None


def test_save_audio_to_media_writes_and_returns_filename():
    mp3 = b"\xff\xfb" + b"x" * 3031
    mock_mw = MagicMock()
    mock_mw.col.media.write_data.return_value = None
    with patch("auto_itaigi.utils.download_audio", return_value=mp3):
        sys.modules["aqt"].mw = mock_mw
        try:
            assert save_audio_to_media("han-tsî/han-tsû") == "itaigi_han-tsi.mp3"
            mock_mw.col.media.write_data.assert_called_once_with("itaigi_han-tsi.mp3", mp3)
        finally:
            del sys.modules["aqt"].mw


def test_save_audio_to_media_returns_none_when_write_fails():
    mp3 = b"\xff\xfb" + b"x" * 3031
    mock_mw = MagicMock()
    mock_mw.col.media.write_data.side_effect = Exception("boom")
    with patch("auto_itaigi.utils.download_audio", return_value=mp3):
        sys.modules["aqt"].mw = mock_mw
        try:
            assert save_audio_to_media("han-tsî/han-tsû") is None
        finally:
            del sys.modules["aqt"].mw
