import json
from unittest.mock import MagicMock, patch

import pytest

import auto_itaigi.utils
from auto_itaigi.utils import (
    download_audio,
    fetch_chhoetaigi_entry,
    fetch_moedict_entry,
    media_filename,
)


def test_fetch_chhoetaigi_entry_success():
    auto_itaigi.utils._chhoetaigi_cache = None
    mock_csv = "HoaBun,KipUnicode,HanLoTaibunKip\n你好,liho,你好\n"

    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = mock_csv.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_chhoetaigi_entry("你好")
        assert result == ("liho", ["你好"])

def test_fetch_chhoetaigi_entry_exception():
    auto_itaigi.utils._chhoetaigi_cache = None
    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback', side_effect=Exception("Test error")):
        result = fetch_chhoetaigi_entry("你好")
        assert result is None

def test_fetch_moedict_entry_success():
    data = {
        "h": [
            {
                "T": "tailo1",
                "_": "audio123",
                "d": [
                    {"f": "definition 1"},
                    {"f": "`definition 2~"}
                ]
            }
        ]
    }

    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_moedict_entry("word")
        assert result == ("tailo1", ["definition 1", "definition 2"], "https://r2-assets.moedict.tw/audio/t/audio123.mp3")

def test_fetch_moedict_entry_empty_h():
    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"h": []}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_moedict_entry("word")
        assert result is None

def test_fetch_moedict_entry_empty_tailo_and_mandarin():
    data = {
        "h": [
            {
                "T": "",
                "d": []
            }
        ]
    }
    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_moedict_entry("word")
        assert result is None

def test_download_audio_success_with_fallback():
    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'ID3_test_audio'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = download_audio("tailo", fallback_url="http://fallback.com")
        assert result == b'ID3_test_audio'
        assert mock_urlopen.call_count == 1

def test_download_audio_failure_continue():
    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback', side_effect=Exception("Test error")) as mock_urlopen:
        result = download_audio("tailo", fallback_url="http://fallback.com")
        assert result is None
        assert mock_urlopen.call_count == 2

def test_media_filename():
    assert media_filename("laha") == "itaigi_laha.mp3"

def test_fetch_moedict_entry_duplicate_mandarin():
    data = {
        "h": [
            {
                "T": "tailo1",
                "_": "audio123",
                "d": [
                    {"f": "definition 1"},
                    {"f": "definition 1"}
                ]
            }
        ]
    }

    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_moedict_entry("word")
        assert result == ("tailo1", ["definition 1"], "https://r2-assets.moedict.tw/audio/t/audio123.mp3")

def test_fetch_chhoetaigi_entry_empty_hoabun():
    auto_itaigi.utils._chhoetaigi_cache = None
    mock_csv = "HoaBun,KipUnicode,HanLoTaibunKip\n,liho,你好\n你好,liho,你好\n"

    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = mock_csv.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_chhoetaigi_entry("你好")
        assert result == ("liho", ["你好"])

def test_fetch_chhoetaigi_entry_use_cache():
    auto_itaigi.utils._chhoetaigi_cache = {"你好": ("liho", ["你好"])}
    result = fetch_chhoetaigi_entry("你好")
    assert result == ("liho", ["你好"])
