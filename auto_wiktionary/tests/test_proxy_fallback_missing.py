import socket
from unittest.mock import MagicMock, patch

import pytest

from auto_wiktionary.proxy_fallback import _detect_local_proxy


def test_detect_local_proxy_oserror_on_sendall():
    with patch('socket.create_connection') as mock_conn:
        mock_sock = MagicMock()
        mock_sock.sendall.side_effect = OSError("Test error")
        mock_conn.return_value.__enter__.return_value = mock_sock

        result = _detect_local_proxy(ports=[1234])
        assert result == "http://127.0.0.1:1234"

def test_detect_local_proxy_http_success():
    with patch('socket.create_connection') as mock_conn:
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'HTTP/1.1 200 OK'
        mock_conn.return_value.__enter__.return_value = mock_sock

        result = _detect_local_proxy(ports=[1234])
        assert result == "http://127.0.0.1:1234"
