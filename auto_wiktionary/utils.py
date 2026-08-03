import json
import re
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from .proxy_fallback import urlopen_with_proxy_fallback


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
        '[\u3040-\u309f'  # Hiragana
        '\u30a0-\u30ff'  # Katakana
        '\u4e00-\u9faf'  # CJK Unified Ideographs
        '\u3400-\u4dbf'  # CJK Unified Ideographs Extension A
        '\u3000-\u303f]'  # CJK Symbols and Punctuation
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
        headers={"User-Agent": "AnkiAutoWiktionary/1.0 (https://github.com/lyeutsaon/anki-addons)"},
    )

    try:
        with urlopen_with_proxy_fallback(req, timeout=5) as response:
            return response.read().decode('utf-8')
    except HTTPError as e:
        if e.code == 404:
            return ""  # Word not found
        return f"Error: {e.code}"
    except URLError as e:
        return f"Error: Network connection failed. ({e.reason})"
    except Exception as e:
        return f"Error: {str(e)}"


def _extract_bare_cross_reference(li):
    """
    Some ja entries define a word by just pointing at another entry: the whole
    gloss is a wikilink plus '。' (e.g. 砧骨 → '<a>きぬたぼね</a>。'), with no
    漢字表記/参照 marker. Returns the linked word, or None if the <li> is not
    a bare cross-reference.
    """
    children = [c for c in li.children if not (isinstance(c, NavigableString) and not c.strip())]
    if not children:
        return None
    first = children[0]
    if not isinstance(first, Tag) or first.name != 'a':
        return None
    rest = "".join(str(c) for c in children[1:]).strip()
    if rest not in ('', '。'):
        return None
    return first.get_text().strip() or None


def detect_kanji_redirect(html_text):
    """
    Detects if a Japanese Wiktionary page is just a kanji notation redirect.
    For example, 血眼 redirects to ちまなこ with "ちまなこの漢字表記。"
    Returns the kana reading to follow, or None if not a redirect.
    """
    if not html_text or html_text.startswith("Error:"):
        return None

    soup = BeautifulSoup(html_text, 'html.parser')

    # Redirect notices live in either an <ol> or a <ul>. The 和語の漢字表記
    # ("native-word kanji notation") pages, e.g. 物語 → ものがたり, use a <ul>.
    lists = soup.find_all(['ol', 'ul'])
    if not lists:
        return None

    # Collect all top-level <li> items across all redirect lists
    all_lis = []
    for lst in lists:
        all_lis.extend(lst.find_all('li', recursive=False))  # type: ignore[attr-defined]

    # A redirect page has all <li> items matching a redirect pattern
    # ("Xの漢字表記。" / "…参照" / a bare cross-reference link).
    if not all_lis:
        return None

    readings = []
    for li in all_lis:
        li_text = li.get_text().strip()
        # Usage-tag qualifiers may precede the redirect notice
        # (e.g. 聴牌 → "(麻雀) 「テンパイ」を参照。"). The qualifier is not
        # part of the reading, so drop it before matching.
        li_text = re.sub(r'^[（(][^）)]*[）)]\s*', '', li_text)
        # Match redirect patterns:
        #   "Xの漢字表記。"        (e.g. 血眼 → ちまなこ)
        #   "X　参照"              (whitespace-joined, e.g. 落ちる → おちる)
        #   "「X」を参照。"         (を-joined with trailing 。, e.g. 天下り → あまくだり)
        #   '"X"参照'              (quote-wrapped, no separator, e.g. 物語 → ものがたり)
        # The separator before 参照 may be whitespace, を, or a closing
        # quote/bracket that wraps the reading.
        match = re.match(r'^(.+?)(?:の漢字表記。|(?:[\s　]+|を|["”」』])参照。?)$', li_text)
        if match:
            reading = match.group(1)
            # Some pages wrap the reading in quotes/corner brackets
            # (e.g. 関脇 → 「せきわけ」の漢字表記。, 物語 → "ものがたり"参照).
            # Strip them so the follow-up fetch uses the bare reading.
            reading = reading.strip('「」『』"“”\'')
        else:
            # Bare cross-reference: the whole gloss is just a wikilink plus '。'
            # (e.g. 砧骨 → '<a>きぬたぼね</a>。'), with no 漢字表記/参照 marker.
            reading = _extract_bare_cross_reference(li)
            if reading is None:
                return None
        readings.append(reading)

    # Multi-language pages repeat the same redirect notice per section
    # (e.g. 砧骨 has identical 日本語/朝鮮語/中国語 glosses) — dedupe.
    readings = list(dict.fromkeys(readings))
    return (readings[0], readings)


