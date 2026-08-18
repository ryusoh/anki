# -*- coding: utf-8 -*-
"""Tests for awesometts.service.edgetts."""

import asyncio
import sys
from unittest.mock import MagicMock

import aiohttp
import pytest

from awesome_tts.awesometts.bundle import Bundle
from awesome_tts.awesometts.service import edgetts as edgetts_module
from awesome_tts.awesometts.service.edgetts import EdgeTTS


@pytest.fixture(autouse=True)
def _reset_proxy_cache(monkeypatch):
    monkeypatch.setattr(edgetts_module, '_working_proxy', None)


@pytest.fixture
def svc(tmp_path):
    return EdgeTTS(
        temp_dir=str(tmp_path),
        lame_flags=lambda: '--quiet -q 2',
        normalize=lambda x: x,
        logger=Bundle(debug=print, info=print, warn=print, error=print),
        ecosystem=Bundle(web='http://test', agent='test'),
        languagetools=Bundle(use_plus_mode=lambda: False),
        config={},
    )


def _mock_edge_tts(monkeypatch, audio_bytes=b'mp3data'):
    """Install a fake edge_tts module that writes audio_bytes to the path."""
    fake = MagicMock()

    def _save_sync(path):
        with open(path, 'wb') as out:
            out.write(audio_bytes)

    communicate_instance = MagicMock()
    communicate_instance.save_sync = _save_sync
    fake.Communicate = MagicMock(return_value=communicate_instance)
    monkeypatch.setitem(sys.modules, 'edge_tts', fake)
    return fake


def _mock_edge_tts_scripted(monkeypatch, outcomes):
    """Install a fake edge_tts whose successive Communicate calls either write
    the given bytes or raise the given exception. Returns the recorded kwargs
    of every call."""
    fake = MagicMock()
    calls = []

    class FakeCommunicate:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def save_sync(self, path):
            outcome = outcomes[len(calls)]
            calls.append(self.kwargs)
            if isinstance(outcome, Exception):
                raise outcome
            with open(path, 'wb') as out:
                out.write(outcome)

    fake.Communicate = FakeCommunicate
    monkeypatch.setitem(sys.modules, 'edge_tts', fake)
    return calls


def _http_error(status=403):
    return aiohttp.ClientResponseError(MagicMock(), (), status=status)


def test_run_writes_audio_file(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    _mock_edge_tts(monkeypatch, b'fake mp3')

    svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(path))

    assert path.read_bytes() == b'fake mp3'


def test_run_uses_default_voice(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    fake = _mock_edge_tts(monkeypatch)

    svc.run('hello', {}, str(path))

    assert fake.Communicate.call_args.kwargs['voice'] == 'en-US-AvaNeural'


def test_run_propagates_failure(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    fake = _mock_edge_tts(monkeypatch)

    class FailingCommunicate:
        def __init__(self, *args, **kwargs):
            pass

        def save_sync(self, path):
            raise RuntimeError('network error')

    fake.Communicate = FailingCommunicate

    with pytest.raises(ValueError, match='edge-tts failed'):
        svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(path))


def test_run_rejects_empty_output(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    _mock_edge_tts(monkeypatch, b'')

    with pytest.raises(ValueError, match='empty or missing file'):
        svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(path))


def test_run_missing_dependency_raises(svc, tmp_path, monkeypatch):
    monkeypatch.delitem(sys.modules, 'edge_tts', raising=False)
    monkeypatch.setitem(sys.modules, 'edge_tts', None)

    with pytest.raises(EnvironmentError, match='edge-tts is not installed'):
        svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(tmp_path / 'out.mp3'))


def test_network_error_retries_via_detected_proxy(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    calls = _mock_edge_tts_scripted(
        monkeypatch, [aiohttp.ClientConnectionError('blocked'), b'fake mp3']
    )
    monkeypatch.setattr(edgetts_module, '_detect_local_proxy', lambda: 'http://127.0.0.1:7897')

    svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(path))

    assert path.read_bytes() == b'fake mp3'
    assert 'proxy' not in calls[0]
    assert calls[1]['proxy'] == 'http://127.0.0.1:7897'
    assert edgetts_module._working_proxy == 'http://127.0.0.1:7897'


def test_network_error_without_proxy_reraises(svc, tmp_path, monkeypatch):
    calls = _mock_edge_tts_scripted(monkeypatch, [aiohttp.ClientConnectionError('blocked')])
    monkeypatch.setattr(edgetts_module, '_detect_local_proxy', lambda: None)

    with pytest.raises(ValueError, match='edge-tts failed'):
        svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(tmp_path / 'out.mp3'))

    assert len(calls) == 1  # no blind retry when no proxy is listening


