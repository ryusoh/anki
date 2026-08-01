"""Proxy-fallback behaviour for Wiktionary API calls: direct connection
first, one retry through a detected local proxy (Clash/Shadowsocks/Astrill-style
localhost listener), HTTP errors passed through untouched."""

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from auto_wiktionary import proxy_fallback, utils
from auto_wiktionary.proxy_fallback import urlopen_with_proxy_fallback

PROXY = 'http://127.0.0.1:7897'


@pytest.fixture(autouse=True)
def reset_cached_opener():
    proxy_fallback._proxy_opener = None
    yield
    proxy_fallback._proxy_opener = None


def test_direct_success_never_probes():
    response = MagicMock()
    with (
        patch('urllib.request.urlopen', return_value=response),
        patch.object(proxy_fallback, '_detect_local_proxy') as detect,
    ):
        assert urlopen_with_proxy_fallback('req', timeout=5) is response
        detect.assert_not_called()


def test_http_error_passes_through_without_fallback():
    err = HTTPError('url', 404, 'not found', None, None)
    with (
        patch('urllib.request.urlopen', side_effect=err),
        patch.object(proxy_fallback, '_detect_local_proxy') as detect,
    ):
        with pytest.raises(HTTPError):
            urlopen_with_proxy_fallback('req', timeout=5)
        detect.assert_not_called()


def test_network_failure_retries_via_local_proxy_and_caches_it():
    response = MagicMock()
    direct_opener = MagicMock()
    direct_opener.open.side_effect = URLError('still offline')
    opener = MagicMock()
    opener.open.return_value = response
    with (
        patch('urllib.request.urlopen', side_effect=URLError('offline')),
        patch.object(proxy_fallback, '_build_direct_opener', return_value=direct_opener),
        patch.object(proxy_fallback, '_detect_local_proxy', return_value=PROXY),
        patch('urllib.request.build_opener', return_value=opener) as build,
    ):
        assert urlopen_with_proxy_fallback('req', timeout=5) is response
    proxies = build.call_args[0][0].proxies
    assert proxies == {'http': PROXY, 'https': PROXY}
    assert proxy_fallback._proxy_opener is opener

    # Cached: the next call goes straight through the proxy opener.
    with patch('urllib.request.urlopen', side_effect=AssertionError('dialed direct')):
        assert urlopen_with_proxy_fallback('req2', timeout=5) is response
    assert opener.open.call_count == 2


def test_stale_cached_system_proxy_heals_via_proxy_free_retry():
    """urlopen's global opener snapshots the system proxy at first use; when
    that proxy later dies (e.g. Astrill OpenWeb switched off or to a tunnel
    mode), every urlopen fails even on a healthy network. The proxy-free
    retry must heal it without probing local ports."""
    response = MagicMock()
    direct_opener = MagicMock()
    direct_opener.open.return_value = response
    with (
        patch('urllib.request.urlopen', side_effect=URLError('stale proxy refused')),
        patch.object(proxy_fallback, '_build_direct_opener', return_value=direct_opener),
        patch.object(proxy_fallback, '_detect_local_proxy') as detect,
    ):
        assert urlopen_with_proxy_fallback('req', timeout=5) is response
        detect.assert_not_called()


def test_network_failure_without_proxy_raises_original_error():
    direct_opener = MagicMock()
    direct_opener.open.side_effect = URLError('still offline')
    with (
        patch('urllib.request.urlopen', side_effect=URLError('offline')),
        patch.object(proxy_fallback, '_build_direct_opener', return_value=direct_opener),
        patch.object(proxy_fallback, '_detect_local_proxy', return_value=None),
    ):
        with pytest.raises(URLError):
            urlopen_with_proxy_fallback('req', timeout=5)


def test_detect_local_proxy_finds_astrill_openweb_port():
    """Astrill VPN's OpenWeb mode runs a local HTTP proxy on 127.0.0.1:3213;
    the fallback must find it when no Clash-family port is listening."""

    def fake_connect(addr, timeout):
        if addr[1] != 3213:
            raise OSError('closed')
        return MagicMock()

    with patch('socket.create_connection', side_effect=fake_connect):
        assert proxy_fallback._detect_local_proxy() == 'http://127.0.0.1:3213'


def test_dead_cached_proxy_heals_back_to_direct():
    dead = MagicMock()
    dead.open.side_effect = OSError('proxy gone')
    proxy_fallback._proxy_opener = dead
    response = MagicMock()
    with patch('urllib.request.urlopen', return_value=response):
        assert urlopen_with_proxy_fallback('req', timeout=5) is response
    assert proxy_fallback._proxy_opener is None


def test_fetch_wiktionary_html_falls_back_to_proxy():
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b'<p>definition</p>'
    direct_opener = MagicMock()
    direct_opener.open.side_effect = URLError('still offline')
    opener = MagicMock()
    opener.open.return_value = response
    with (
        patch('urllib.request.urlopen', side_effect=URLError('offline')),
        patch.object(proxy_fallback, '_build_direct_opener', return_value=direct_opener),
        patch.object(proxy_fallback, '_detect_local_proxy', return_value=PROXY),
        patch('urllib.request.build_opener', return_value=opener),
    ):
        assert utils.fetch_wiktionary_html('word', 'en') == '<p>definition</p>'
