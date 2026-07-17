import json
import logging
import re
import urllib.parse
import urllib.request
from urllib.error import HTTPError

logger = logging.getLogger(__name__)

# Well-known localhost HTTP-proxy ports probed when a direct connection
# fails: Clash Verge/Clash mixed ports, ShadowsocksX-NG HTTP, Privoxy.
_LOCAL_PROXY_PORTS = (7897, 7890, 1087, 8118)

_proxy_opener = None  # cached opener routed through a detected local proxy


def _detect_local_proxy(ports=_LOCAL_PROXY_PORTS):
    """Return a live local HTTP proxy URL worth falling back to, or None."""
    import socket

    for port in ports:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.3):
                return f'http://127.0.0.1:{port}'
        except OSError:
            continue
    return None


def urlopen_with_proxy_fallback(req, timeout=10):
    """urlopen that tries a direct connection first and, on network failure,
    retries once through a detected local proxy (cached for later calls).

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
    except OSError:
        proxy = _detect_local_proxy()
        if proxy is None:
            raise
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
        )
        response = opener.open(req, timeout=timeout)
        _proxy_opener = opener
        return response


def clean_html_text(html_text):
    """Cleans HTML tags and entities to extract raw text for searching."""
    if not html_text:
        return ""

    text = re.sub(r'<br\s*/?>', ' ', html_text)
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'<[^>]+>', '', text)
    text = ' '.join(text.split())
    return text


def _get_vqd_token(query):
    """Fetches a DuckDuckGo vqd token needed for the image API."""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://duckduckgo.com/?q={encoded_query}&iax=images&ia=images"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        },
    )
    with urlopen_with_proxy_fallback(req, timeout=10) as response:
        html = response.read().decode('utf-8', errors='ignore')

    match = re.search(r'vqd="([^"]+)"', html) or re.search(r'vqd=([^&"]+)', html)
    return match.group(1) if match else None


def fetch_image_results(query):
    """
    Fetches candidate image URLs using DuckDuckGo's image search API.
    Returns raw URLs without downloading — validation is done lazily per click.
    """
    if not query:
        return []

    try:
        vqd = _get_vqd_token(query)
        if not vqd:
            return []

        encoded_query = urllib.parse.quote_plus(query)
        api_url = (
            f"https://duckduckgo.com/i.js?l=us-en&o=json&q={encoded_query}&vqd={vqd}&f=,,,,,&p=1"
        )
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://duckduckgo.com/",
            },
        )
        with urlopen_with_proxy_fallback(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        return [r["thumbnail"] for r in data.get("results", [])[:20] if r.get("thumbnail")]
    except Exception as e:
        logger.warning(f"Failed to fetch image results for query '{query}': {e}")
        pass

    return []


def download_image(url):
    """Downloads image bytes from a URL. Returns bytes or None on failure."""
    if not url:
        return None
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        },
    )
    try:
        with urlopen_with_proxy_fallback(req, timeout=10) as response:
            data = response.read()
            return data if data else None
    except Exception as e:
        logger.warning(f"Failed to download image from {url}: {e}")
        return None


def build_image_html(url):
    """Builds an img tag with the given URL, constrained to max-width."""
    if not url:
        return ""
    return f'<img src="{url}" style="max-width:300px;">'
