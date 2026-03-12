import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import detect_language, clean_html_text

def test_clean_html_text():
    assert clean_html_text("hello") == "hello"
    assert clean_html_text("<b>bold</b>") == "bold"
    assert clean_html_text("  spaces  ") == "spaces"
    assert clean_html_text("hello&nbsp;world") == "hello world"
    assert clean_html_text("multiple<br>lines") == "multiple lines"

def test_detect_language():
    # English words
    assert detect_language("hello") == "en"
    assert detect_language("jazz dot") == "en"
    assert detect_language("This is a test.") == "en"

    # Japanese words (Hiragana, Katakana, Kanji)
    assert detect_language("邂逅") == "ja"
    assert detect_language("こんにちは") == "ja"
    assert detect_language("テスト") == "ja"
    assert detect_language("これはテストです") == "ja"

    # Mixed words: we lean towards ja if it has Japanese chars
    assert detect_language("jazz dot (ジャズ・ドット)") == "ja"
