import sys
import types
from unittest.mock import MagicMock, patch


def test_missing_timeout(tmp_path):
    # Setup sys.modules for mock
    mock_base = MagicMock()

    class MockService(object):
        def net_download(self, path, urls):
            pass

        def normalize(self, value):
            return value.lower()

    mock_base.Service = MockService

    sys.modules['awesometts'] = MagicMock()
    sys.modules['awesometts.service'] = MagicMock()
    sys.modules['awesometts.service.base'] = mock_base
    sys.modules['awesometts.service.common'] = MagicMock()

    with open('awesome_tts/awesometts/service/freedictionary.py', 'r') as f:
        code = f.read()

    # Make it absolute import for the test
    code = code.replace('from .base import Service', 'from awesometts.service.base import Service')
    code = code.replace('from .common import Trait', 'from awesometts.service.common import Trait')

    module = types.ModuleType('freedictionary')
    sys.modules['freedictionary'] = module
    exec(code, module.__dict__)

    service = module.FreeDictionary()

    output_path = str(tmp_path / "test.mp3")

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = (
            b'[{"phonetics": [{"audio": "https://example.com/audio.mp3"}]}]'
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response

        service.run("hello", {"voice": "us"}, output_path)

        assert mock_urlopen.call_count == 2
        for call_args in mock_urlopen.call_args_list:
            args, kwargs = call_args
            assert 'timeout' in kwargs
            assert kwargs['timeout'] == 10
