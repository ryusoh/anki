import urllib.request
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from auto_wiktionary.proxy_fallback import _detect_local_proxy, urlopen_with_proxy_fallback


def test_detect_local_proxy_oserror():
    with patch('socket.create_connection', side_effect=OSError):
        assert _detect_local_proxy([1234]) is None


def test_urlopen_with_proxy_fallback_httperror_direct():
    req = urllib.request.Request('http://example.com')
    with patch('urllib.request.urlopen', side_effect=HTTPError('url', 404, 'Not Found', {}, None)):
        try:
            urlopen_with_proxy_fallback(req)
        except HTTPError:
            pass
        else:
            raise AssertionError("Should raise HTTPError")


def test_urlopen_with_proxy_fallback_httperror_proxy():
    req = urllib.request.Request('http://example.com')
    import auto_wiktionary.proxy_fallback as proxy_fallback

    proxy_fallback._proxy_opener = MagicMock()
    proxy_fallback._proxy_opener.open.side_effect = HTTPError('url', 404, 'Not Found', {}, None)
    try:
        urlopen_with_proxy_fallback(req)
    except HTTPError:
        pass
    else:
        raise AssertionError("Should raise HTTPError")
    finally:
        proxy_fallback._proxy_opener = None
