# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
# Copyright (C) 2010-Present  Anki AwesomeTTS Development Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Service implementation for the local Kokoro-82M TTS engine.

Kokoro is imported lazily; it is not declared as a dependency because the
user must install it (plus torch/soundfile/espeak-ng) manually in Anki's
Python environment.
"""

import os

from .base import Service

__all__ = ['Kokoro']


# Common American English voices in Kokoro-82M. The user must still install
# the voice files / model pack; this list only controls the dialog default.
_VOICE_LIST = [
    ('af_heart', 'American English (Heart)'),
    ('af_bella', 'American English (Bella)'),
    ('af_nicole', 'American English (Nicole)'),
    ('am_fenrir', 'American English (Fenrir)'),
    ('am_michael', 'American English (Michael)'),
]


class Kokoro(Service):
    """Local Kokoro-82M English TTS."""

    __slots__ = []

    NAME = "★ Kokoro (free, local)"

    TRAITS = []

    def desc(self):
        return "Kokoro-82M (free local English TTS; manual install required)"

    def options(self):
        return [
            dict(
                key='voice',
                label="Voice",
                values=_VOICE_LIST,
                transform=lambda value: value,
                default='af_heart',
            ),
        ]

    def run(self, text, options, path):
        try:
            import kokoro
            import numpy as np
            import soundfile as sf
        except ImportError as exc:
            raise EnvironmentError(
                'Kokoro is not installed — manual setup (needs espeak-ng): '
                'docs/free-tts-services-spec.md §7'
            ) from exc

        voice = options.get('voice', 'af_heart')
        sample_rate = 24000

        try:
            pipeline = kokoro.KPipeline(lang_code='a')
            generator = pipeline(text, voice=voice)
            chunks = [audio for _, _, audio in generator]
        except Exception as exc:
            raise ValueError(f"Kokoro generation failed for voice {voice}: {exc}") from exc

        if not chunks:
            raise ValueError("Kokoro produced no audio")

        merged = np.concatenate(chunks)
        wav_path = self.path_temp('wav')
        try:
            sf.write(wav_path, merged, sample_rate)
            self.cli_transcode(wav_path, path)
        finally:
            self.path_unlink(wav_path)

        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise ValueError(f"Kokoro wrote an empty or missing file at {path}")
