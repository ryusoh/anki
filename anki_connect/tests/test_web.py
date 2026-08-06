import json
import socket
import unittest.mock as mock
import pytest

from anki_connect import web, util


def test_web_request_init():
    req = web.WebRequest("POST", {"content-type": "application/json"}, b'{"action": "version"}')
    assert req.method == "POST"
    assert req.headers["content-type"] == "application/json"
    assert req.body == b'{"action": "version"}'


def test_web_client_parse_request():
    client = web.WebClient(None, None)

    # Incomplete header
    req, length = client.parseRequest(b"POST / HTTP/1.1\r\nHost: localhost")
    assert req is None
    assert length == 0

    # Complete request with body
    body_data = json.dumps({"action": "version"}).encode("utf-8")
    raw_http = (
        f"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body_data)}\r\n\r\n".encode(
            "utf-8"
        )
        + body_data
    )
    req, length = client.parseRequest(raw_http)
    assert req is not None
    assert req.method == b"POST"
    assert req.headers[b"host"] == b"localhost"
    assert req.body == body_data
    assert length == len(raw_http)

    # Incomplete body
    raw_http_short = (
        f"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body_data) + 10}\r\n\r\n".encode(
            "utf-8"
        )
        + body_data
    )
    req, length = client.parseRequest(raw_http_short)
    assert req is None
    assert length == 0


def test_web_client_advance_read_and_write():
    mock_sock = mock.MagicMock()
    handler = mock.MagicMock(return_value=b"HTTP/1.1 200 OK\r\n\r\nOK")
    client = web.WebClient(mock_sock, handler)

    body_data = json.dumps({"action": "version"}).encode("utf-8")
    raw_http = (
        f"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body_data)}\r\n\r\n".encode(
            "utf-8"
        )
        + body_data
    )

    mock_sock.recv.return_value = raw_http
    mock_sock.send.side_effect = lambda b: len(b)

    with mock.patch("select.select", return_value=([mock_sock], [mock_sock], [])):
        res = client.advance()
        assert res is False  # Closed after write completed
        mock_sock.recv.assert_called()
        mock_sock.send.assert_called()


def test_web_client_advance_none_socket():
    client = web.WebClient(None, None)
    assert client.advance() is False


def test_web_client_advance_recv_error():
    mock_sock = mock.MagicMock()
    client = web.WebClient(mock_sock, None)
    mock_sock.recv.side_effect = ConnectionResetError

    with mock.patch("select.select", return_value=([mock_sock], [], [])):
        assert client.advance() is False
        assert client.sock is None


def test_web_server_allow_origin():
    server = web.WebServer(None)

    # Test default localhost setting
    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: ["http://localhost"] if k == "webCorsOriginList" else None,
    ):
        req_local = web.WebRequest("POST", {b"origin": b"http://localhost"}, b"")
        allowed, cors = server.allowOrigin(req_local)
        assert allowed is True
        assert cors == "http://localhost"

        req_127 = web.WebRequest("POST", {b"origin": b"http://127.0.0.1:8765"}, b"")
        allowed, cors = server.allowOrigin(req_127)
        assert allowed is True
        assert cors == "http://127.0.0.1:8765"

        req_chrome = web.WebRequest("POST", {b"origin": b"chrome-extension://abc"}, b"")
        allowed, cors = server.allowOrigin(req_chrome)
        assert allowed is True

        req_disallowed = web.WebRequest("POST", {b"origin": b"http://evil.com"}, b"")
        allowed, cors = server.allowOrigin(req_disallowed)
        assert allowed is False

    # Test wildcard CORS
    with mock.patch.object(
        util, "setting", side_effect=lambda k: ["*"] if k == "webCorsOriginList" else None
    ):
        req_any = web.WebRequest("POST", {b"origin": b"http://random.com"}, b"")
        allowed, cors = server.allowOrigin(req_any)
        assert allowed is True
        assert cors == "*"


def test_web_server_handler_wrapper_options():
    server = web.WebServer(None)
    req = web.WebRequest(
        b"OPTIONS",
        {b"origin": b"http://localhost", b"access-control-request-private-network": b"true"},
        b"",
    )
    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: ["http://localhost"] if k == "webCorsOriginList" else None,
    ):
        resp = server.handlerWrapper(req)
        assert b"Access-Control-Allow-Private-Network: true" in resp
        assert b"200 OK" in resp


def test_web_server_handler_wrapper_valid_request():
    mock_handler = mock.MagicMock(return_value={"result": "6", "error": None})
    server = web.WebServer(mock_handler)

    req_body = json.dumps({"action": "version", "version": 6}).encode("utf-8")
    req = web.WebRequest(b"POST", {b"origin": b"http://localhost"}, req_body)

    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: ["http://localhost"] if k == "webCorsOriginList" else None,
    ):
        resp = server.handlerWrapper(req)
        assert b"200 OK" in resp
        assert b'"result": "6"' in resp
        mock_handler.assert_called_once_with({"action": "version", "version": 6})


def test_web_server_handler_wrapper_invalid_json_or_schema():
    server = web.WebServer(None)

    # Empty body
    req_empty = web.WebRequest(b"POST", {}, b"")
    with mock.patch.object(
        util, "setting", side_effect=lambda k: 6 if k == "apiVersion" else ["http://localhost"]
    ):
        resp = server.handlerWrapper(req_empty)
        assert b"AnkiConnect v.6" in resp

    # Bad schema (missing action)
    req_bad = web.WebRequest(b"POST", {}, b'{"invalid": 123}')
    with mock.patch.object(
        util, "setting", side_effect=lambda k: 6 if k == "apiVersion" else ["http://localhost"]
    ):
        resp = server.handlerWrapper(req_bad)
        assert b'"error"' in resp


def test_web_server_handler_wrapper_forbidden():
    server = web.WebServer(None)
    req_body = json.dumps({"action": "version"}).encode("utf-8")
    req = web.WebRequest(b"POST", {b"origin": b"http://evil.com"}, req_body)

    with mock.patch.object(
        util,
        "setting",
        side_effect=lambda k: ["http://localhost"] if k == "webCorsOriginList" else None,
    ):
        resp = server.handlerWrapper(req)
        assert b"403 Forbidden" in resp


def test_web_server_listen_and_close():
    server = web.WebServer(None)
    mock_sock = mock.MagicMock()
    with (
        mock.patch("socket.socket", return_value=mock_sock),
        mock.patch.object(
            util,
            "setting",
            side_effect=lambda k: (
                "127.0.0.1" if k == "webBindAddress" else (8765 if k == "webBindPort" else 5)
            ),
        ),
    ):
        server.listen()
        mock_sock.bind.assert_called_once_with(("127.0.0.1", 8765))
        mock_sock.listen.assert_called_once_with(5)

    server.close()
    mock_sock.close.assert_called_once()
    assert server.sock is None


def test_format_replies():
    assert web.format_success_reply(4, "ok") == "ok"
    assert web.format_success_reply(6, "ok") == {"result": "ok", "error": None}
    assert web.format_exception_reply(6, Exception("fail")) == {"result": None, "error": "fail"}
