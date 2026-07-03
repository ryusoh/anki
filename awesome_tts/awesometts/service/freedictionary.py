# -*- coding: utf-8 -*-


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
        """Executes a speech request using Free Dictionary API"""
        try:
            import urllib.request
            from json import loads
            from urllib.parse import quote_plus

            word = quote_plus(text.strip())
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 AwesomeTTS'})
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    data = loads(response.read().decode('utf-8'))
            except Exception as e:
                raise IOError(f"Network error when connecting to Free Dictionary API: {e}") from e

            if isinstance(data, dict) and data.get("title") == "No Definitions Found":
                raise ValueError(f"Word not found in Free Dictionary: {text}")

            audio_url = None
            if isinstance(data, list) and len(data) > 0:
                phonetics = data[0].get("phonetics", [])
                for phonetic in phonetics:
                    audio_candidate = phonetic.get("audio")
                    if audio_candidate:
                        audio_url = audio_candidate
                        break

            if not audio_url:
                raise ValueError(f"No audio available for word: {text}")

            audio_request = urllib.request.Request(
                audio_url, headers={'User-Agent': 'Mozilla/5.0 AwesomeTTS'}
            )
            try:
                with urllib.request.urlopen(audio_request, timeout=10) as audio_response:
                    with open(path, 'wb') as f:
                        f.write(audio_response.read())
            except Exception as e:
                raise IOError(f"Error downloading audio from {audio_url}: {e}") from e

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
