# -*- coding: utf-8 -*-
"""Tests for awesometts.service.voicevox."""

import shutil
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from awesome_tts.awesometts.bundle import Bundle
from awesome_tts.awesometts.service.voicevox import Voicevox


@pytest.fixture
def svc(tmp_path):
    return Voicevox(
        temp_dir=str(tmp_path),
        lame_flags=lambda: '--quiet -q 2',
        normalize=lambda x: x,
        logger=Bundle(debug=print, info=print, warn=print, error=print),
        ecosystem=Bundle(web='http://test', agent='test'),
        languagetools=Bundle(use_plus_mode=lambda: False),
        config={},
    )


@pytest.fixture(autouse=True)
def _bypass_lame():
    """Replace LAME transcoding with a plain file copy for tests."""
    with patch.object(
        Voicevox,
        'cli_transcode',
        lambda self, input_path, output_path: shutil.copyfile(input_path, output_path),
    ):
        yield


def _response(body, status=200):
    resp = MagicMock()
    resp.read.return_value = body if isinstance(body, bytes) else body.encode('utf-8')
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_run_queries_speaker_and_synthesizes(svc, tmp_path):
    path = tmp_path / 'out.mp3'
    speakers = [{'name': '四国めたん', 'styles': [{'id': 2}]}]
    query_json = '{"kana":"カナ"}'
    wav = b'RIFFwavdata'

    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        if '/speakers' in url:
            return _response(__import__('json').dumps(speakers).encode('utf-8'))
        if '/audio_query' in url:
            return _response(query_json.encode('utf-8'))
        if '/synthesis' in url:
            return _response(wav)
        raise AssertionError(f"unexpected URL: {url}")

    with patch('awesome_tts.awesometts.service.voicevox.urlopen', side_effect=fake_urlopen):
        svc.run('日陰', {}, str(path))

    assert path.read_bytes() == wav
    assert svc._speaker_id == 2


def test_run_reuses_cached_speaker_id(svc, tmp_path):
    svc._speaker_id = 7
    path = tmp_path / 'out.mp3'
    query_json = '{"kana":"カナ"}'
    wav = b'RIFFwavdata'

    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        if '/audio_query' in url:
            return _response(query_json.encode('utf-8'))
        if '/synthesis' in url:
            return _response(wav)
        raise AssertionError(f"unexpected URL: {url}")

    with patch('awesome_tts.awesometts.service.voicevox.urlopen', side_effect=fake_urlopen):
        svc.run('日陰', {}, str(path))

    assert path.read_bytes() == wav


def test_run_fails_when_engine_unreachable(svc, tmp_path):
    with patch('awesome_tts.awesometts.service.voicevox.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = URLError("connection refused")
        with pytest.raises(EnvironmentError, match='Cannot reach VOICEVOX'):
            svc.run('日陰', {}, str(tmp_path / 'out.mp3'))
