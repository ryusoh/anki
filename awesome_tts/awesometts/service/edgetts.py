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

import asyncio
import os

from ...proxy_fallback import _detect_local_proxy
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


# Local proxy URL that worked previously; re-probed when it dies, matching
# shared/proxy_fallback.py's heal-back-to-direct behavior (edge-tts uses
# aiohttp, which ignores proxy env vars, so the proxy is passed explicitly).
_working_proxy = None


def _is_network_error(exc):
    """True when no server was reached, so retrying via a proxy is worthwhile.

    HTTP-level failures (bad token, 403) reached the server and re-raise
    untouched — a proxy would not change them.
    """
    import aiohttp

    return isinstance(exc, (aiohttp.ClientConnectionError, asyncio.TimeoutError, OSError))


def _save_with_proxy_fallback(edge_tts, text, voice, path):
    """Save audio, trying a direct connection first and, on network failure,
    retrying once through a detected local proxy (cached for later calls)."""
    global _working_proxy
    if _working_proxy is not None:
        try:
            edge_tts.Communicate(text, voice=voice, proxy=_working_proxy).save_sync(path)
            return
        except Exception as exc:
            if not _is_network_error(exc):
                raise
            _working_proxy = None  # cached proxy died — heal back to direct
    try:
        edge_tts.Communicate(text, voice=voice).save_sync(path)
        return
    except Exception as exc:
        if not _is_network_error(exc):
            raise
        direct_error = exc
    proxy = _detect_local_proxy()
    if proxy is None:
        raise direct_error
    try:
        edge_tts.Communicate(text, voice=voice, proxy=proxy).save_sync(path)
    except Exception as exc:
        if _is_network_error(exc):
            raise direct_error from None  # both routes failed; report the direct one
        raise
    _working_proxy = proxy


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
                'edge-tts is not installed yet; AwesomeTTS auto-installs it in '
                'the background at startup — try again in a few seconds '
                '(requires network)'
            ) from exc

        voice = options.get('voice', 'en-US-AvaNeural')

        try:
            _save_with_proxy_fallback(edge_tts, text, voice, path)
        except Exception as exc:
            raise ValueError(f'edge-tts failed for voice {voice}: {exc}') from exc

        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise ValueError(f"edge-tts wrote an empty or missing file at {path}")