def inject_redirect_pronunciation(parsed_html, all_readings):
    """
    When a kanji redirect occurs, ensures the pronunciation appears at the top
    of the parsed output (right after the opening <ul>).
    - Multi-reading: always prepends "reading1 又は reading2"
    - Single-reading: prepends if the pronunciation isn't already the first <p>
    """
    if not all_readings:
        return parsed_html

    pronunciation = " 又は ".join(all_readings)

    # Check if pronunciation is already at the top (e.g. <ul><p><strong>つく</strong></p>...)
    if len(all_readings) == 1:
        # Match <ul><p> ... reading ... </p> at the start
        match = re.match(
            r'^<ul><p>(?:<[^>]+>)*' + re.escape(all_readings[0]) + r'(?:<[^>]+>)*</p>', parsed_html
        )
        if match:
            return parsed_html

    if parsed_html.startswith("<ul>"):
        return "<ul><p>" + pronunciation + "</p>" + parsed_html[4:]
    return "<p>" + pronunciation + "</p>" + parsed_html


def _filter_language_sections(soup, lang):
    target_headers = {"en": ["english"], "ja": ["japanese", "日本語"]}
    sections = soup.find_all('section')
    if sections:
        for section in sections:
            h2 = section.find('h2')
            if h2:
                header_text = h2.get_text().strip().lower()
                allowed_headers = target_headers.get(lang, [])
                if allowed_headers and not any(h == header_text for h in allowed_headers):
                    section.decompose()
        return
    # New wrinkle: the parse API no longer emits <section> wrappers — headings
    # are flat <div class="mw-heading mw-headingN"> siblings, so remove whole
    # heading blocks instead (h2 blocks run to the next h2).
    allowed_headers = target_headers.get(lang, [])
    if not allowed_headers:
        return
    for div, level, h_tag in _iter_heading_divs(soup):
        if level == 2 and h_tag.get_text().strip().lower() not in allowed_headers:
            _remove_heading_div_block(div, level)


def _heading_div_level(div):
    for cls in div.get('class', []):
        match = re.fullmatch(r'mw-heading(\d)', cls)
        if match:
            return int(match.group(1))
    return None


def _iter_heading_divs(soup):
    for div in soup.find_all('div', class_=re.compile(r'\bmw-heading\d\b')):
        h_tag = div.find(['h2', 'h3', 'h4', 'h5'])
        level = _heading_div_level(div)
        if h_tag and level is not None:
            yield div, level, h_tag


def _remove_heading_div_block(div, level, stop_at_any_heading=False):
    # Heading divs are flat siblings of their content (no <section> nesting):
    # drop everything up to the next heading div of the same or higher level
    # (or any next heading div when stop_at_any_heading is True).
    node = div.next_sibling
    while node is not None:
        nxt = node.next_sibling
        if isinstance(node, Tag) and _heading_div_level(node) is not None:
            if stop_at_any_heading or _heading_div_level(node) <= level:
                break
        node.extract()
        node = nxt
    div.decompose()


def _remove_unwanted_tags(soup):
    # Citation lists (mw-references-wrap/ol.references) are footnote dumps,
    # not definitions — they sit under 参考文献/References headings that the
    # keyword filter keeps.
    for tag in soup.find_all(
        class_=[
            "mw-empty-elt",
            "reference",
            "references",
            "mw-references-wrap",
            "mw-editsection",
            "ext-phonos",
        ]
    ):
        tag.decompose()
    for tag in soup.find_all(["style", "link"]):
        tag.decompose()
    skip_keywords = [
        'translation',
        'synonym',
        'antonym',
        'pronunciation',
        'etymology',
        '翻訳',
        '類義語',
        '関連語',
        '対義語',
        '発音',
        '語源',
        '合成語',
        '関連項目',
        'anagram',
    ]
    for section in list(soup.find_all('section')):
        h_tag = section.find(['h2', 'h3', 'h4', 'h5'])
        if h_tag:
            header_text = h_tag.get_text().lower()
            if any(kw in header_text for kw in skip_keywords):
                child_sections = section.find_all('section', recursive=False)
                for child in reversed(child_sections):
                    section.insert_after(child)
                section.decompose()
    for div, level, h_tag in _iter_heading_divs(soup):
        if any(kw in h_tag.get_text().lower() for kw in skip_keywords):
            _remove_heading_div_block(div, level, stop_at_any_heading=True)


