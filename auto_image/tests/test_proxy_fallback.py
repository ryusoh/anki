"""Proxy-fallback behaviour for DuckDuckGo image API calls: direct
connection first, one retry through a detected local proxy
(Clash/Shadowsocks-style localhost listener), HTTP errors untouched."""

import os
import sys
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils
from utils import urlopen_with_proxy_fallback

PROXY = 'http://127.0.0.1:7897'


@pytest.fixture(autouse=True)
def reset_cached_opener():
    utils._proxy_opener = None
    yield
    utils._proxy_opener = None


def test_direct_success_never_probes():
    response = MagicMock()
    with (
        patch('urllib.request.urlopen', return_value=response),
        patch.object(utils, '_detect_local_proxy') as detect,
    ):
        assert urlopen_with_proxy_fallback('req') is response
        detect.assert_not_called()


def test_http_error_passes_through_without_fallback():
    err = HTTPError('url', 403, 'forbidden', None, None)
    with (
        patch('urllib.request.urlopen', side_effect=err),
        patch.object(utils, '_detect_local_proxy') as detect,
    ):
        with pytest.raises(HTTPError):
            urlopen_with_proxy_fallback('req')
        detect.assert_not_called()


def test_network_failure_retries_via_local_proxy_and_caches_it():
    response = MagicMock()
    opener = MagicMock()
    opener.open.return_value = response
    with (
        patch('urllib.request.urlopen', side_effect=URLError('offline')),
        patch.object(utils, '_detect_local_proxy', return_value=PROXY),
        patch('urllib.request.build_opener', return_value=opener) as build,
    ):
        assert urlopen_with_proxy_fallback('req') is response
    assert build.call_args[0][0].proxies == {'http': PROXY, 'https': PROXY}
    assert utils._proxy_opener is opener

    with patch('urllib.request.urlopen', side_effect=AssertionError('dialed direct')):
        assert urlopen_with_proxy_fallback('req2') is response
    assert opener.open.call_count == 2


def test_network_failure_without_proxy_raises_original_error():
    with (
        patch('urllib.request.urlopen', side_effect=URLError('offline')),
        patch.object(utils, '_detect_local_proxy', return_value=None),
    ):
        with pytest.raises(URLError):
            urlopen_with_proxy_fallback('req')


def test_dead_cached_proxy_heals_back_to_direct():
    dead = MagicMock()
    dead.open.side_effect = OSError('proxy gone')
    utils._proxy_opener = dead
    response = MagicMock()
    with patch('urllib.request.urlopen', return_value=response):
        assert urlopen_with_proxy_fallback('req') is response
    assert utils._proxy_opener is None


def test_download_image_falls_back_to_proxy():
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b'image-bytes'
    opener = MagicMock()
    opener.open.return_value = response
    with (
        patch('urllib.request.urlopen', side_effect=URLError('offline')),
        patch.object(utils, '_detect_local_proxy', return_value=PROXY),
        patch('urllib.request.build_opener', return_value=opener),
    ):
        assert utils.download_image('https://example.com/a.jpg') == b'image-bytes'
