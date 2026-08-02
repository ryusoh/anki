"""Local-proxy fallback for urllib-based HTTP calls behind a blocked network.

Try a direct connection first; on network failure, retry once with a
proxy-free opener (heals a stale proxy cached in urllib's global opener),
then once through a detected local HTTP proxy (cached for later calls).
Probed ports: Clash Verge/Clash mixed (7897, 7890), ShadowsocksX-NG HTTP
(1087), Privoxy (8118), Astrill VPN OpenWeb mode (3213). HTTP errors
(4xx/5xx) reached the server, so they re-raise untouched.

This is the CANONICAL source. Anki add-ons must be self-contained (AnkiWeb
packages ship a single add-on dir), so each consuming add-on keeps a
byte-identical vendored copy at <addon>/proxy_fallback.py and uses it via:

    from .proxy_fallback import urlopen_with_proxy_fallback

tests/test_proxy_fallback_sync.py pins all copies (and the port list in
data/anki/upload-to-r2) in sync — edit here, re-vendor everywhere, keep that
test green. Background: docs/limited-network.md, failure mode 3.
"""

import urllib.request
from urllib.error import HTTPError

# Well-known localhost HTTP-proxy ports probed when a direct connection
# fails: Clash Verge/Clash mixed ports, ShadowsocksX-NG HTTP, Privoxy,
# Astrill VPN (OpenWeb mode local HTTP proxy).
_LOCAL_PROXY_PORTS = (7897, 7890, 1087, 8118, 3213)

_proxy_opener = None  # cached opener routed through a detected local proxy


def _detect_local_proxy(ports=_LOCAL_PROXY_PORTS):
    """Return a live local HTTP proxy URL worth falling back to, or None."""
    import os
    import socket
    from urllib.parse import urlparse

    candidate_ports = list(ports)

    # Dynamically discover local proxy ports configured in system settings or env
    for proxy_url in urllib.request.getproxies().values():
        if proxy_url:
            parsed = urlparse(proxy_url if '://' in proxy_url else f'http://{proxy_url}')
            if parsed.hostname in ('127.0.0.1', 'localhost') and parsed.port:
                if parsed.port not in candidate_ports:
                    candidate_ports.insert(0, parsed.port)

    for env_var in (
        'HTTP_PROXY',
        'HTTPS_PROXY',
        'ALL_PROXY',
        'http_proxy',
        'https_proxy',
        'all_proxy',
    ):
        val = os.environ.get(env_var)
        if val:
            parsed = urlparse(val if '://' in val else f'http://{val}')
            if parsed.hostname in ('127.0.0.1', 'localhost') and parsed.port:
                if parsed.port not in candidate_ports:
                    candidate_ports.insert(0, parsed.port)

    for port in candidate_ports:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.3):
                return f'http://127.0.0.1:{port}'
        except OSError:
            continue
    return None


def _build_direct_opener():
    """Opener that bypasses all proxies — a truly direct connection.

    ``urllib.request.urlopen`` reuses a global opener whose ProxyHandler
    snapshots the system proxy at first use. If a local proxy client (e.g.
    Astrill OpenWeb) was running when Anki made its first request and is
    later switched off or to a tunnel mode, that stale snapshot breaks every
    later urlopen even though the network itself is fine. A proxy-free
    opener heals this without leaking a proxy to the whole process.
    """
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def urlopen_with_proxy_fallback(req, timeout=10):
    """urlopen that tries a direct connection first and, on network failure,
    retries once proxy-free and once through a detected local proxy (cached
    for later calls).

    HTTP errors (4xx/5xx) reached the server, so they re-raise untouched.
    Runs inside Anki, so the proxy is scoped to a cached opener instead of
    mutating os.environ for the whole app; if the proxy dies later, the
    helper heals back to a direct connection.
    """
    global _proxy_opener
    if _proxy_opener is not None:
        try:
            return _proxy_opener.open(req, timeout=timeout)
        except HTTPError:
            raise
        except OSError:
            _proxy_opener = None  # proxy died — fall back to direct
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except HTTPError:
        raise
    except OSError as direct_err:
        # A stale proxy cached in the global opener can be the real failure —
        # retry once with a proxy-free opener before probing local ports.
        try:
            return _build_direct_opener().open(req, timeout=timeout)
        except HTTPError:
            raise
        except OSError:
            proxy = _detect_local_proxy()
            if proxy is None:
                raise direct_err from None
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
            )
            response = opener.open(req, timeout=timeout)
            _proxy_opener = opener
            return response
