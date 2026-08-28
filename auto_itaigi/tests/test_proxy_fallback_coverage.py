import urllib.request
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from auto_itaigi.proxy_fallback import _detect_local_proxy, urlopen_with_proxy_fallback


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
    import auto_itaigi.proxy_fallback as proxy_fallback

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


def test_detect_local_proxy_sources_env():
    import os

    # line 52-58: checking os.environ for proxy
    with patch.dict(os.environ, {"HTTP_PROXY": "127.0.0.1:8080"}):
        # mock create_connection to return success for 8080
        def fake_create_connection(address, timeout=None):
            if address[1] == 8080:
                mock_sock = MagicMock()
                mock_sock.recv.return_value = b"HTTP/1.1 200 OK"
                mock_sock.__enter__.return_value = mock_sock
                return mock_sock
            raise OSError

        with patch('socket.create_connection', fake_create_connection):
            assert _detect_local_proxy() == "http://127.0.0.1:8080"


def test_detect_local_proxy_socket_send_oserror():
    # line 71-73: s.sendall raises OSError but socket is connected
    def fake_create_connection(address, timeout=None):
        if address[1] == 7897:  # First default port
            mock_sock = MagicMock()
            mock_sock.sendall.side_effect = OSError
            mock_sock.__enter__.return_value = mock_sock
            return mock_sock
        raise OSError

    with patch('socket.create_connection', fake_create_connection):
        assert _detect_local_proxy() == "http://127.0.0.1:7897"


def test_urlopen_with_proxy_fallback_direct_opener_httperror():
    req = urllib.request.Request('http://example.com')
    # mock urlopen to raise OSError (direct fails)
    # mock _build_direct_opener().open to raise HTTPError

    mock_opener = MagicMock()
    mock_opener.open.side_effect = HTTPError('url', 404, 'Not Found', {}, None)

    with patch('urllib.request.urlopen', side_effect=OSError):
        with patch('auto_itaigi.proxy_fallback._build_direct_opener', return_value=mock_opener):
            try:
                urlopen_with_proxy_fallback(req)
            except HTTPError:
                pass
            else:
                raise AssertionError("Should raise HTTPError")


def test_build_direct_opener():
    from auto_itaigi.proxy_fallback import _build_direct_opener

    opener = _build_direct_opener()
    assert opener is not None
