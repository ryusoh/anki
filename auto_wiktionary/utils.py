import re
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import json
from bs4 import BeautifulSoup

def clean_html_text(html_text):
    """
    Cleans HTML tags and entities to extract the raw text for searching.
    """
    if not html_text:
        return ""

    # Replace common HTML breaks/spaces with a space
    text = re.sub(r'<br\s*/?>', ' ', html_text)
    text = text.replace('&nbsp;', ' ')

    # Remove any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Strip extra whitespace
    text = ' '.join(text.split())

    return text

def detect_language(text):
    """
    Detects if the text contains Japanese characters (Hiragana, Katakana, Kanji).
    Returns 'ja' if so, otherwise 'en'.
    """
    if not text:
        return "en"

    jp_regex = re.compile(
        '[\u3040-\u309F' # Hiragana
        '\u30A0-\u30FF' # Katakana
        '\u4E00-\u9FAF' # CJK Unified Ideographs
        '\u3400-\u4DBF' # CJK Unified Ideographs Extension A
        '\u3000-\u303F]' # CJK Symbols and Punctuation
    )

    if jp_regex.search(text):
        return "ja"
    return "en"


def fetch_wiktionary_html(word, lang):
    """
    Fetches the HTML definition of the word from Wiktionary API.
    """
    if not word:
        return ""

    encoded_word = urllib.parse.quote(word)
    url = f"https://{lang}.wiktionary.org/api/rest_v1/page/html/{encoded_word}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AnkiAutoWiktionary/1.0 (https://github.com/lyeutsaon/anki-addons)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode('utf-8')
    except HTTPError as e:
        if e.code == 404:
            return "" # Word not found
        return f"Error: {e.code}"
    except URLError:
        return "Error: Network connection failed."
    except Exception as e:
        return f"Error: {str(e)}"

def detect_kanji_redirect(html_text):
    """
    Detects if a Japanese Wiktionary page is just a kanji notation redirect.
    For example, 血眼 redirects to ちまなこ with "ちまなこの漢字表記。"
    Returns the kana reading to follow, or None if not a redirect.
    """
    if not html_text or html_text.startswith("Error:"):
        return None

    soup = BeautifulSoup(html_text, 'html.parser')

    ols = soup.find_all('ol')
    if not ols:
        return None

    # Collect all <li> items across all <ol>s
    all_lis = []
    for ol in ols:
        all_lis.extend(ol.find_all('li', recursive=False))

    # A redirect page has all <li> items matching "Xの漢字表記。"
    if not all_lis:
        return None

    readings = []
    for li in all_lis:
        li_text = li.get_text().strip()
        match = re.match(r'^(.+)の漢字表記。$', li_text)
        if not match:
            return None
        readings.append(match.group(1))

    return (readings[0], readings)


def inject_redirect_pronunciation(parsed_html, all_readings):
    """
    When a kanji redirect has multiple readings, prepends a <p> with all readings
    at the top of the parsed output (right after the opening <ul>).
    For single readings, returns the parsed HTML unchanged.
    """
    if len(all_readings) <= 1:
        return parsed_html

    pronunciation = " 又は ".join(all_readings)
    if parsed_html.startswith("<ul>"):
        return "<ul><p>" + pronunciation + "</p>" + parsed_html[4:]
    return "<p>" + pronunciation + "</p>" + parsed_html


def _filter_language_sections(soup, lang):
    target_headers = {
        "en": ["english"],
        "ja": ["japanese", "日本語"]
    }
    for section in soup.find_all('section'):
        h2 = section.find('h2')
        if h2:
            header_text = h2.get_text().strip().lower()
            allowed_headers = target_headers.get(lang, [])
            if allowed_headers and not any(h == header_text for h in allowed_headers):
                section.decompose()


def _remove_unwanted_tags(soup):
    for tag in soup.find_all(class_=["mw-empty-elt", "reference", "mw-editsection", "ext-phonos"]):
        tag.decompose()
    for tag in soup.find_all(["style", "link"]):
        tag.decompose()
    for section in soup.find_all('section'):
        h_tag = section.find(['h2', 'h3', 'h4', 'h5'])
        if h_tag:
            header_text = h_tag.get_text().lower()
            skip_keywords = ['translation', 'synonym', 'antonym', '翻訳', '類義語', '関連語', '対義語', 'anagram']
            if any(kw in header_text for kw in skip_keywords):
                section.decompose()


def _extract_square_bracket_reading(p_tag):
    hit_bracket = False
    for child in list(p_tag.contents):
        if child.name is None:
            text_val = str(child)
            if not hit_bracket and '【' in text_val:
                hit_bracket = True
                before = text_val[:text_val.index('【')]
                if before.strip():
                    child.replace_with(before)
                else:
                    child.extract()
                continue
        if hit_bracket:
            child.extract()


def _extract_parenthesis_reading(p_tag):
    hit_parenthesis = False
    for child in list(p_tag.contents):
        if child.name is None:
            text_val = str(child)
            if not hit_parenthesis and ('(' in text_val or '（' in text_val):
                hit_parenthesis = True
                idx = -1
                if '(' in text_val and '（' in text_val:
                    idx = min(text_val.find('('), text_val.find('（'))
                elif '(' in text_val:
                    idx = text_val.find('(')
                elif '（' in text_val:
                    idx = text_val.find('（')

                if idx != -1:
                    child.replace_with(text_val[idx:])
                continue
        if not hit_parenthesis:
            child.extract()


