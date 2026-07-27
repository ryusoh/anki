from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from auto_itaigi.utils import fetch_itaigi_json


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
