from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from auto_itaigi.utils import (
    fetch_chhoetaigi_entry,
    fetch_itaigi_json,
    fetch_moedict_entry,
    lookup_itaigi,
)


def _make_response(body: bytes) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = body
    return resp


def test_fetch_itaigi_json_returns_body():
    body = '{"列表": []}'.encode("utf-8")
    mock_resp = _make_response(body)
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    with patch(
        "auto_itaigi.utils.urlopen_with_proxy_fallback",
        new=mock_urlopen,
    ):
        result = fetch_itaigi_json("番薯")
        assert result == '{"列表": []}'
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url.isascii()
        assert req.headers.get("User-agent", "").startswith("AnkiAutoItaigi")


def test_fetch_itaigi_json_404_returns_empty():
    error = HTTPError(
        url="http://example.com",
        code=404,
        msg="Not Found",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,  # type: ignore[arg-type]
    )
    with patch(
        "auto_itaigi.utils.urlopen_with_proxy_fallback",
        side_effect=error,
    ):
        assert fetch_itaigi_json("番薯") == ""


def test_fetch_itaigi_json_http_error_returns_code():
    error = HTTPError(
        url="http://example.com",
        code=500,
        msg="Server Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,  # type: ignore[arg-type]
    )
    with patch(
        "auto_itaigi.utils.urlopen_with_proxy_fallback",
        side_effect=error,
    ):
        assert fetch_itaigi_json("番薯") == "Error: 500"


def test_fetch_itaigi_json_url_error_returns_network():
    with patch(
        "auto_itaigi.utils.urlopen_with_proxy_fallback",
        side_effect=URLError("no route"),
    ):
        assert fetch_itaigi_json("番薯") == "Error: Network connection failed."


def test_fetch_moedict_entry_success():
    body = '{"h": [{"T": "han-tsî/han-tsû", "_": "8782", "d": [{"f": "`地~`瓜~"}]}]}'.encode(
        "utf-8"
    )
    mock_resp = _make_response(body)
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    with patch("auto_itaigi.utils.urlopen_with_proxy_fallback", new=mock_urlopen):
        res = fetch_moedict_entry("番薯")
        assert res == ("han-tsî/han-tsû", ["地瓜"], "https://r2-assets.moedict.tw/audio/t/8782.mp3")


def test_fetch_moedict_entry_failure():
    with patch("auto_itaigi.utils.urlopen_with_proxy_fallback", side_effect=Exception("error")):
        assert fetch_moedict_entry("unknown") is None


def test_fetch_chhoetaigi_entry_success():
    csv_data = 'HoaBun,KipUnicode,HanLoTaibunKip\n番薯,han-tsî,蕃薯\n'.encode("utf-8")
    mock_resp = _make_response(csv_data)
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    with patch("auto_itaigi.utils.urlopen_with_proxy_fallback", new=mock_urlopen):
        with patch("auto_itaigi.utils._chhoetaigi_cache", None):
            res = fetch_chhoetaigi_entry("番薯")
            assert res == ("han-tsî", ["蕃薯"])


def test_lookup_itaigi_tier1_success():
    fixture = '{"列表": [{"新詞文本": [{"文本資料": "番薯", "音標資料": "han-tsî", "按呢講的外語列表": [{"外語資料": "地瓜"}]}]}]}'
    with (
        patch("auto_itaigi.utils.fetch_itaigi_json", return_value=fixture),
        patch("auto_itaigi.utils.fetch_moedict_entry") as mock_moe,
    ):
        res = lookup_itaigi("番薯")
        assert res == ("han-tsî", ["地瓜"], None)
        assert not mock_moe.called


def test_lookup_itaigi_tier1_fail_tier2_success():
    with (
        patch("auto_itaigi.utils.fetch_itaigi_json", return_value="Error: 500"),
        patch(
            "auto_itaigi.utils.fetch_moedict_entry",
            return_value=("han-tsî", ["地瓜"], "https://r2-assets.moedict.tw/audio/t/8782.mp3"),
        ),
        patch("auto_itaigi.utils.fetch_chhoetaigi_entry") as mock_chhoe,
    ):
        res = lookup_itaigi("番薯")
        assert res == ("han-tsî", ["地瓜"], "https://r2-assets.moedict.tw/audio/t/8782.mp3")
        assert not mock_chhoe.called


def test_lookup_itaigi_tier1_2_fail_tier3_success():
    with (
        patch("auto_itaigi.utils.fetch_itaigi_json", return_value="Error: 500"),
        patch("auto_itaigi.utils.fetch_moedict_entry", return_value=None),
        patch("auto_itaigi.utils.fetch_chhoetaigi_entry", return_value=("han-tsî", ["蕃薯"])),
    ):
        res = lookup_itaigi("番薯")
        assert res == ("han-tsî", ["蕃薯"], None)
