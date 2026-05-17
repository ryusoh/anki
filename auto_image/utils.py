import re
import json
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError


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
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=10) as response:
        html = response.read().decode('utf-8', errors='ignore')

    match = re.search(r'vqd="([^"]+)"', html) or re.search(r'vqd=([^&"]+)', html)
    return match.group(1) if match else None


def fetch_image_results(query):
    """
    Fetches a list of valid image URLs using DuckDuckGo's image search API.
    Validates each URL by attempting to download it.
    Returns a list of URL strings (may be empty).
    """
    if not query:
        return []

    try:
        vqd = _get_vqd_token(query)
        if not vqd:
            return []

        encoded_query = urllib.parse.quote_plus(query)
        api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={encoded_query}&vqd={vqd}&f=,,,,,&p=1"
        req = urllib.request.Request(api_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://duckduckgo.com/"
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        valid_urls = []
        for result in data.get("results", [])[:10]:
            image_url = result.get("image", "")
            if image_url and download_image(image_url) is not None:
                valid_urls.append(image_url)
        return valid_urls
    except Exception:
        pass

    return []


def download_image(url):
    """
    Downloads image bytes from a URL. Returns the bytes if successful,
    or None if the URL is unreachable, not an image, or empty.
    """
    if not url:
        return None

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                return None
            data = response.read()
            if not data:
                return None
            return data
    except Exception:
        return None


def build_image_html(url):
    """Builds an img tag with the given URL, constrained to max-width."""
    if not url:
        return ""
    return f'<img src="{url}" style="max-width:300px;">'
