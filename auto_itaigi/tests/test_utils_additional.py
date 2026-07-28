import json
import urllib.request
from unittest.mock import patch

import pytest

from auto_itaigi.utils import fetch_itaigi_json, parse_itaigi_json, save_audio_to_media


def test_parse_itaigi_json_fallback_loop():
    data = {
        "其他建議": [
            {"文本資料": "no match 1"},
            {"文本資料": "no match 2"},
        ]
    }
    result = parse_itaigi_json(json.dumps(data), "query")
    assert result is None


def test_save_audio_to_media_none():
    with patch('auto_itaigi.utils.download_audio', return_value=None):
        assert save_audio_to_media("tailo") is None


def test_fetch_itaigi_json_exception():
    with patch('auto_itaigi.utils.urlopen_with_proxy_fallback', side_effect=Exception("Test Error")):
        result = fetch_itaigi_json("word")
        assert result == "Error: Test Error"
