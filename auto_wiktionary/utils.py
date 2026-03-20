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

def parse_wiktionary_html(html_text, lang="en"):
    """
    Parses the raw HTML from Wiktionary into a cleaner <ul><li> format suitable for Anki.
    """
    if not html_text or html_text.startswith("Error:"):
        return html_text

    soup = BeautifulSoup(html_text, 'html.parser')

    # Keep only the target language section if there are language headers
    target_headers = {
        "en": ["english"],
        "ja": ["japanese", "日本語"]
    }
    
    # Check if there are any top-level language sections
    # On Wiktionary, languages are usually in h2 tags
    for section in soup.find_all('section'):
        h2 = section.find('h2')
        if h2:
            header_text = h2.get_text().strip().lower()
            allowed_headers = target_headers.get(lang, [])
            if allowed_headers and not any(h == header_text for h in allowed_headers):
                section.decompose()

    # Remove empty elements and references
    for tag in soup.find_all(class_=["mw-empty-elt", "reference", "mw-editsection", "ext-phonos"]):
        tag.decompose()

    # Remove styles and links (used for categories)
    for tag in soup.find_all(["style", "link"]):
        tag.decompose()

    # Remove non-definition sections like Translations or Synonyms if they are separate
    for section in soup.find_all('section'):
        h_tag = section.find(['h2', 'h3', 'h4', 'h5'])
        if h_tag:
            header_text = h_tag.get_text().lower()
            skip_keywords = ['translation', 'synonym', 'antonym', '翻訳', '類義語', '関連語', '対義語', 'anagram']
            if any(kw in header_text for kw in skip_keywords):
                section.decompose()

    ols = soup.find_all('ol')

    results = []
    processed_ps = set()
    for ol in ols:
        p_tag = ol.find_previous_sibling('p')
        if p_tag and id(p_tag) not in processed_ps:
            processed_ps.add(id(p_tag))
            
            for span in p_tag.find_all('span'):
                span.unwrap()
            for a in p_tag.find_all('a'):
                a.unwrap()
                
            for tag in p_tag.find_all(True):
                tag.attrs = {}
            p_tag.attrs = {}
            
            hit_parenthesis = False
            for child in list(p_tag.contents):
                if child.name is None: # Text node
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
            
            inner_html = "".join(str(c) for c in p_tag.contents).strip(" \t\n\r\xa0")
            if inner_html.startswith("(") or inner_html.startswith("（"):
                inner_html = inner_html[1:]
            if inner_html.endswith(")") or inner_html.endswith("）"):
                inner_html = inner_html[:-1]
            inner_html = inner_html.strip(" \t\n\r\xa0")
            
            if inner_html:
                results.append(f"<p>{inner_html}</p>")

        for li in ol.find_all('li', recursive=False):
            # Unwrap links (remove <a> but keep inner text)
            for a in li.find_all('a'):
                a.unwrap()

            # Clean all attributes from remaining tags
            for tag in li.find_all(True):
                # We can keep some basic tags
                tag.attrs = {}

            li.attrs = {}
            results.append(str(li))

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
