"""Proxy-fallback behaviour for AwesomeTTS API calls: direct connection first,
one retry through a detected local proxy (Clash/Shadowsocks/Astrill-style
localhost listener), HTTP errors untouched."""

from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from awesome_tts import proxy_fallback
from awesome_tts.proxy_fallback import urlopen_with_proxy_fallback

PROXY = "http://127.0.0.1:7897"


@pytest.fixture(autouse=True)
def reset_cached_opener():
    proxy_fallback._proxy_opener = None
    yield
    proxy_fallback._proxy_opener = None


def test_direct_success_never_probes():
    response = MagicMock()
    with (
        patch("urllib.request.urlopen", return_value=response),
        patch.object(proxy_fallback, "_detect_local_proxy") as detect,
    ):
        assert urlopen_with_proxy_fallback("req") is response
        detect.assert_not_called()


def test_http_error_passes_through_without_fallback():
    err = HTTPError("url", 403, "forbidden", None, None)
    with (
        patch("urllib.request.urlopen", side_effect=err),
        patch.object(proxy_fallback, "_detect_local_proxy") as detect,
    ):
        with pytest.raises(HTTPError):
            urlopen_with_proxy_fallback("req")
        detect.assert_not_called()


def test_network_failure_retries_via_local_proxy_and_caches_it():
    response = MagicMock()
    direct_opener = MagicMock()
    direct_opener.open.side_effect = URLError("still offline")
    opener = MagicMock()
    opener.open.return_value = response
    with (
        patch("urllib.request.urlopen", side_effect=URLError("offline")),
        patch.object(proxy_fallback, "_build_direct_opener", return_value=direct_opener),
        patch.object(proxy_fallback, "_detect_local_proxy", return_value=PROXY),
        patch("urllib.request.build_opener", return_value=opener) as build,
    ):
        assert urlopen_with_proxy_fallback("req") is response
    assert build.call_args[0][0].proxies == {"http": PROXY, "https": PROXY}
    assert proxy_fallback._proxy_opener is opener

    with patch("urllib.request.urlopen", side_effect=AssertionError("dialed direct")):
        assert urlopen_with_proxy_fallback("req2") is response
    assert opener.open.call_count == 2


def test_stale_cached_system_proxy_heals_via_proxy_free_retry():
    response = MagicMock()
    direct_opener = MagicMock()
    direct_opener.open.return_value = response
    with (
        patch(
            "urllib.request.urlopen",
            side_effect=URLError("stale proxy refused"),
        ),
        patch.object(proxy_fallback, "_build_direct_opener", return_value=direct_opener),
        patch.object(proxy_fallback, "_detect_local_proxy") as detect,
    ):
        assert urlopen_with_proxy_fallback("req") is response
        detect.assert_not_called()


def test_network_failure_without_proxy_raises_original_error():
    direct_opener = MagicMock()
    direct_opener.open.side_effect = URLError("still offline")
    with (
        patch("urllib.request.urlopen", side_effect=URLError("offline")),
        patch.object(proxy_fallback, "_build_direct_opener", return_value=direct_opener),
        patch.object(proxy_fallback, "_detect_local_proxy", return_value=None),
    ):
        with pytest.raises(URLError):
            urlopen_with_proxy_fallback("req")


def test_detect_local_proxy_finds_astrill_openweb_port():
    def fake_connect(addr, timeout):
        if addr[1] != 3213:
            raise OSError("closed")
        return MagicMock()

    with patch("socket.create_connection", side_effect=fake_connect):
        assert proxy_fallback._detect_local_proxy() == "http://127.0.0.1:3213"


def test_detect_local_proxy_finds_dynamic_system_or_env_port():
    def fake_connect(addr, timeout):
        if addr[1] != 9999:
            raise OSError("closed")
        return MagicMock()

    with (
        patch("socket.create_connection", side_effect=fake_connect),
        patch(
            "urllib.request.getproxies",
            return_value={"http": "http://127.0.0.1:9999"},
        ),
    ):
        assert proxy_fallback._detect_local_proxy() == "http://127.0.0.1:9999"


def test_dead_cached_proxy_heals_back_to_direct():
    dead = MagicMock()
    dead.open.side_effect = OSError("proxy gone")
    proxy_fallback._proxy_opener = dead
    response = MagicMock()
    with patch("urllib.request.urlopen", return_value=response):
        assert urlopen_with_proxy_fallback("req") is response
    assert proxy_fallback._proxy_opener is None
