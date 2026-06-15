# -*- coding: utf-8 -*-

import json
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

from .base import Service
from .common import Trait

__all__ = ['FreeDictionary']


class FreeDictionary(Service):
    """
    Provides a Service-compliant implementation for Free Dictionary API.
    """

    NAME = "Free Dictionary API"

    TRAITS = [Trait.INTERNET]

    # Free Dictionary API primarily supports English dialects based on their returned URLs
    _VOICE_CODES = {
        'us': "English (US)",
        'uk': "English (UK)",
        'au': "English (AU)",
        'any': "English (Any Available)",
    }

    def desc(self):
        """
        Returns a short, static description.
        """
        return "Free Dictionary API (dictionaryapi.dev). Supports English words and provides real human pronunciations."

    def options(self):
        """
        Provides access to the dialect (voice) option.
        """

        def transform_voice(value):
            normalized = self.normalize(value)
            for code in self._VOICE_CODES:
                if normalized == self.normalize(code):
                    return code
            return value

        return [
            dict(
                key='voice',
                label="Voice/Dialect",
                values=[(code, name) for code, name in self._VOICE_CODES.items()],
                transform=transform_voice,
                default='us',
            ),
        ]

    def run(self, text, options, path):
        """
        Downloads from Free Dictionary API directly to an MP3.
        """
        if not text or not text.strip():
            raise ValueError("No text provided.")

        # Free dictionary API usually expects a single word, but we'll try to urlencode whatever is passed.
        # It doesn't support phrases well, but we pass it anyway.
        word = text.strip()
        encoded_word = urllib.parse.quote(word)
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{encoded_word}"

        req = urllib.request.Request(url, headers={"User-Agent": "AwesomeTTS-FreeDictionary/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            if e.code == 404:
                raise ValueError(f"Word '{word}' not found in Free Dictionary API.") from e
            raise IOError(f"Free Dictionary API returned HTTP {e.code}") from e
        except URLError as e:
            raise IOError(f"Network error when connecting to Free Dictionary API: {e}") from e
        except Exception as e:
            raise IOError(f"Error communicating with Free Dictionary API: {e}") from e

        # Extract the audio URLs
        audio_urls = []
        if isinstance(data, list) and len(data) > 0:
            for entry in data:
                if 'phonetics' in entry:
                    for phonetic in entry['phonetics']:
                        if 'audio' in phonetic and phonetic['audio'].strip():
                            audio_urls.append(phonetic['audio'])

        if not audio_urls:
            raise ValueError(f"No audio pronunciation found for '{word}'.")

        selected_url = None
        dialect = options.get('voice', 'us')

        if dialect != 'any':
            suffix = f"-{dialect}.mp3"
            for a_url in audio_urls:
                if a_url.endswith(suffix):
                    selected_url = a_url
                    break

        # Fallback to the first available if the specific dialect is not found or 'any' is selected
        if not selected_url:
            selected_url = audio_urls[0]

        # Use AwesomeTTS's built-in net_download utility to fetch the actual MP3
        self.net_download(path, [(selected_url, {})])
