import sys
from unittest.mock import MagicMock
sys.modules['anki'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.qt'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()

import unittest
from unittest.mock import patch
sys.path.append('awesome_tts')
from awesometts.service.ispeech import ISpeech

class TestISpeechHttps(unittest.TestCase):
    @patch('awesometts.service.ispeech.urllib.request.urlopen')
    def test_ispeech_uses_https(self, mock_urlopen):
        # We just need to check the parameters passed to awesometts.service.base's fetch method implicitly,
        # but the ispeech code sets up a list of tuples containing URL and payload.
        # Let's mock _fetch_payload directly to verify what is passed.
        with patch.object(ISpeech, '_fetch_payload') as mock_fetch:
            mock_fetch.return_value = True
            service = ISpeech()
            options = {'key': 'testkey', 'voice': 'usenglishmale', 'speed': 0, 'pitch': 100}
            service.play_tts('Hello', options)

            # The second argument to _fetch_payload should be a list of configuration tuples
            # where the first element of each tuple is the URL.
            configs = mock_fetch.call_args[0][1]
            for config in configs:
                url = config[0]
                self.assertTrue(url.startswith('https://'), "URL should start with https://")

if __name__ == '__main__':
    unittest.main()
