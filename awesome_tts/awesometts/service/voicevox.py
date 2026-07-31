# -*- coding: utf-8 -*-

# AwesomeTTS text-to-speech add-on for Anki
# Copyright (C) 2010-Present  Anki AwesomeTTS Development Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Service implementation for a local VOICEVOX engine.

Expects the VOICEVOX HTTP API at http://localhost:50021 (default).
"""

import json
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .base import Service

__all__ = ['Voicevox']


_BASE_URL = 'http://localhost:50021'
_TIMEOUT = 10


class Voicevox(Service):
    """Local VOICEVOX Japanese TTS."""

    __slots__ = ['_speaker_id']

    NAME = "★ VOICEVOX (free, local)"

    TRAITS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._speaker_id = None

    def desc(self):
        return "VOICEVOX (free local Japanese TTS; localhost:50021)"

    def options(self):
        return []

    def _get_speaker_id(self):
        """Pick the first available speaker/style from the local engine."""
        if self._speaker_id is not None:
            return self._speaker_id

        try:
            with urlopen(f'{_BASE_URL}/speakers', timeout=_TIMEOUT) as response:
                speakers = json.loads(response.read().decode('utf-8'))
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise EnvironmentError(
                'Cannot reach VOICEVOX at localhost:50021 — engine not running; '
                'manual setup: docs/free-tts-services-spec.md §7'
            ) from exc

        for speaker in speakers:
            styles = speaker.get('styles', [])
            if styles:
                self._speaker_id = styles[0].get('id')
                break

        if self._speaker_id is None:
            raise EnvironmentError("VOICEVOX returned no usable speakers")

        return self._speaker_id

    def run(self, text, options, path):
        speaker_id = self._get_speaker_id()
        encoded_text = quote(text, safe='')

        query_url = f'{_BASE_URL}/audio_query?text={encoded_text}&speaker={speaker_id}'
        try:
            query_req = Request(query_url, data=b'', method='POST')
            with urlopen(query_req, timeout=_TIMEOUT) as response:
                query_payload = response.read().decode('utf-8')
        except (URLError, TimeoutError) as exc:
            raise ValueError(f"VOICEVOX audio_query failed: {exc}") from exc

        synth_url = f'{_BASE_URL}/synthesis?speaker={speaker_id}'
        try:
            synth_req = Request(
                synth_url,
                data=query_payload.encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urlopen(synth_req, timeout=_TIMEOUT) as response:
                wav_bytes = response.read()
        except (URLError, TimeoutError) as exc:
            raise ValueError(f"VOICEVOX synthesis failed: {exc}") from exc

        if not wav_bytes:
            raise ValueError("VOICEVOX returned empty audio")

        wav_path = self.path_temp('wav')
        with open(wav_path, 'wb') as out:
            out.write(wav_bytes)

        try:
            self.cli_transcode(wav_path, path)
        finally:
            self.path_unlink(wav_path)
