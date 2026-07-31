# -*- coding: utf-8 -*-
"""Tests for awesometts.service.edgetts."""

import sys
from unittest.mock import MagicMock

import pytest

from awesome_tts.awesometts.bundle import Bundle
from awesome_tts.awesometts.service.edgetts import EdgeTTS


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
