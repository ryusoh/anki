# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
# Copyright (C) 2010-Present  Anki AwesomeTTS Development Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Service implementation for edge-tts (unofficial Microsoft Edge TTS).

edge-tts is an optional dependency; this module imports it lazily so the
add-on still loads when edge-tts is not installed.
"""

import os

from .base import Service
from .common import Trait

__all__ = ['EdgeTTS']


# Short static list of the best-known free neural voices. edge-tts can list
# many more, but a static list keeps the dialog fast and avoids a network call.
_VOICE_LIST = [
    ('ja-JP-NanamiNeural', 'Japanese (Nanami)'),
    ('ja-JP-KeitaNeural', 'Japanese (Keita)'),
    ('en-US-AvaNeural', 'English US (Ava)'),
    ('en-US-AndrewNeural', 'English US (Andrew)'),
    ('en-GB-SoniaNeural', 'English GB (Sonia)'),
    ('en-GB-RyanNeural', 'English GB (Ryan)'),
]


class EdgeTTS(Service):
    """Unofficial Microsoft Edge TTS via the edge-tts package."""

    __slots__ = []

    NAME = "★ Edge-TTS (free)"

    TRAITS = [Trait.INTERNET]

    def desc(self):
        return "Edge-TTS (free neural; Internet required)"

    def options(self):
        return [
            dict(
                key='voice',
                label="Voice",
                values=_VOICE_LIST,
                transform=lambda value: value,
                default='en-US-AvaNeural',
            ),
        ]

    def run(self, text, options, path):
        try:
            import edge_tts
        except ImportError as exc:
            raise EnvironmentError(
                "edge-tts is not installed; run 'pip install edge-tts' in Anki's Python"
            ) from exc

        voice = options.get('voice', 'en-US-AvaNeural')

        try:
            edge_tts.Communicate(text, voice=voice).save_sync(path)
        except Exception as exc:
            raise ValueError(f"edge-tts failed for voice {voice}: {exc}") from exc

        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise ValueError(f"edge-tts wrote an empty or missing file at {path}")