def _extract_square_bracket_reading(p_tag):
    hit_bracket = False
    for child in list(p_tag.contents):
        if child.name is None:
            text_val = str(child)
            if not hit_bracket and '【' in text_val:
                hit_bracket = True
                before = text_val[: text_val.index('【')]
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


def _extract_inline_reading(ol):
    """
    For kanji character pages where the <ol> has no preceding <p>,
    the first <li> may start with <b>reading</b>。definition...
    or <b>r1</b> 又は <b>r2</b>。definition...
    Extracts the reading(s) and removes them from the <li>.
    Returns the reading string, or None.
    """
    first_li = ol.find('li', recursive=False)
    if not first_li:
        return None

    # Check if first child is <b> (possibly containing <a>)
    first_child = None
    for child in first_li.children:
        if isinstance(child, str) and not child.strip():
            continue
        first_child = child
        break

    if not first_child or getattr(first_child, 'name', None) != 'b':
        return None

    # Collect reading parts: <b>r1</b> [又は <b>r2</b>]*。
    reading_parts = []
    nodes_to_remove = []

    for child in list(first_li.children):
        if isinstance(child, str) and not child.strip() and not reading_parts:
            continue

        if isinstance(child, Tag) and child.name == 'b':
            reading_parts.append(child.get_text())
            nodes_to_remove.append(child)
        elif isinstance(child, NavigableString):
            text = child.strip()
            if text.startswith('又は') and reading_parts:
                nodes_to_remove.append(child)
                continue
            if text.startswith('。') and reading_parts:
                # Found the separator — remove the 。 and stop
                remaining = str(child).replace('。', '', 1)
                if remaining.strip():
                    child.replace_with(NavigableString(remaining))
                else:
                    child.extract()
                break
            # Not a reading pattern
            return None
        else:
            # Non-text, non-<b> element before 。 — not a reading pattern
            return None

    if not reading_parts:
        return None

    # Remove collected reading nodes
    for node in nodes_to_remove:
        node.extract()

    return " 又は ".join(reading_parts)


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

    # Definitions live in <ol> on most pages, but single-gloss entries
    # (e.g. ja:起工) use a plain <ul>. Nested lists (examples inside an
    # <li>) are skipped — they are already captured in the parent's text.
    lists = [lst for lst in soup.find_all(['ol', 'ul']) if lst.find_parent(['ol', 'ul']) is None]

    results = []
    processed_ps = set()
    for ol in lists:
        p_tag = ol.find_previous_sibling('p')
        if p_tag and id(p_tag) not in processed_ps:
            processed_ps.add(id(p_tag))
            inner_html = _clean_p_tag_content(p_tag)
            if inner_html:
                results.append(f"<p>{inner_html}</p>")
        else:
            reading = _extract_inline_reading(ol)
            if reading:
                results.append(f"<p>{reading}</p>")

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
        if (
            clean_content.startswith("<p>Word '")
            or clean_content.startswith("<div><p>Word '")
            or clean_content.startswith("Word '")
        ):
            return parsed_definition

    soup_parsed = BeautifulSoup(parsed_definition, 'html.parser')
    p_tag = soup_parsed.find('p')
    overlapped = False
    if p_tag:
        pronunciation = p_tag.get_text(strip=True)
        if pronunciation:
            pronunciation_escaped = re.escape(pronunciation)
            pattern = (
                r'^\s*(?:<[^>]+>\s*)*' + pronunciation_escaped + r'\s*(?:</[^>]+>|<br\s*/?>)?\s*'
            )
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
        headers={"User-Agent": "AnkiAutoWiktionary/1.0 (https://github.com/lyeutsaon/anki-addons)"},
    )

    try:
        with urlopen_with_proxy_fallback(req, timeout=5) as response:
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