def test_cached_proxy_is_used_first(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    calls = _mock_edge_tts_scripted(monkeypatch, [b'fake mp3'])
    edgetts_module._working_proxy = 'http://127.0.0.1:7890'

    svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(path))

    assert calls[0]['proxy'] == 'http://127.0.0.1:7890'


def test_dead_cached_proxy_heals_back_to_direct(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    calls = _mock_edge_tts_scripted(
        monkeypatch, [aiohttp.ClientConnectionError('proxy died'), b'fake mp3']
    )
    edgetts_module._working_proxy = 'http://127.0.0.1:7890'
    detect = MagicMock(return_value='http://127.0.0.1:7897')
    monkeypatch.setattr(edgetts_module, '_detect_local_proxy', detect)

    svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(path))

    assert path.read_bytes() == b'fake mp3'
    assert 'proxy' not in calls[1]  # healed back to a direct connection
    assert edgetts_module._working_proxy is None
    detect.assert_not_called()


def test_http_error_is_not_retried(svc, tmp_path, monkeypatch):
    calls = _mock_edge_tts_scripted(monkeypatch, [_http_error(403)])
    detect = MagicMock(return_value='http://127.0.0.1:7897')
    monkeypatch.setattr(edgetts_module, '_detect_local_proxy', detect)

    with pytest.raises(ValueError, match='edge-tts failed'):
        svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(tmp_path / 'out.mp3'))

    assert len(calls) == 1
    detect.assert_not_called()


def test_failed_proxy_retry_reports_the_direct_error(svc, tmp_path, monkeypatch):
    _mock_edge_tts_scripted(
        monkeypatch,
        [
            aiohttp.ClientConnectionError('direct route blocked'),
            aiohttp.ClientConnectionError('proxy route blocked'),
        ],
    )
    monkeypatch.setattr(edgetts_module, '_detect_local_proxy', lambda: 'http://127.0.0.1:7897')

    with pytest.raises(ValueError, match='direct route blocked'):
        svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(tmp_path / 'out.mp3'))


def test_is_network_error_classification():
    assert edgetts_module._is_network_error(aiohttp.ClientConnectionError('x'))
    assert edgetts_module._is_network_error(asyncio.TimeoutError('x'))
    assert edgetts_module._is_network_error(OSError('x'))
    assert not edgetts_module._is_network_error(_http_error(403))
    assert not edgetts_module._is_network_error(RuntimeError('x'))


def test_desc():
    assert EdgeTTS.NAME == "★ Edge-TTS (free)"
    svc = EdgeTTS(
        temp_dir="tmp",
        lame_flags=lambda: '--quiet -q 2',
        normalize=lambda x: x,
        logger=Bundle(debug=print, info=print, warn=print, error=print),
        ecosystem=Bundle(web='http://test', agent='test'),
        languagetools=Bundle(use_plus_mode=lambda: False),
        config={},
    )
    assert svc.desc() == "Edge-TTS (free neural; Internet required)"


def test_options():
    svc = EdgeTTS(
        temp_dir="tmp",
        lame_flags=lambda: '--quiet -q 2',
        normalize=lambda x: x,
        logger=Bundle(debug=print, info=print, warn=print, error=print),
        ecosystem=Bundle(web='http://test', agent='test'),
        languagetools=Bundle(use_plus_mode=lambda: False),
        config={},
    )
    options = svc.options()
    assert len(options) == 1
    assert options[0]['key'] == 'voice'
    assert options[0]['transform']("x") == "x"


def test_cached_proxy_non_network_error_reraises(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    _mock_edge_tts_scripted(monkeypatch, [ValueError('non network error')])
    edgetts_module._working_proxy = 'http://127.0.0.1:7890'
    with pytest.raises(ValueError, match='non network error'):
        svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(path))


def test_proxy_fallback_non_network_error_reraises(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    _mock_edge_tts_scripted(
        monkeypatch,
        [aiohttp.ClientConnectionError('direct blocked'), ValueError('non network error')],
    )
    monkeypatch.setattr(edgetts_module, '_detect_local_proxy', lambda: 'http://127.0.0.1:7897')

    with pytest.raises(ValueError, match='non network error'):
        svc.run('hello', {'voice': 'en-US-AvaNeural'}, str(path))
