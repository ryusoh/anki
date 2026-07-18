import json
import logging
import re
import urllib.parse
import urllib.request

from .proxy_fallback import urlopen_with_proxy_fallback

logger = logging.getLogger(__name__)


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
