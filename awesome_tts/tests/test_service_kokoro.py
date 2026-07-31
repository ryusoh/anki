# -*- coding: utf-8 -*-
"""Tests for awesometts.service.kokoro."""

import shutil
import sys
from unittest.mock import MagicMock, patch

import pytest

from awesome_tts.awesometts.bundle import Bundle
from awesome_tts.awesometts.service.kokoro import Kokoro


@pytest.fixture
def svc(tmp_path):
    return Kokoro(
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
        Kokoro,
        'cli_transcode',
        lambda self, input_path, output_path: shutil.copyfile(input_path, output_path),
    ):
        yield


def _install_fake_kokoro(monkeypatch, audio_chunks=None, raise_on_gen=None):
    """Install a fake kokoro/numpy/soundfile stack into sys.modules."""
    audio_chunks = audio_chunks if audio_chunks is not None else [b'chunk1']

    fake_kokoro = MagicMock()

    class FakePipeline:
        def __call__(self, text, voice):
            if raise_on_gen:
                raise raise_on_gen
            for chunk in audio_chunks:
                yield ('gs', 'ps', chunk)

    fake_kokoro.KPipeline = MagicMock(return_value=FakePipeline())

    fake_np = MagicMock()

    def fake_concat(arrays):
        return b''.join(arrays)

    fake_np.concatenate = fake_concat

    fake_sf = MagicMock()

    def fake_write(path, data, samplerate):
        with open(path, 'wb') as out:
            out.write(data)

    fake_sf.write = fake_write

    monkeypatch.setitem(sys.modules, 'kokoro', fake_kokoro)
    monkeypatch.setitem(sys.modules, 'numpy', fake_np)
    monkeypatch.setitem(sys.modules, 'soundfile', fake_sf)
    return fake_kokoro, fake_np, fake_sf


def test_run_generates_audio(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    _install_fake_kokoro(monkeypatch, [b'RIFFwav1', b'RIFFwav2'])

    svc.run('hello', {'voice': 'af_heart'}, str(path))

    assert path.read_bytes() == b'RIFFwav1RIFFwav2'


def test_run_uses_default_voice(svc, tmp_path, monkeypatch):
    path = tmp_path / 'out.mp3'
    fake_kokoro, _, _ = _install_fake_kokoro(monkeypatch, [b'RIFFwav'])

    svc.run('hello', {}, str(path))

    assert fake_kokoro.KPipeline.call_args.kwargs['lang_code'] == 'a'


def test_run_missing_dependency_raises(svc, tmp_path, monkeypatch):
    monkeypatch.delitem(sys.modules, 'kokoro', raising=False)
    monkeypatch.setitem(sys.modules, 'kokoro', None)

    with pytest.raises(EnvironmentError, match='Kokoro is not installed'):
        svc.run('hello', {'voice': 'af_heart'}, str(tmp_path / 'out.mp3'))


def test_run_propagates_generation_failure(svc, tmp_path, monkeypatch):
    _install_fake_kokoro(monkeypatch, raise_on_gen=RuntimeError('model missing'))

    with pytest.raises(ValueError, match='Kokoro generation failed'):
        svc.run('hello', {'voice': 'af_heart'}, str(tmp_path / 'out.mp3'))
