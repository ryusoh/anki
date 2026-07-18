#!/usr/bin/env python3
"""
Test local-proxy fallback in upload-to-r2: uploads try a direct connection
first and, on failure, retry through a detected localhost proxy exported as
HTTPS_PROXY (Clash/ShadowsocksX-NG/Privoxy/Astrill-style local listeners).
"""

import importlib.util
import os
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPT_DIR = Path(__file__).parent
SCRIPT = SCRIPT_DIR.parent / 'upload-to-r2'

_loader = SourceFileLoader('upload_to_r2_mod', str(SCRIPT))
_spec = importlib.util.spec_from_loader('upload_to_r2_mod', _loader)
r2 = importlib.util.module_from_spec(_spec)
_loader.exec_module(r2)

CREDS = {'account_id': 'acct', 'access_key': 'ak', 'secret_key': 'sk', 'bucket': 'b'}
PROXY = 'http://127.0.0.1:7897'


@pytest.fixture(autouse=True)
def clean_proxy_env(monkeypatch):
    """Start each test with no proxy env vars, no cached S3 client, and
    leak neither afterwards."""
    for var in ('HTTPS_PROXY', 'https_proxy', 'HTTP_PROXY', 'http_proxy'):
        monkeypatch.delenv(var, raising=False)
    r2._s3_client = None
    r2._s3_client_key = None
    yield
    for var in ('HTTPS_PROXY', 'HTTP_PROXY'):
        os.environ.pop(var, None)
    r2._s3_client = None
    r2._s3_client_key = None


def test_enable_keeps_live_explicit_proxy(monkeypatch):
    monkeypatch.setenv('HTTPS_PROXY', 'http://127.0.0.1:9999')
    monkeypatch.setattr(r2, '_probe_proxy', lambda url: True)
    assert r2.enable_proxy_fallback() is None
    assert os.environ['HTTPS_PROXY'] == 'http://127.0.0.1:9999'


def test_enable_drops_dead_proxy_and_retries_direct(monkeypatch):
    monkeypatch.setenv('HTTPS_PROXY', PROXY)
    monkeypatch.setattr(r2, '_probe_proxy', lambda url: False)
    monkeypatch.setattr(r2, 'detect_local_proxy', lambda ports=None: None)
    assert r2.enable_proxy_fallback() == 'direct'
    assert 'HTTPS_PROXY' not in os.environ
    assert 'HTTP_PROXY' not in os.environ


def test_enable_switches_dead_proxy_to_live_one(monkeypatch):
    monkeypatch.setenv('HTTPS_PROXY', 'http://127.0.0.1:1080')
    monkeypatch.setattr(r2, '_probe_proxy', lambda url: False)
    monkeypatch.setattr(r2, 'detect_local_proxy', lambda ports=None: PROXY)
    assert r2.enable_proxy_fallback() == PROXY
    assert os.environ['HTTPS_PROXY'] == PROXY


def test_boto3_dead_env_proxy_retries_direct(monkeypatch):
    """A stale HTTPS_PROXY pointing at a stopped proxy must not sink the
    upload: the run drops it and retries with a direct connection."""
    monkeypatch.setenv('HTTPS_PROXY', PROXY)
    client = MagicMock()
    client.put_object.side_effect = [ConnectionError('proxy refused'), None]
    monkeypatch.setattr(r2, 'HAS_BOTO3', True)
    monkeypatch.setattr(r2, 'boto3', MagicMock(client=MagicMock(return_value=client)), raising=False)
    monkeypatch.setattr(r2, 'Config', MagicMock(), raising=False)
    monkeypatch.setattr(r2, '_probe_proxy', lambda url: False)
    monkeypatch.setattr(r2, 'detect_local_proxy', lambda ports=None: None)

    ok, _ = r2.upload_to_r2('b', 'k', b'data', CREDS)

    assert ok
    assert client.put_object.call_count == 2
    assert 'HTTPS_PROXY' not in os.environ


def test_detect_probes_known_ports():
    def fake_connect(addr, timeout=None):
        if addr == ('127.0.0.1', 7897):
            return MagicMock()
        raise OSError('connection refused')

    with patch('socket.create_connection', side_effect=fake_connect):
        assert r2.detect_local_proxy() == PROXY


def test_detect_finds_astrill_openweb_port():
    """Astrill VPN's OpenWeb mode runs a local HTTP proxy on 127.0.0.1:3213;
    the fallback must find it when no Clash-family port is listening."""

    def fake_connect(addr, timeout=None):
        if addr == ('127.0.0.1', 3213):
            return MagicMock()
        raise OSError('connection refused')

    with patch('socket.create_connection', side_effect=fake_connect):
        assert r2.detect_local_proxy() == 'http://127.0.0.1:3213'


