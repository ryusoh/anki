import sys
from unittest.mock import MagicMock

sys.modules['anki'] = MagicMock()
sys.modules['aqt'] = MagicMock()

from unittest.mock import patch

from awesome_tts.awesometts.service.freedictionary import FreeDictionary


def test_missing_timeout():
    service = FreeDictionary()

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'[{"phonetics": [{"audio": "https://example.com/audio.mp3"}]}]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch('awesome_tts.awesometts.service.base.Service.net_download') as mock_net_download:
            service.run("hello", {"voice": "us"}, "/tmp/test.mp3")

        for call_args in mock_urlopen.call_args_list:
            args, kwargs = call_args
            if 'timeout' in kwargs:
                print(f"FAILED: timeout found in {kwargs}")
                return

        print("Success: timeout is missing")

test_missing_timeout()