def _strip_outer_parentheses(inner_html):
    if inner_html.startswith("(") or inner_html.startswith("（"):
        open_c = inner_html[0]
        close_c = ')' if open_c == '(' else '）'
        plain = re.sub(r'<[^>]+>', '', inner_html)
        depth = 0
        match_end = -1
        for i, ch in enumerate(plain):
            if ch == open_c:
                depth += 1
            elif ch == close_c:
                depth -= 1
                if depth == 0:
                    match_end = i
                    break
        if match_end == len(plain.rstrip()) - 1:
            inner_html = inner_html[1:]
            if inner_html.endswith(close_c):
                inner_html = inner_html[:-1]
    return inner_html.strip(" \t\n\r\xa0")


def _clean_p_tag_content(p_tag):
    for span in p_tag.find_all('span'):
        span.unwrap()
    for a in p_tag.find_all('a'):
        a.unwrap()
    for tag in p_tag.find_all(True):
        tag.attrs = {}
    p_tag.attrs = {}

    full_text = p_tag.get_text()
    use_square_bracket = '【' in full_text and ('(' not in full_text and '（' not in full_text)

    if use_square_bracket:
        _extract_square_bracket_reading(p_tag)
    else:
        _extract_parenthesis_reading(p_tag)

    inner_html = "".join(str(c) for c in p_tag.contents).strip(" \t\n\r\xa0")
    if not use_square_bracket:
        inner_html = _strip_outer_parentheses(inner_html)
    return inner_html


def _process_ol_items(ol):
    items = []
    for li in ol.find_all('li', recursive=False):
        for a in li.find_all('a'):
            a.unwrap()
        for tag in li.find_all(True):
            tag.attrs = {}
        li.attrs = {}
        items.append(str(li))
    return "".join(items)


def parse_wiktionary_html(html_text, lang="en"):
    """
    Parses the raw HTML from Wiktionary into a cleaner <ul><li> format suitable for Anki.
    """
    if not html_text or html_text.startswith("Error:"):
        return html_text

    soup = BeautifulSoup(html_text, 'html.parser')

    _filter_language_sections(soup, lang)
    _remove_unwanted_tags(soup)

    ols = soup.find_all('ol')

    results = []
    processed_ps = set()
    for ol in ols:
        p_tag = ol.find_previous_sibling('p')
        if p_tag and id(p_tag) not in processed_ps:
            processed_ps.add(id(p_tag))
            inner_html = _clean_p_tag_content(p_tag)
            if inner_html:
                results.append(f"<p>{inner_html}</p>")

        results.append(_process_ol_items(ol))

    if not results:
        return ""

    return "<ul>" + "".join(results) + "</ul>"

def merge_definition(current_content, parsed_definition):
    """
    Merges the fetched definition with the existing content.
    If there is existing content, prepends the definition to it.
    """
    if not current_content:
        return parsed_definition
        
    clean_content = current_content.strip()
    if clean_content in ('', '<br>', '<br/>', '<br />', '<div><br></div>'):
        return parsed_definition

    if "not found. Did you mean:</p>" in clean_content:
        # Check if it starts with the "Did you mean" template
        if clean_content.startswith("<p>Word '") or clean_content.startswith("<div><p>Word '") or clean_content.startswith("Word '"):
            return parsed_definition
        
    soup_parsed = BeautifulSoup(parsed_definition, 'html.parser')
    p_tag = soup_parsed.find('p')
    overlapped = False
    if p_tag:
        pronunciation = p_tag.get_text(strip=True)
        if pronunciation:
            pronunciation_escaped = re.escape(pronunciation)
            pattern = r'^\s*(?:<[^>]+>\s*)*' + pronunciation_escaped + r'\s*(?:</[^>]+>|<br\s*/?>)?\s*'
            new_content = re.sub(pattern, '', current_content, count=1)
            if new_content != current_content:
                current_content = new_content
                overlapped = True
            
    if overlapped:
        return f"{parsed_definition}{current_content}"
    return f"{parsed_definition}<br>{current_content}"

def get_wiktionary_candidates(word, lang="en"):
    """
    Fetches a list of up to 5 suggested words from Wiktionary's opensearch API.
    """
    if not word:
        return []

    encoded_word = urllib.parse.quote(word)
    url = f"https://{lang}.wiktionary.org/w/api.php?action=opensearch&search={encoded_word}&limit=5&format=json"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AnkiAutoWiktionary/1.0 (https://github.com/lyeutsaon/anki-addons)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if len(data) > 1 and isinstance(data[1], list):
                return data[1]
    except Exception as e:
        print(f"Error getting wiktionary candidates: {e}")
    
    return []

def format_candidates_html(word, candidates):
    """
    Formats a list of candidate words as plain text separated by line breaks.
    """
    if not candidates:
        return ""
        
    html = f"<p>Word '{word}' not found. Did you mean:</p>\n"
    html += "<br>\n".join(candidates)
    return html