def test_detect_returns_none_when_nothing_listens():
    with patch('socket.create_connection', side_effect=OSError('refused')):
        assert r2.detect_local_proxy() is None


def test_probe_proxy_true_when_listening():
    with patch('socket.create_connection', return_value=MagicMock()) as probe:
        assert r2._probe_proxy(PROXY) is True
    assert probe.call_args[0][0] == ('127.0.0.1', 7897)


def test_probe_proxy_false_when_refused_or_malformed():
    with patch('socket.create_connection', side_effect=OSError('refused')):
        assert r2._probe_proxy(PROXY) is False
    assert r2._probe_proxy('http://') is False


def test_boto3_retries_via_detected_proxy(monkeypatch):
    client = MagicMock()
    client.put_object.side_effect = [ConnectionError('direct blocked'), None]
    monkeypatch.setattr(r2, 'HAS_BOTO3', True)
    monkeypatch.setattr(r2, 'boto3', MagicMock(client=MagicMock(return_value=client)), raising=False)
    monkeypatch.setattr(r2, 'Config', MagicMock(), raising=False)
    monkeypatch.setattr(r2, 'detect_local_proxy', lambda ports=None: PROXY)

    ok, size = r2.upload_to_r2('b', 'k', b'data', CREDS)

    assert ok
    assert size > 0
    assert client.put_object.call_count == 2
    assert os.environ['HTTPS_PROXY'] == PROXY


def test_boto3_falls_through_to_urllib_when_no_proxy(monkeypatch):
    client = MagicMock()
    client.put_object.side_effect = OSError('network down')
    monkeypatch.setattr(r2, 'HAS_BOTO3', True)
    monkeypatch.setattr(r2, 'boto3', MagicMock(client=MagicMock(return_value=client)), raising=False)
    monkeypatch.setattr(r2, 'Config', MagicMock(), raising=False)
    monkeypatch.setattr(r2, 'detect_local_proxy', lambda ports=None: None)

    with patch('urllib.request.urlopen', return_value=MagicMock(status=200)) as urlopen:
        ok, _ = r2.upload_to_r2('b', 'k', b'data', CREDS)

    assert ok
    assert client.put_object.call_count == 1  # no proxy found -> no boto3 retry
    urlopen.assert_called_once()
    assert 'HTTPS_PROXY' not in os.environ


def test_s3_client_reused_across_uploads(monkeypatch):
    """One client (one connection pool) serves the whole run — a client per
    file meant a fresh TLS handshake per note, which dominated upload time."""
    client = MagicMock()
    boto3_mock = MagicMock(client=MagicMock(return_value=client))
    monkeypatch.setattr(r2, 'HAS_BOTO3', True)
    monkeypatch.setattr(r2, 'boto3', boto3_mock, raising=False)
    monkeypatch.setattr(r2, 'Config', MagicMock(), raising=False)

    ok1, _ = r2.upload_to_r2('b', 'k1', b'a', CREDS)
    ok2, _ = r2.upload_to_r2('b', 'k2', b'b', CREDS)

    assert ok1 and ok2
    assert client.put_object.call_count == 2
    assert boto3_mock.client.call_count == 1


def test_s3_client_rebuilt_when_proxy_env_changes(monkeypatch):
    """botocore reads proxy env only at client creation, so a proxy enabled
    mid-run must invalidate the cached client."""
    boto3_mock = MagicMock()
    monkeypatch.setattr(r2, 'boto3', boto3_mock, raising=False)
    monkeypatch.setattr(r2, 'Config', MagicMock(), raising=False)

    r2.get_s3_client(CREDS)
    r2.get_s3_client(CREDS)
    assert boto3_mock.client.call_count == 1

    monkeypatch.setenv('HTTPS_PROXY', PROXY)
    r2.get_s3_client(CREDS)
    assert boto3_mock.client.call_count == 2


def test_urllib_retry_enables_proxy_and_rebuilds_opener(monkeypatch):
    monkeypatch.setattr(r2, 'HAS_BOTO3', False)
    monkeypatch.setattr(r2, 'detect_local_proxy', lambda ports=None: PROXY)

    with patch('urllib.request.urlopen',
               side_effect=[OSError('direct blocked'), MagicMock(status=200)]) as urlopen, \
         patch('urllib.request.install_opener') as install_opener, \
         patch('time.sleep'):
        ok, _ = r2.upload_to_r2('b', 'k', b'data', CREDS)

    assert ok
    assert urlopen.call_count == 2
    install_opener.assert_called_once()
    assert os.environ['HTTPS_PROXY'] == PROXY
